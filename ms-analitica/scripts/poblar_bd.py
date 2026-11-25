# ms-analitica/scripts/poblar_bd.py
# ms-analitica no tiene datos propios: todo sale de los eventos de los demás servicios.
# Este script genera eventos de ejemplo (con los mismos identificadores que los datos de prueba
# de los otros microservicios) y los procesa igual que llegarían por RabbitMQ.
# Uso: python scripts/poblar_bd.py   (desde la carpeta ms-analitica)
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.database import crear_indices  # noqa: E402
from eventos.procesador import procesar  # noqa: E402

AHORA = datetime.now(timezone.utc)


def sobre(tipo: str, datos: dict, dias_atras: int = 0) -> dict:
    # id_evento determinista: volver a ejecutar el script no duplica nada (idempotencia)
    clave = f"{tipo}|{sorted(datos.items())}|{dias_atras}"
    return {"id_evento": str(uuid.uuid5(uuid.NAMESPACE_URL, clave)), "tipo": tipo, "version": 1,
            "origen": "poblar_bd", "fecha": (AHORA - timedelta(days=dias_atras)).isoformat(),
            "correlation_id": str(uuid.uuid4()), "datos": datos}


def artista(n: int) -> str:
    return f"22222222-2222-4222-8222-{n:012d}"


ARTISTAS = {1: ("Martin Garrix", ["house", "progressive"]), 2: ("Tiësto", ["house", "trance"]),
            3: ("David Guetta", ["house", "pop"]), 4: ("Armin van Buuren", ["trance", "progressive"]),
            5: ("Above & Beyond", ["trance"]), 9: ("Skrillex", ["dubstep", "bass"]),
            10: ("Diplo", ["moombahton", "bass"]), 11: ("Alok", ["brazilian bass", "house"])}


def pase(n_artista: int, escenario: str, inicio: str, fin: str) -> dict:
    return {"pase_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"pase-{n_artista}-{inicio}")),
            "artista_id": artista(n_artista), "artista": ARTISTAS[n_artista][0], "escenario": escenario,
            "inicio": inicio, "fin": fin, "estado": "CONFIRMADO"}


eventos = []
for ev, titulo, ini, fin in (("evento-belgium", "Subsonic Belgium", "2026-07-18", "2026-07-27"),
                             ("evento-thailand", "Subsonic Thailand", "2026-08-08", "2026-08-17"),
                             ("evento-brasil", "Subsonic Brasil", "2026-09-12", "2026-09-21")):
    eventos.append(sobre("espacios.evento.publicado", {"evento_id": ev, "titulo": titulo, "fecha_inicio": ini,
                                                       "fecha_fin": fin, "estado": "PUBLICADO"}, 30))

espacios = [
    ("espacio-belgium-main-stage", "evento-belgium", "ESCENARIO", "Main Stage", 15000, None),
    ("espacio-belgium-trance-stage", "evento-belgium", "ESCENARIO", "Trance Stage", 8000, None),
    ("espacio-001", "evento-belgium", "FOOD_BEVERAGE", "Puesto F&B entrada", None, 1500.0),
    ("espacio-002", "evento-belgium", "MERCHANDISING", "Puesto merch central", None, 900.0),
    ("espacio-003", "evento-thailand", "FOOD_BEVERAGE", "Chiringuito playa", None, 1100.0),
]
for esp_id, ev, tipo, nombre, aforo, precio in espacios:
    eventos.append(sobre("espacios.espacio.creado", {"espacio_id": esp_id, "evento_id": ev, "tipo": tipo,
                                                     "nombre": nombre, "aforo": aforo, "precio_alquiler": precio,
                                                     "disponible": tipo != "ESCENARIO"}, 30))

for n, (nombre, generos) in ARTISTAS.items():
    eventos.append(sobre("escaleta.artista.creado", {"artista_id": artista(n), "nombre": nombre,
                                                     "generos": generos}, 30))

eventos.append(sobre("escaleta.publicada", {"evento_id": "evento-belgium", "version": 1, "dias": [
    {"fecha": "2026-07-18", "escenarios": [
        {"espacio_id": "espacio-belgium-main-stage", "nombre": "Main Stage", "pases": [
            pase(1, "Main Stage", "2026-07-18T20:00:00Z", "2026-07-18T22:00:00Z"),
            pase(2, "Main Stage", "2026-07-18T22:00:00Z", "2026-07-19T00:00:00Z"),
            pase(3, "Main Stage", "2026-07-19T00:00:00Z", "2026-07-19T02:00:00Z")]},
        {"espacio_id": "espacio-belgium-trance-stage", "nombre": "Trance Stage", "pases": [
            pase(4, "Trance Stage", "2026-07-18T19:00:00Z", "2026-07-18T21:00:00Z"),
            pase(5, "Trance Stage", "2026-07-18T21:00:00Z", "2026-07-18T23:00:00Z")]},
    ]}]}, 20))

# Usuarios, favoritos y compras repartidas en los últimos días
clientes = ["uid-cliente-david"] + [f"uid-cliente-{i}" for i in range(1, 8)]
for i, cliente in enumerate(clientes):
    eventos.append(sobre("usuarios.usuario.registrado", {"usuario_id": cliente, "rol": "CLIENTE"}, 25 - i))
    for n in ((4, 5) if i % 2 else (1, 2, 3))[: 1 + i % 3]:
        eventos.append(sobre("usuarios.favorito.anadido", {"usuario_id": cliente, "artista_id": artista(n),
                                                           "artista_nombre": ARTISTAS[n][0]}, i))
    tipo, precio = (("WEEKEND", 199.0), ("DAY", 89.0), ("VIP", 399.0))[i % 3]
    eventos.append(sobre("usuarios.entrada.comprada", {"entrada_id": f"entrada-seed{i}", "usuario_id": cliente,
                                                       "evento_id": "evento-belgium", "tipo_pase": tipo,
                                                       "precio_pagado": precio}, i))
eventos.append(sobre("usuarios.entrada.cancelada", {"entrada_id": "entrada-seed7", "usuario_id": clientes[7],
                                                    "evento_id": "evento-belgium", "tipo_pase": "DAY",
                                                    "precio_pagado": 89.0}, 0))
eventos.append(sobre("usuarios.usuario.registrado", {"usuario_id": "uid-proveedor-ana", "rol": "PROVEEDOR"}, 28))
eventos.append(sobre("espacios.alquiler.aprobado", {"alquiler_id": "alq-seed-1", "espacio_id": "espacio-001",
                                                    "evento_id": "evento-belgium", "proveedor_id": "uid-proveedor-ana",
                                                    "importe": 19500.0, "estado": "APROBADO"}, 10))

# Tienda
eventos.append(sobre("tienda.pedido.creado", {"pedido_id": "pedido-seed1", "usuario_id": "uid-cliente-david",
                                              "estado": "PAGADO", "importe_total": 64.97, "lineas": [
                                                  {"variante_id": "v1", "producto_id": "camiseta-2026", "talla": "M",
                                                   "cantidad": 1, "precio_unitario": 29.99},
                                                  {"variante_id": "v2", "producto_id": "gorra-black",
                                                   "talla": "UNICA", "cantidad": 1, "precio_unitario": 19.99}]}, 2))
eventos.append(sobre("tienda.stock.bajo", {"variante_id": "v9", "producto_id": "camiseta-belgium-2026",
                                           "talla": "M", "stock": 3}, 1))

crear_indices()
nuevos = sum(procesar(e) for e in eventos)
print(f"[OK] {nuevos} eventos procesados ({len(eventos) - nuevos} ya estaban procesados)")
