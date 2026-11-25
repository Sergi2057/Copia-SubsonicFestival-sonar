# ms-espacios/scripts/poblar_bd.py
# Datos de prueba iniciales (los festivales de la versión monolítica, ya separados en recintos,
# eventos, tarifas y espacios). Los identificadores coinciden con los de los demás microservicios.
# Uso: python scripts/poblar_bd.py   (desde la carpeta ms-espacios)
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.database import SessionLocal, crear_tablas  # noqa: E402
from eventos.publicador import publicar  # noqa: E402
from model.models import Espacio, Evento, Proveedor, Recinto, TarifaAcceso  # noqa: E402
from service.espacio_service import _datos_espacio  # noqa: E402
from service.evento_service import _datos_evento  # noqa: E402

# UUID fijos para que otros servicios puedan referenciarlos
RECINTOS = [
    Recinto(id=uuid.UUID("11111111-1111-4111-8111-000000000001"), nombre="Dreamville Grounds",
            ciudad="Boom", pais="Bélgica", latitud=51.0911, longitud=4.3707, aforo_maximo=70000),
    Recinto(id=uuid.UUID("11111111-1111-4111-8111-000000000002"), nombre="Maya Festival Site",
            ciudad="Pattaya", pais="Tailandia", latitud=12.9236, longitud=100.8825, aforo_maximo=40000),
    Recinto(id=uuid.UUID("11111111-1111-4111-8111-000000000003"), nombre="Sambódromo",
            ciudad="São Paulo", pais="Brasil", latitud=-23.5175, longitud=-46.6458, aforo_maximo=30000),
]

EVENTOS = [
    (Evento(id="evento-belgium", titulo="Subsonic Belgium", pais="Bélgica", recinto_id=RECINTOS[0].id,
            fecha_inicio=date(2026, 7, 18), fecha_fin=date(2026, 7, 27), imagen_url="/subsonic_belgica.jpg",
            descripcion="La experiencia definitiva de música electrónica en los campos de Bélgica.",
            tags=["techno", "house", "trance", "belgium", "verano"],
            servicios_generales=["Zona de acampada premium", "Food trucks internacionales", "Servicio médico 24h",
                                 "Transporte lanzadera", "Consigna de equipaje", "Zona de descanso"],
            estado="PUBLICADO"),
     {"DAY": (89, 20000), "WEEKEND": (199, 20000), "VIP": (399, 2000)},
     ["Main Stage", "Trance Stage"]),
    (Evento(id="evento-thailand", titulo="Subsonic Thailand", pais="Tailandia", recinto_id=RECINTOS[1].id,
            fecha_inicio=date(2026, 8, 8), fecha_fin=date(2026, 8, 17), imagen_url="/subsonic_tailandia.jpg",
            descripcion="Sumérgete en la vibrante escena electrónica tailandesa con vistas al mar.",
            tags=["techno", "house", "asia", "verano", "playa"],
            servicios_generales=["Zona VIP con piscina", "Restaurantes temáticos", "Servicio médico 24h"],
            estado="PUBLICADO"),
     {"DAY": (75, 15000), "WEEKEND": (160, 15000)},
     ["Ocean Stage", "Jungle Stage"]),
    (Evento(id="evento-brasil", titulo="Subsonic Brasil", pais="Brasil", recinto_id=RECINTOS[2].id,
            fecha_inicio=date(2026, 9, 12), fecha_fin=date(2026, 9, 21), imagen_url="/subsonic_brasil.jpg",
            descripcion="La energía de Brasil combinada con los mejores ritmos electrónicos del planeta.",
            tags=["techno", "house", "brasil", "latinoamerica"],
            servicios_generales=["Zona de samba interactiva", "Gastronomía brasileña", "Servicio médico 24h"],
            estado="PUBLICADO"),
     {"DAY": (65, 12000), "WEEKEND": (140, 12000)},
     ["Carnival Stage"]),
]


def id_escenario(evento_id: str, nombre: str) -> str:
    # ej: evento-belgium + Main Stage -> espacio-belgium-main-stage
    return f"espacio-{evento_id.removeprefix('evento-')}-{nombre.lower().replace(' ', '-')}"


crear_tablas()
db = SessionLocal()
try:
    for recinto in RECINTOS:
        if not db.get(Recinto, recinto.id):
            db.add(recinto)
    db.flush()

    eventos_nuevos, espacios_nuevos = [], []
    for evento, tarifas, escenarios in EVENTOS:
        if db.get(Evento, evento.id):
            continue
        db.add(evento)
        eventos_nuevos.append(evento)
        for tipo, (precio, cupo) in tarifas.items():
            db.add(TarifaAcceso(evento_id=evento.id, tipo_pase=tipo, precio=precio, cupo_total=cupo))
        for nombre in escenarios:
            espacios_nuevos.append(Espacio(id=id_escenario(evento.id, nombre), evento_id=evento.id,
                                           tipo="ESCENARIO", nombre=nombre, aforo=15000, disponible=False))
            db.add(espacios_nuevos[-1])

    # Espacios alquilables (los de la versión monolítica)
    alquilables = [
        Espacio(id="espacio-001", evento_id="evento-belgium", tipo="FOOD_BEVERAGE", nombre="Puesto F&B entrada",
                zona="Zona A - Entrada Principal", tamano="Grande", dimensiones="10x10m", precio_alquiler=1500,
                servicios=["electricidad", "agua", "mostrador"], disponible=True),
        Espacio(id="espacio-002", evento_id="evento-belgium", tipo="MERCHANDISING", nombre="Puesto merch central",
                zona="Zona B - Central", tamano="Mediano", dimensiones="6x4m", precio_alquiler=900,
                servicios=["electricidad"], disponible=True),
        Espacio(id="espacio-003", evento_id="evento-thailand", tipo="FOOD_BEVERAGE", nombre="Chiringuito playa",
                zona="Zona Playa", tamano="Mediano", dimensiones="8x6m", precio_alquiler=1100,
                servicios=["electricidad", "agua"], disponible=True),
    ]
    for espacio in alquilables:
        if not db.get(Espacio, espacio.id):
            db.add(espacio)
            espacios_nuevos.append(espacio)

    # Réplica de proveedores (en producción la alimentan los eventos usuarios.proveedor.*)
    if not db.get(Proveedor, "uid-proveedor-ana"):
        db.add(Proveedor(proveedor_id="uid-proveedor-ana", nombre_comercial="Ana Food Truck",
                         tipo_servicio="food-truck", activo=True))

    db.commit()

    # Como al crearlos por la API: los demás servicios se enteran por los eventos (ms-analitica usa el
    # título, el aforo y los espacios; ms-escaleta y ms-tienda, el estado del evento)
    for evento in eventos_nuevos:
        publicar("espacios.evento.publicado", _datos_evento(evento))
    for espacio in espacios_nuevos:
        publicar("espacios.espacio.creado", _datos_espacio(espacio))
    print("[OK] Recintos, eventos, tarifas, espacios y proveedores creados")
finally:
    db.close()
