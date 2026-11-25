# ms-analitica/config/database.py
# Conexión a MongoDB (analitica_db). En los tests se usa mongomock (en memoria).
from functools import lru_cache
from pymongo import ASCENDING, DESCENDING
from pymongo.database import Database
from config.settings import MONGO_DB, MONGO_URL


@lru_cache
def get_db() -> Database:
    if MONGO_URL.startswith("mongomock://"):
        import mongomock
        cliente = mongomock.MongoClient()
    else:
        from pymongo import MongoClient
        cliente = MongoClient(MONGO_URL, serverSelectionTimeoutMS=3000, tz_aware=True)
    return cliente[MONGO_DB]


def crear_indices() -> None:
    db = get_db()
    db.eventos_dominio.create_index([("tipo", ASCENDING), ("fecha", DESCENDING)])
    db.interacciones.create_index([("objetivo_id", ASCENDING), ("fecha", DESCENDING)])
    db.metricas_ventas.create_index([("evento_id", ASCENDING), ("fecha", ASCENDING), ("tipo_pase", ASCENDING)],
                                    unique=True)
    db.metricas_ocupacion.create_index([("evento_id", ASCENDING), ("tipo_espacio", ASCENDING)], unique=True)
    db.metricas_tienda.create_index([("producto_id", ASCENDING), ("talla", ASCENDING), ("fecha", ASCENDING)],
                                    unique=True)
    db.popularidad_diaria.create_index([("artista_id", ASCENDING), ("fecha", ASCENDING)], unique=True)
    db.favoritos.create_index([("usuario_id", ASCENDING), ("artista_id", ASCENDING)], unique=True)
    db.espacios.create_index([("evento_id", ASCENDING)])
