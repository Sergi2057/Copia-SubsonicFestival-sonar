# ms-analitica/model/dao/analitica_dao.py
# Acceso a las colecciones de analitica_db.
# Colecciones de la especificación: eventos_dominio, interacciones, metricas_ventas, metricas_ocupacion,
# metricas_tienda, popularidad_artistas, recomendaciones y procesados.
# Réplicas auxiliares (también reconstruibles a partir de los eventos): eventos, espacios, artistas,
# escaletas, favoritos, usuarios, alquileres, asistencia, stock_bajo y popularidad_diaria.
from datetime import datetime, timezone
from pymongo.database import Database
from pymongo.errors import DuplicateKeyError


class AnaliticaDAO:
    def __init__(self, db: Database):
        self.db = db

    # ── Idempotencia y registro histórico ────────────────────

    def marcar_procesado(self, id_evento: str) -> bool:
        """False si el evento ya se había procesado (mensaje repetido)."""
        try:
            self.db.procesados.insert_one({"_id": id_evento, "procesado_en": datetime.now(timezone.utc)})
            return True
        except DuplicateKeyError:
            return False

    def guardar_evento_dominio(self, sobre: dict) -> None:
        self.db.eventos_dominio.insert_one({k: sobre.get(k) for k in ("id_evento", "tipo", "origen", "fecha", "datos")})

    # ── Réplicas ─────────────────────────────────────────────

    def guardar(self, coleccion: str, _id: str, datos: dict) -> None:
        self.db[coleccion].update_one({"_id": _id}, {"$set": datos}, upsert=True)

    def obtener(self, coleccion: str, _id: str) -> dict | None:
        return self.db[coleccion].find_one({"_id": _id})

    def buscar(self, coleccion: str, filtro: dict | None = None) -> list[dict]:
        return list(self.db[coleccion].find(filtro or {}))

    def borrar(self, coleccion: str, filtro: dict) -> None:
        self.db[coleccion].delete_many(filtro)

    def contar(self, coleccion: str, filtro: dict | None = None) -> int:
        return self.db[coleccion].count_documents(filtro or {})

    # ── Métricas agregadas ($inc con upsert) ─────────────────

    def incrementar(self, coleccion: str, clave: dict, incrementos: dict, valores: dict | None = None) -> None:
        cambio = {"$inc": incrementos}
        if valores:
            cambio["$set"] = valores
        self.db[coleccion].update_one(clave, cambio, upsert=True)

    # ── Interacciones ────────────────────────────────────────

    def guardar_interacciones(self, documentos: list[dict]) -> None:
        if documentos:
            self.db.interacciones.insert_many(documentos)

    # ── RGPD ─────────────────────────────────────────────────

    def anonimizar_usuario(self, usuario_id: str) -> None:
        self.db.favoritos.delete_many({"usuario_id": usuario_id})
        self.db.recomendaciones.delete_many({"usuario_id": usuario_id})
        self.db.usuarios.delete_many({"_id": usuario_id})
        self.db.interacciones.update_many({"sujeto": usuario_id}, {"$set": {"sujeto": "anonimizado"}})
        self.db.eventos_dominio.update_many({"datos.usuario_id": usuario_id},
                                            {"$set": {"datos.usuario_id": "anonimizado"}})
        self.db.alquileres.update_many({"proveedor_id": usuario_id}, {"$set": {"proveedor_id": "anonimizado"}})
