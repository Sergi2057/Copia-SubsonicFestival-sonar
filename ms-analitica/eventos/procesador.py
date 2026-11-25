# ms-analitica/eventos/procesador.py
# Procesa los eventos de dominio del resto de servicios (sobre común de la memoria, apartado 4.1).
# - Idempotente: cada id_evento se procesa una sola vez (colección procesados).
# - Todo lo que calcula este servicio se puede reconstruir volviendo a procesar los eventos.
# Lo llama el consumidor de RabbitMQ (eventos/manejadores.py, cola ms-analitica con la clave "#"),
# y también los tests y scripts/poblar_bd.py.
import logging
from datetime import datetime, timezone
from model.dao.analitica_dao import AnaliticaDAO
from model.factory.factory_dao import DAOFactory
from service import cache

log = logging.getLogger("procesador")


def _fecha(sobre: dict) -> str:
    fecha = sobre.get("fecha")
    if isinstance(fecha, str):
        fecha = datetime.fromisoformat(fecha.replace("Z", "+00:00"))
    return (fecha or datetime.now(timezone.utc)).date().isoformat()


def invalidar_recomendaciones(dao: AnaliticaDAO, usuario_id: str) -> None:
    dao.borrar("recomendaciones", {"usuario_id": usuario_id})
    cache.borrar(f"recomendaciones:{usuario_id}")


# ── ms-usuarios ─────────────────────────────────────────────

def _entrada_comprada(dao, d, fecha):
    dao.incrementar("metricas_ventas", {"evento_id": d["evento_id"], "fecha": fecha, "tipo_pase": d["tipo_pase"]},
                    {"entradas": 1, "ingresos": d["precio_pagado"], "cancelaciones": 0})


def _entrada_cancelada(dao, d, fecha):
    dao.incrementar("metricas_ventas", {"evento_id": d["evento_id"], "fecha": fecha, "tipo_pase": d["tipo_pase"]},
                    {"entradas": 0, "ingresos": -d["precio_pagado"], "cancelaciones": 1})


def _entrada_validada(dao, d, fecha):
    dao.incrementar("asistencia", {"evento_id": d["evento_id"], "fecha": fecha}, {"validadas": 1})


def _usuario_registrado(dao, d, fecha):
    dao.guardar("usuarios", d["usuario_id"], {"rol": d.get("rol"), "registrado_en": fecha})


def _usuario_eliminado(dao, d, fecha):
    dao.anonimizar_usuario(d["usuario_id"])
    cache.borrar(f"recomendaciones:{d['usuario_id']}")


def _favorito_anadido(dao, d, fecha):
    clave = {"usuario_id": d["usuario_id"], "artista_id": d["artista_id"]}
    if dao.contar("favoritos", clave):
        return
    dao.db.favoritos.insert_one(clave | {"creado_en": fecha})
    nombre = {"artista": d["artista_nombre"]} if d.get("artista_nombre") else None
    dao.incrementar("popularidad_artistas", {"_id": d["artista_id"]}, {"favoritos": 1, "visitas": 0}, nombre)
    dao.incrementar("popularidad_diaria", {"artista_id": d["artista_id"], "fecha": fecha},
                    {"favoritos": 1, "visitas": 0})
    invalidar_recomendaciones(dao, d["usuario_id"])


def _favorito_eliminado(dao, d, fecha):
    clave = {"usuario_id": d["usuario_id"], "artista_id": d["artista_id"]}
    if not dao.contar("favoritos", clave):
        return
    dao.borrar("favoritos", clave)
    dao.incrementar("popularidad_artistas", {"_id": d["artista_id"]}, {"favoritos": -1})
    dao.incrementar("popularidad_diaria", {"artista_id": d["artista_id"], "fecha": fecha}, {"favoritos": -1})
    invalidar_recomendaciones(dao, d["usuario_id"])


# ── ms-espacios ─────────────────────────────────────────────

def _evento(dao, d, fecha):
    dao.guardar("eventos", d["evento_id"], {k: d.get(k) for k in ("titulo", "pais", "fecha_inicio", "fecha_fin",
                                                                   "estado")})


def _cuenta_en_ocupacion(espacio: dict | None) -> bool:
    return bool(espacio) and espacio.get("tipo") != "ESCENARIO"


def _espacio_guardado(dao, d, fecha):
    anterior = dao.obtener("espacios", d["espacio_id"])
    dao.guardar("espacios", d["espacio_id"], {k: d.get(k) for k in ("evento_id", "tipo", "nombre", "zona", "aforo",
                                                                     "precio_alquiler", "disponible")})
    if not anterior and _cuenta_en_ocupacion(d):
        dao.incrementar("metricas_ocupacion", {"evento_id": d["evento_id"], "tipo_espacio": d["tipo"]},
                        {"total": 1, "alquilados": 0, "ingresos_alquiler": 0})


def _espacio_eliminado(dao, d, fecha):
    anterior = dao.obtener("espacios", d["espacio_id"])
    dao.borrar("espacios", {"_id": d["espacio_id"]})
    if _cuenta_en_ocupacion(anterior):
        dao.incrementar("metricas_ocupacion", {"evento_id": anterior["evento_id"], "tipo_espacio": anterior["tipo"]},
                        {"total": -1})


def _alquiler(dao, d, fecha):
    dao.guardar("alquileres", d["alquiler_id"], {k: d.get(k) for k in ("espacio_id", "evento_id", "proveedor_id",
                                                                        "importe", "estado")})


def _alquiler_aprobado(dao, d, fecha):
    _alquiler(dao, d, fecha)
    espacio = dao.obtener("espacios", d["espacio_id"])
    if espacio:
        dao.incrementar("metricas_ocupacion", {"evento_id": d["evento_id"], "tipo_espacio": espacio["tipo"]},
                        {"alquilados": 1, "ingresos_alquiler": d["importe"]})


# ── ms-escaleta ─────────────────────────────────────────────

def _escaleta_publicada(dao, d, fecha):
    dao.guardar("escaletas", d["evento_id"], {"version": d["version"], "dias": d.get("dias", [])})


def _artista(dao, d, fecha):
    dao.guardar("artistas", d["artista_id"], {"nombre": d["nombre"], "generos": d.get("generos", [])})
    dao.guardar("popularidad_artistas", d["artista_id"], {"artista": d["nombre"]})


# ── ms-tienda ───────────────────────────────────────────────

def _sumar_pedido(dao, lineas, fecha, signo):
    for l in lineas:
        dao.incrementar("metricas_tienda", {"producto_id": l.get("producto_id"), "talla": l.get("talla"),
                                            "fecha": fecha},
                        {"unidades": signo * l["cantidad"], "ingresos": signo * l["cantidad"] * l["precio_unitario"]})


def _pedido_creado(dao, d, fecha):
    dao.guardar("pedidos", d["pedido_id"], {"lineas": d["lineas"], "fecha": fecha, "estado": d["estado"]})
    _sumar_pedido(dao, d["lineas"], fecha, 1)


def _pedido_actualizado(dao, d, fecha):
    pedido = dao.obtener("pedidos", d["pedido_id"])
    if d["estado"] == "CANCELADO" and pedido and pedido.get("estado") != "CANCELADO":
        _sumar_pedido(dao, pedido["lineas"], pedido["fecha"], -1)  # se descuenta del día en que se vendió
    if pedido:
        dao.guardar("pedidos", d["pedido_id"], {"estado": d["estado"]})


def _stock_bajo(dao, d, fecha):
    dao.guardar("stock_bajo", d["variante_id"], {"producto_id": d["producto_id"], "talla": d["talla"],
                                                 "stock": d["stock"], "fecha": fecha})


MANEJADORES = {
    "usuarios.entrada.comprada": _entrada_comprada,
    "usuarios.entrada.cancelada": _entrada_cancelada,
    "usuarios.entrada.validada": _entrada_validada,
    "usuarios.usuario.registrado": _usuario_registrado,
    "usuarios.usuario.eliminado": _usuario_eliminado,
    "usuarios.favorito.anadido": _favorito_anadido,
    "usuarios.favorito.eliminado": _favorito_eliminado,
    "espacios.evento.publicado": _evento,
    "espacios.evento.actualizado": _evento,
    "espacios.evento.cancelado": _evento,
    "espacios.espacio.creado": _espacio_guardado,
    "espacios.espacio.actualizado": _espacio_guardado,
    "espacios.espacio.eliminado": _espacio_eliminado,
    "espacios.alquiler.solicitado": _alquiler,
    "espacios.alquiler.aprobado": _alquiler_aprobado,
    "espacios.alquiler.rechazado": _alquiler,
    "espacios.alquiler.finalizado": _alquiler,
    "escaleta.publicada": _escaleta_publicada,
    "escaleta.artista.creado": _artista,
    "escaleta.artista.actualizado": _artista,
    "tienda.pedido.creado": _pedido_creado,
    "tienda.pedido.actualizado": _pedido_actualizado,
    "tienda.stock.bajo": _stock_bajo,
    # escaleta.pase.*, espacios.aforo.agotado…: solo se guardan en eventos_dominio
}


def procesar(sobre: dict) -> bool:
    """Procesa un evento. Devuelve False si ya se había procesado (mensaje repetido)."""
    dao = DAOFactory.get_analitica_dao()
    if not dao.marcar_procesado(sobre["id_evento"]):
        return False
    try:
        dao.guardar_evento_dominio(sobre)
        manejador = MANEJADORES.get(sobre["tipo"])
        if manejador:
            manejador(dao, sobre["datos"], _fecha(sobre))
    except Exception:
        # Se desmarca para que RabbitMQ lo vuelva a entregar (y acabe en la DLQ si sigue fallando)
        dao.borrar("procesados", {"_id": sobre["id_evento"]})
        log.exception("Error procesando %s %s", sobre.get("tipo"), sobre.get("id_evento"))
        raise
    return True
