# ms-analitica/service/estadisticas_service.py
# Estadísticas para el panel de administración (cacheadas 60 s)
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from config.errores import ErrorApi
from config.settings import SEGUNDOS_CACHE_ESTADISTICAS
from model.dto.analitica_dto import (
    AgruparPor, EstadisticasTiendaDTO, FranjaAfluenciaDTO, MetricaOcupacionDTO, MetricaVentasDTO,
    PopularidadArtistaDTO, PrevisionAfluenciaDTO, ResumenDTO,
)
from model.factory.factory_dao import DAOFactory
from service import cache


def _dao():
    return DAOFactory.get_analitica_dao()


def _cacheado(clave: str, calcular):
    valor = cache.obtener(clave)
    if valor is None:
        valor = calcular()
        cache.guardar(clave, valor, SEGUNDOS_CACHE_ESTADISTICAS)
    return valor


def _rango_fechas(filtro: dict, desde: date | None, hasta: date | None) -> dict:
    if desde and hasta and desde > hasta:
        raise ErrorApi(400, "PETICION_NO_VALIDA", "desde no puede ser posterior a hasta")
    if desde or hasta:
        filtro["fecha"] = {}
        if desde:
            filtro["fecha"]["$gte"] = desde.isoformat()
        if hasta:
            filtro["fecha"]["$lte"] = hasta.isoformat()
    return filtro


def entradas_netas(evento_id: str) -> int:
    ventas = _dao().buscar("metricas_ventas", {"evento_id": evento_id})
    return sum(v.get("entradas", 0) - v.get("cancelaciones", 0) for v in ventas)


# ── Resumen ─────────────────────────────────────────────────

def resumen(evento_id: str | None) -> dict:
    def calcular():
        dao = _dao()
        filtro = {"evento_id": evento_id} if evento_id else {}
        ventas = dao.buscar("metricas_ventas", filtro)
        ocupacion = dao.buscar("metricas_ocupacion", filtro)
        tienda = dao.buscar("metricas_tienda")
        total_espacios = sum(o.get("total", 0) for o in ocupacion)
        hoy = datetime.now(timezone.utc).date().isoformat()
        return ResumenDTO(
            entradas_vendidas=sum(v.get("entradas", 0) - v.get("cancelaciones", 0) for v in ventas),
            ingresos_entradas=round(sum(v.get("ingresos", 0) for v in ventas), 2),
            ingresos_alquileres=round(sum(o.get("ingresos_alquiler", 0) for o in ocupacion), 2),
            ingresos_tienda=round(sum(t.get("ingresos", 0) for t in tienda), 2),
            usuarios_registrados=dao.contar("usuarios"),
            ocupacion_espacios=round(sum(o.get("alquilados", 0) for o in ocupacion) / total_espacios, 4)
            if total_espacios else 0.0,
            asistentes_hoy=sum(a.get("validadas", 0) for a in dao.buscar("asistencia", filtro | {"fecha": hoy})),
            actualizado_en=datetime.now(timezone.utc),
        ).model_dump(mode="json")

    return _cacheado(f"estadisticas:resumen:{evento_id}", calcular)


# ── Ventas ──────────────────────────────────────────────────

def _periodo(fila: dict, agrupar: AgruparPor) -> str:
    if agrupar == AgruparPor.TIPO_PASE:
        return fila["tipo_pase"]
    if agrupar == AgruparPor.SEMANA:
        anio, semana, _ = date.fromisoformat(fila["fecha"]).isocalendar()
        return f"{anio}-W{semana:02d}"
    return fila["fecha"]


def ventas(evento_id: str | None, desde: date | None, hasta: date | None, agrupar: AgruparPor) -> list[dict]:
    filtro = _rango_fechas({"evento_id": evento_id} if evento_id else {}, desde, hasta)

    def calcular():
        grupos: dict[tuple, dict] = defaultdict(lambda: {"entradas": 0, "ingresos": 0.0, "cancelaciones": 0})
        for fila in _dao().buscar("metricas_ventas", filtro):
            clave = (fila["evento_id"], _periodo(fila, agrupar))
            for campo in ("entradas", "ingresos", "cancelaciones"):
                grupos[clave][campo] += fila.get(campo, 0)
        return [
            MetricaVentasDTO(evento_id=ev, periodo=periodo, entradas=g["entradas"], ingresos=round(g["ingresos"], 2),
                             cancelaciones=g["cancelaciones"],
                             tipo_pase=periodo if agrupar == AgruparPor.TIPO_PASE else None).model_dump()
            for (ev, periodo), g in sorted(grupos.items())
        ]

    return _cacheado(f"estadisticas:ventas:{evento_id}:{desde}:{hasta}:{agrupar.value}", calcular)


# ── Ocupación ───────────────────────────────────────────────

def ocupacion(evento_id: str) -> list[dict]:
    filas = _dao().buscar("metricas_ocupacion", {"evento_id": evento_id})
    if not filas:
        raise ErrorApi(404, "SIN_DATOS", f"No hay datos de ocupación para {evento_id}")
    return [MetricaOcupacionDTO(evento_id=evento_id, tipo_espacio=f["tipo_espacio"], total=f.get("total", 0),
                                alquilados=f.get("alquilados", 0),
                                ingresos_alquiler=round(f.get("ingresos_alquiler", 0), 2)).model_dump()
            for f in sorted(filas, key=lambda f: f["tipo_espacio"])]


# ── Afluencia ───────────────────────────────────────────────

def _solapan(a: dict, b: dict) -> bool:
    return a["inicio"] < b["fin"] and b["inicio"] < a["fin"]


def afluencia(evento_id: str, fecha: date | None) -> list[PrevisionAfluenciaDTO]:
    """Público del día (entradas validadas o, si aún no hay, vendidas) repartido entre los pases que
    coinciden en el tiempo según los favoritos de cada artista."""
    dao = _dao()
    escaleta = dao.obtener("escaletas", evento_id)
    if not escaleta:
        raise ErrorApi(404, "SIN_DATOS", f"No hay escaleta publicada para {evento_id}")
    favoritos = {p["_id"]: p.get("favoritos", 0) for p in dao.buscar("popularidad_artistas")}
    vendidas = entradas_netas(evento_id)

    resultado: dict[str, PrevisionAfluenciaDTO] = {}
    for dia in escaleta["dias"]:
        if fecha and dia["fecha"] != fecha.isoformat():
            continue
        validadas = sum(a.get("validadas", 0) for a in dao.buscar("asistencia", {"evento_id": evento_id,
                                                                                 "fecha": dia["fecha"]}))
        publico = validadas or vendidas
        pases = [p | {"espacio_id": e["espacio_id"]} for e in dia["escenarios"] for p in e["pases"]
                 if p["estado"] != "CANCELADO"]
        for pase in pases:
            concurrentes = [q for q in pases if _solapan(pase, q)]
            peso = favoritos.get(pase["artista_id"], 0) + 1
            cuota = peso / sum(favoritos.get(q["artista_id"], 0) + 1 for q in concurrentes)
            aforo = (dao.obtener("espacios", pase["espacio_id"]) or {}).get("aforo")
            estimados = round(publico * cuota)
            if aforo:
                estimados = min(estimados, aforo)
            prevision = resultado.setdefault(pase["espacio_id"], PrevisionAfluenciaDTO(
                espacio_id=pase["espacio_id"], escenario=pase["escenario"], franjas=[]))
            prevision.franjas.append(FranjaAfluenciaDTO(
                inicio=pase["inicio"], fin=pase["fin"], artista=pase["artista"], asistentes_estimados=estimados,
                porcentaje_aforo=round(estimados / aforo, 4) if aforo else None))
    for prevision in resultado.values():
        prevision.franjas.sort(key=lambda f: f.inicio)
    return sorted(resultado.values(), key=lambda p: p.escenario)


# ── Tienda ──────────────────────────────────────────────────

def tienda(desde: date | None, hasta: date | None) -> dict:
    filtro = _rango_fechas({}, desde, hasta)

    def calcular():
        grupos: dict[tuple, dict] = defaultdict(lambda: {"unidades": 0, "ingresos": 0.0})
        for fila in _dao().buscar("metricas_tienda", filtro):
            grupos[(fila["producto_id"], fila["talla"])]["unidades"] += fila.get("unidades", 0)
            grupos[(fila["producto_id"], fila["talla"])]["ingresos"] += fila.get("ingresos", 0)
        ventas_tienda = [{"producto_id": p, "talla": t, "unidades": g["unidades"], "ingresos": round(g["ingresos"], 2)}
                         for (p, t), g in sorted(grupos.items(), key=lambda x: -x[1]["unidades"])]
        stock = [{"producto_id": s["producto_id"], "talla": s["talla"], "stock": s["stock"]}
                 for s in _dao().buscar("stock_bajo")]
        return EstadisticasTiendaDTO(ventas=ventas_tienda, stock_bajo=stock).model_dump()

    return _cacheado(f"estadisticas:tienda:{desde}:{hasta}", calcular)


# ── Popularidad de artistas ─────────────────────────────────

def _actividad(diaria: list[dict], desde: date, hasta: date) -> int:
    return sum(d.get("favoritos", 0) + d.get("visitas", 0) for d in diaria
               if desde.isoformat() <= d["fecha"] < hasta.isoformat())


def artistas_del_evento(evento_id: str) -> set[str] | None:
    escaleta = _dao().obtener("escaletas", evento_id)
    if not escaleta:
        return None
    return {p["artista_id"] for d in escaleta["dias"] for e in d["escenarios"] for p in e["pases"]}


def popularidad(evento_id: str | None = None, limite: int = 10) -> list[PopularidadArtistaDTO]:
    dao = _dao()
    del_evento = artistas_del_evento(evento_id) if evento_id else None
    hoy = datetime.now(timezone.utc).date() + timedelta(days=1)
    ranking = []
    for p in dao.buscar("popularidad_artistas"):
        if evento_id and (del_evento is None or p["_id"] not in del_evento):
            continue
        diaria = dao.buscar("popularidad_diaria", {"artista_id": p["_id"]})
        ultimos = _actividad(diaria, hoy - timedelta(days=7), hoy)
        anteriores = _actividad(diaria, hoy - timedelta(days=14), hoy - timedelta(days=7))
        tendencia = (ultimos - anteriores) / anteriores if anteriores else (1.0 if ultimos else 0.0)
        ranking.append(PopularidadArtistaDTO(artista_id=p["_id"], artista=p.get("artista"),
                                             favoritos=max(p.get("favoritos", 0), 0), visitas=p.get("visitas", 0),
                                             tendencia_7d=round(tendencia, 4)))
    ranking.sort(key=lambda a: (a.favoritos, a.visitas), reverse=True)
    return ranking[:limite]
