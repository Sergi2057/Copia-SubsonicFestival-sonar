# ms-escaleta/scripts/poblar_bd.py
# Datos de prueba iniciales: el campo "horarios" de los festivales de la versión monolítica pasa a
# artistas, slots y pases, y se publica la versión 1 de cada escaleta.
# Los identificadores de eventos y escenarios coinciden con los de ms-espacios.
# Uso: python scripts/poblar_bd.py   (desde la carpeta ms-escaleta)
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.database import SessionLocal, crear_tablas  # noqa: E402
from eventos.publicador import publicar  # noqa: E402
from sqlalchemy import select  # noqa: E402
from model.models import Artista, Escenario, EventoReplica, Pase, Slot  # noqa: E402
from service import escaleta_service  # noqa: E402
from service.artista_service import datos_artista  # noqa: E402


def uid_artista(n: int) -> uuid.UUID:
    # UUID fijos para poder usarlos desde ms-usuarios (favoritos) y ms-analitica
    return uuid.UUID(f"22222222-2222-4222-8222-{n:012d}")


ARTISTAS = {
    "Martin Garrix": (1, ["house", "progressive"], "Países Bajos"),
    "Tiësto": (2, ["house", "trance"], "Países Bajos"),
    "David Guetta": (3, ["house", "pop"], "Francia"),
    "Armin van Buuren": (4, ["trance", "progressive"], "Países Bajos"),
    "Above & Beyond": (5, ["trance"], "Reino Unido"),
    "Hardwell": (6, ["big room", "techno"], "Países Bajos"),
    "Afrojack": (7, ["house"], "Países Bajos"),
    "Steve Aoki": (8, ["electro house"], "Estados Unidos"),
    "Skrillex": (9, ["dubstep", "bass"], "Estados Unidos"),
    "Diplo": (10, ["moombahton", "bass"], "Estados Unidos"),
    "Alok": (11, ["brazilian bass", "house"], "Brasil"),
    "Anitta": (12, ["funk", "pop"], "Brasil"),
}

# evento -> (primer día, zona horaria, {escenario: [(artista, "HH:MM", horas)]})
HORARIOS = {
    "evento-belgium": ("2026-07-18", 2, {
        "Main Stage": [("Martin Garrix", "22:00", 2), ("Tiësto", "00:00", 2), ("David Guetta", "02:00", 2)],
        "Trance Stage": [("Armin van Buuren", "21:00", 2), ("Above & Beyond", "23:00", 2)],
    }),
    "evento-thailand": ("2026-08-08", 7, {
        "Ocean Stage": [("Hardwell", "21:00", 2), ("Afrojack", "23:00", 2), ("Steve Aoki", "01:00", 2)],
        "Jungle Stage": [("Skrillex", "22:00", 2), ("Diplo", "00:00", 2)],
    }),
    "evento-brasil": ("2026-09-12", -3, {
        "Carnival Stage": [("Alok", "21:00", 2), ("Anitta", "23:00", 2), ("David Guetta", "01:00", 2)],
    }),
}


def id_escenario(evento_id: str, nombre: str) -> str:
    return f"espacio-{evento_id.removeprefix('evento-')}-{nombre.lower().replace(' ', '-')}"


crear_tablas()
db = SessionLocal()
try:
    nuevos = []
    for nombre, (n, generos, pais) in ARTISTAS.items():
        if not db.get(Artista, uid_artista(n)):
            nuevos.append(Artista(id=uid_artista(n), nombre=nombre, generos=generos, pais=pais, redes={}))
            db.add(nuevos[-1])
    db.commit()
    # Como al crearlos por la API: ms-analitica y ms-usuarios se enteran por el evento (géneros, nombre)
    for artista in nuevos:
        publicar("escaleta.artista.creado", datos_artista(artista))

    for evento_id, (primer_dia, zona, escenarios) in HORARIOS.items():
        # Ya poblado si tiene slots. No basta con mirar la réplica del evento: en el entorno completo
        # la crean antes los eventos espacios.evento.publicado que envía el poblado de ms-espacios
        if db.scalar(select(Slot.id).where(Slot.evento_id == evento_id).limit(1)):
            continue
        # Réplicas (normalmente las alimentan los eventos espacios.evento.* y espacios.espacio.*;
        # se crean aquí por si este servicio se puebla sin ms-espacios)
        if not db.get(EventoReplica, evento_id):
            db.add(EventoReplica(evento_id=evento_id, estado="PUBLICADO"))
        tz = timezone(timedelta(hours=zona))
        for nombre_escenario, actuaciones in escenarios.items():
            espacio_id = id_escenario(evento_id, nombre_escenario)
            if not db.get(Escenario, espacio_id):
                db.add(Escenario(espacio_id=espacio_id, evento_id=evento_id, nombre=nombre_escenario, aforo=15000))
            db.flush()
            for artista, hora, horas in actuaciones:
                inicio = datetime.fromisoformat(f"{primer_dia}T{hora}:00").replace(tzinfo=tz)
                if inicio.hour < 12:  # después de medianoche: noche siguiente
                    inicio += timedelta(days=1)
                slot = Slot(evento_id=evento_id, espacio_id=espacio_id, inicio=inicio.astimezone(timezone.utc),
                            fin=(inicio + timedelta(hours=horas)).astimezone(timezone.utc), tipo="ACTUACION")
                db.add(slot)
                db.flush()
                db.add(Pase(slot_id=slot.id, artista_id=uid_artista(ARTISTAS[artista][0]), formato="DJ_SET",
                            estado="CONFIRMADO", version=1))
        db.commit()
        escaleta_service.publicar_escaleta(db, evento_id, "seed")

    db.commit()
    print("[OK] Artistas, escenarios, slots y pases creados; escaletas publicadas (versión 1)")
finally:
    db.close()
