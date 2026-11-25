# ms-analitica/service/recomendaciones_service.py
# Recomendaciones (clientes, visitantes y proveedores) y registro de interacciones del front-end
from collections import Counter
from datetime import datetime, timezone
from config.errores import ErrorApi
from config.settings import SEGUNDOS_CACHE_RECOMENDACIONES
from model.dto.analitica_dto import (
    ArtistaRecomendadoDTO, EspacioRecomendadoDTO, EventoRecomendadoDTO, LoteInteraccionesDTO, PaseMiEscaletaDTO,
    RecomendacionesClienteDTO, RecomendacionesPopularesDTO,
)
from model.factory.factory_dao import DAOFactory
from service import cache
from service.estadisticas_service import entradas_netas, popularidad

ESTADOS_VISIBLES = ("PUBLICADO", None)  # None: evento del que aún no ha llegado el estado


def _dao():
    return DAOFactory.get_analitica_dao()


def _pases_por_evento() -> dict[str, list[dict]]:
    """Pases publicados de cada evento (réplica alimentada por escaleta.publicada)."""
    return {e["_id"]: [p for d in e["dias"] for esc in d["escenarios"] for p in esc["pases"]]
            for e in _dao().buscar("escaletas")}


def _eventos_visibles() -> dict[str, dict]:
    estados = {e["_id"]: e for e in _dao().buscar("eventos")}
    return {ev: estados.get(ev, {}) for ev in _pases_por_evento()
            if estados.get(ev, {}).get("estado") in ESTADOS_VISIBLES}


# ── Cliente ─────────────────────────────────────────────────

def _artistas_recomendados(dao, favoritos: set[str], usuario_id: str) -> list[ArtistaRecomendadoDTO]:
    artistas = {a["_id"]: a for a in dao.buscar("artistas")}
    generos_favoritos = Counter(g for a in favoritos for g in artistas.get(a, {}).get("generos", []))

    # Colaborativo: qué más marcan los clientes que comparten algún favorito
    vecinos = {f["usuario_id"] for f in dao.buscar("favoritos", {"artista_id": {"$in": list(favoritos)}})} - {usuario_id}
    colaborativo = Counter(f["artista_id"] for f in dao.buscar("favoritos", {"usuario_id": {"$in": list(vecinos)}})
                           if f["artista_id"] not in favoritos)
    max_colab = max(colaborativo.values(), default=0)

    recomendados = []
    for artista_id, artista in artistas.items():
        if artista_id in favoritos:
            continue
        generos = artista.get("generos", [])
        comunes = [g for g in generos if g in generos_favoritos]
        contenido = len(comunes) / len(generos) if generos else 0
        colab = colaborativo.get(artista_id, 0) / max_colab if max_colab else 0
        puntuacion = round(0.6 * contenido + 0.4 * colab, 4)
        if puntuacion <= 0:
            continue
        if contenido >= colab:
            referencia = next((artistas[f]["nombre"] for f in favoritos
                               if set(artistas.get(f, {}).get("generos", [])) & set(comunes)), comunes[0])
            motivo = f"Porque te gusta {referencia}"
        else:
            motivo = "A clientes con tus mismos favoritos también les gusta"
        recomendados.append(ArtistaRecomendadoDTO(artista_id=artista_id, artista=artista.get("nombre"),
                                                  puntuacion=puntuacion, motivo=motivo))
    return sorted(recomendados, key=lambda a: a.puntuacion, reverse=True)[:10]


def _eventos_recomendados(favoritos: set[str], recomendados: set[str], evento_id: str | None):
    pases = _pases_por_evento()
    candidatos = []
    for ev, datos in _eventos_visibles().items():
        if evento_id and ev != evento_id:
            continue
        artistas_ev = {p["artista_id"] for p in pases[ev]}
        n_fav, n_rec = len(artistas_ev & favoritos), len(artistas_ev & recomendados)
        if n_fav or n_rec:
            motivo = (f"Actúan {n_fav} de tus artistas favoritos" if n_fav
                      else f"Actúan {n_rec} artistas que te pueden gustar")
            candidatos.append((n_fav + 0.5 * n_rec, ev, datos.get("titulo"), motivo))
    maximo = max((c[0] for c in candidatos), default=0)
    return [EventoRecomendadoDTO(evento_id=ev, titulo=titulo, puntuacion=round(puntos / maximo, 4), motivo=motivo)
            for puntos, ev, titulo, motivo in sorted(candidatos, reverse=True)]


def _mi_escaleta(favoritos: set[str], evento_id: str | None) -> list[PaseMiEscaletaDTO]:
    pases = [p for ev, lista in _pases_por_evento().items() if not evento_id or ev == evento_id
             for p in lista if p["artista_id"] in favoritos and p["estado"] != "CANCELADO"]
    pases.sort(key=lambda p: p["inicio"])
    return [PaseMiEscaletaDTO(pase_id=p["pase_id"], artista=p["artista"], escenario=p["escenario"],
                              inicio=p["inicio"], fin=p["fin"],
                              solapa_con=[q["pase_id"] for q in pases if q is not p
                                          and q["inicio"] < p["fin"] and p["inicio"] < q["fin"]])
            for p in pases]


def para_cliente(usuario_id: str, evento_id: str | None) -> dict:
    clave = f"recomendaciones:{usuario_id}"
    if not evento_id and (guardadas := cache.obtener(clave)) is not None:
        return guardadas

    dao = _dao()
    favoritos = {f["artista_id"] for f in dao.buscar("favoritos", {"usuario_id": usuario_id})}
    artistas = _artistas_recomendados(dao, favoritos, usuario_id) if favoritos else []
    if not favoritos:  # sin favoritos todavía: lo más popular
        artistas = [ArtistaRecomendadoDTO(artista_id=p.artista_id, artista=p.artista, puntuacion=0.0,
                                          motivo="De los más populares del festival") for p in popularidad()]
    resultado = RecomendacionesClienteDTO(
        generadas_en=datetime.now(timezone.utc),
        eventos=_eventos_recomendados(favoritos, {a.artista_id for a in artistas}, evento_id),
        artistas=artistas,
        mi_escaleta=_mi_escaleta(favoritos, evento_id),
    ).model_dump(mode="json")

    if not evento_id:
        dao.guardar("recomendaciones", usuario_id, resultado | {"usuario_id": usuario_id})
        cache.guardar(clave, resultado, SEGUNDOS_CACHE_RECOMENDACIONES)
    return resultado


# ── Visitante ───────────────────────────────────────────────

def populares() -> RecomendacionesPopularesDTO:
    ranking = popularidad(limite=10)
    puntos = {a.artista_id: a.favoritos + a.visitas for a in popularidad(limite=1000)}
    pases = _pases_por_evento()
    eventos = [(sum(puntos.get(a, 0) for a in {p["artista_id"] for p in pases[ev]}), ev, datos.get("titulo"))
               for ev, datos in _eventos_visibles().items()]
    maximo = max((e[0] for e in eventos), default=0) or 1
    return RecomendacionesPopularesDTO(
        eventos=[EventoRecomendadoDTO(evento_id=ev, titulo=titulo, puntuacion=round(p / maximo, 4),
                                      # Sin seguidores ni visitas no se puede decir que sus artistas sean populares
                                      motivo="Sus artistas son de los más seguidos" if p
                                      else "Próxima edición del festival")
                 for p, ev, titulo in sorted(eventos, reverse=True)],
        artistas=ranking,
    )


# ── Proveedor ───────────────────────────────────────────────

def espacios_para_proveedor(proveedor_id: str, evento_id: str | None) -> list[EspacioRecomendadoDTO]:
    dao = _dao()
    espacios = {e["_id"]: e for e in dao.buscar("espacios")}
    alquileres = dao.buscar("alquileres")
    ocupados = {a["espacio_id"] for a in alquileres if a.get("estado") in ("APROBADO", "ACTIVO")}
    # Tipos que ya ha alquilado antes; si es nuevo, todos los alquilables
    tipos_previos = {espacios[a["espacio_id"]]["tipo"] for a in alquileres
                     if a.get("proveedor_id") == proveedor_id and a["espacio_id"] in espacios}
    estados = {e["_id"]: e.get("estado") for e in dao.buscar("eventos")}

    ocupacion_tipo: dict[str, list[int]] = {}
    for o in dao.buscar("metricas_ocupacion"):
        total, alquilados = ocupacion_tipo.setdefault(o["tipo_espacio"], [0, 0])
        ocupacion_tipo[o["tipo_espacio"]] = [total + o.get("total", 0), alquilados + o.get("alquilados", 0)]

    candidatos = [e for e in espacios.values()
                  if e.get("tipo") != "ESCENARIO" and e.get("disponible") and e["_id"] not in ocupados
                  and (not tipos_previos or e["tipo"] in tipos_previos)
                  and (not evento_id or e["evento_id"] == evento_id)
                  and estados.get(e["evento_id"]) in ESTADOS_VISIBLES]
    if not candidatos:
        return []

    afluencia = {ev: entradas_netas(ev) for ev in {e["evento_id"] for e in candidatos}}
    max_afluencia = max(afluencia.values()) or 1
    precios = [e.get("precio_alquiler") or 0 for e in candidatos]
    max_precio = max(precios) or 1
    media_precio = sum(precios) / len(precios)

    resultado = []
    for e in candidatos:
        total, alquilados = ocupacion_tipo.get(e["tipo"], [0, 0])
        demanda = alquilados / total if total else 0
        precio = e.get("precio_alquiler") or 0
        factores = {
            "Evento con mucho público previsto": 0.5 * afluencia[e["evento_id"]] / max_afluencia,
            f"Tipo de espacio muy demandado ({demanda:.0%} alquilado)": 0.3 * demanda,
            "Precio por debajo de la media": 0.2 * (1 - precio / max_precio) if precio < media_precio else 0,
        }
        resultado.append(EspacioRecomendadoDTO(
            espacio_id=e["_id"], evento_id=e["evento_id"], tipo=e["tipo"], precio_alquiler=e.get("precio_alquiler"),
            afluencia_estimada=afluencia[e["evento_id"]], puntuacion=round(sum(factores.values()), 4),
            motivo=max(factores, key=factores.get)))
    return sorted(resultado, key=lambda r: r.puntuacion, reverse=True)[:10]


# ── Interacciones ───────────────────────────────────────────

def registrar_interacciones(usuario_id: str | None, lote: LoteInteraccionesDTO) -> int:
    sujeto = usuario_id or (str(lote.sesion_id) if lote.sesion_id else None)
    if not sujeto:
        raise ErrorApi(400, "PETICION_NO_VALIDA", "Hace falta un token o un sesion_id")
    dao = _dao()
    dao.guardar_interacciones([{"sujeto": sujeto, "accion": i.accion.value, "objetivo_id": i.objetivo_id,
                                "fecha": i.fecha} for i in lote.interacciones])
    for i in lote.interacciones:
        # El endpoint es público: solo cuentan las visitas a artistas que existen
        if i.accion.value == "VER_ARTISTA" and dao.obtener("artistas", i.objetivo_id):
            dao.incrementar("popularidad_artistas", {"_id": i.objetivo_id}, {"visitas": 1, "favoritos": 0})
            dao.incrementar("popularidad_diaria", {"artista_id": i.objetivo_id, "fecha": i.fecha.date().isoformat()},
                            {"visitas": 1, "favoritos": 0})
    return len(lote.interacciones)
