# ms-escaleta/tests/test_escaleta.py
import asyncio
from config.database import SessionLocal
from conftest import ADMIN, CLIENTE
from service import escaleta_service
from service.difusor import Difusor

API = "/api/v1"
EVENTO = "evento-test"


def preparar(c, estado_evento="PUBLICADO"):
    """Réplicas de ms-espacios (como si hubieran llegado sus eventos) y dos artistas."""
    db = SessionLocal()
    escaleta_service.al_cambiar_estado_evento(db, EVENTO, estado_evento)
    for espacio_id, nombre in (("esc-main", "Main Stage"), ("esc-trance", "Trance Stage")):
        escaleta_service.al_cambiar_espacio(db, "espacios.espacio.creado", {
            "espacio_id": espacio_id, "evento_id": EVENTO, "tipo": "ESCENARIO", "nombre": nombre, "aforo": 1000})
    escaleta_service.al_cambiar_espacio(db, "espacios.espacio.creado", {  # no es escenario: se ignora
        "espacio_id": "esc-fb", "evento_id": EVENTO, "tipo": "FOOD_BEVERAGE", "nombre": "F&B"})
    db.close()
    artistas = [c.post(f"{API}/artistas", headers=ADMIN, json={"nombre": n, "generos": g}).json()
                for n, g in (("Tiësto", ["house", "trance"]), ("Armin van Buuren", ["trance"]))]
    return artistas


def slot(c, espacio="esc-main", inicio="2026-07-18T22:00:00+02:00", fin="2026-07-19T00:00:00+02:00"):
    return c.post(f"{API}/escaletas/{EVENTO}/slots", headers=ADMIN,
                  json={"espacio_id": espacio, "inicio": inicio, "fin": fin, "tipo": "ACTUACION"})


def test_slots_no_se_solapan(cliente_http):
    c = cliente_http
    preparar(c)
    assert slot(c).status_code == 201
    r = slot(c, inicio="2026-07-18T23:00:00+02:00", fin="2026-07-19T01:00:00+02:00")
    assert r.status_code == 409 and r.json()["codigo"] == "SLOT_SOLAPADO"
    assert slot(c, espacio="esc-trance", inicio="2026-07-18T23:00:00+02:00").status_code == 201  # otro escenario
    assert slot(c, espacio="esc-fb").status_code == 404  # no está en la réplica de escenarios
    assert slot(c, inicio="2026-07-18T22:00:00").status_code == 400  # sin zona horaria
    assert c.post(f"{API}/escaletas/{EVENTO}/slots", headers=CLIENTE, json={}).status_code == 403


def test_evento_no_publicado_no_admite_slots(cliente_http):
    c = cliente_http
    preparar(c, estado_evento="BORRADOR")
    assert slot(c).status_code == 409


def test_artista_no_puede_estar_en_dos_escenarios(cliente_http):
    c = cliente_http
    tiesto, armin = preparar(c)
    s1 = slot(c).json()
    s2 = slot(c, espacio="esc-trance", inicio="2026-07-18T23:00:00+02:00", fin="2026-07-19T01:00:00+02:00").json()
    assert c.post(f"{API}/slots/{s1['id']}/pases", headers=ADMIN,
                  json={"artista_id": tiesto["id"], "formato": "DJ_SET"}).status_code == 201
    assert c.post(f"{API}/slots/{s1['id']}/pases", headers=ADMIN,
                  json={"artista_id": armin["id"], "formato": "DJ_SET"}).status_code == 409  # slot ocupado
    r = c.post(f"{API}/slots/{s2['id']}/pases", headers=ADMIN, json={"artista_id": tiesto["id"], "formato": "LIVE"})
    assert r.status_code == 409 and r.json()["codigo"] == "ARTISTA_SOLAPADO"
    # No se puede borrar un artista con pases
    assert c.delete(f"{API}/artistas/{tiesto['id']}", headers=ADMIN).status_code == 409


def test_version_optimista_y_estados(cliente_http):
    c = cliente_http
    tiesto, _ = preparar(c)
    s1 = slot(c).json()
    pase = c.post(f"{API}/slots/{s1['id']}/pases", headers=ADMIN,
                  json={"artista_id": tiesto["id"], "formato": "DJ_SET"}).json()
    url = f"{API}/pases/{pase['id']}"
    # Retraso de media hora
    r = c.patch(url, headers=ADMIN, json={"version": 1, "inicio": "2026-07-18T22:30:00+02:00",
                                          "fin": "2026-07-19T00:30:00+02:00", "motivo": "Retraso técnico"})
    assert r.status_code == 200 and r.json()["version"] == 2
    # Otro admin con la versión antigua -> 409
    r = c.patch(url, headers=ADMIN, json={"version": 1, "estado": "CONFIRMADO"})
    assert r.status_code == 409 and r.json()["detalles"]["version_actual"] == 2
    assert c.patch(url, headers=ADMIN, json={"version": 2, "estado": "FINALIZADO"}).status_code == 409
    assert c.patch(url, headers=ADMIN, json={"version": 2, "estado": "CANCELADO"}).json()["estado"] == "CANCELADO"
    assert c.get(url).json()["artista_nombre"] == "Tiësto"  # público


def test_publicacion_y_escaleta_publica(cliente_http):
    c = cliente_http
    tiesto, armin = preparar(c)
    assert c.get(f"{API}/escaletas/{EVENTO}").status_code == 404
    s1 = slot(c).json()
    s2 = slot(c, espacio="esc-trance", inicio="2026-07-19T00:30:00+02:00", fin="2026-07-19T02:00:00+02:00").json()
    c.post(f"{API}/slots/{s1['id']}/pases", headers=ADMIN, json={"artista_id": tiesto["id"], "formato": "DJ_SET"})
    pase = c.post(f"{API}/slots/{s2['id']}/pases", headers=ADMIN,
                  json={"artista_id": armin["id"], "formato": "DJ_SET"}).json()

    r = c.post(f"{API}/escaletas/{EVENTO}/publicaciones", headers=ADMIN)
    assert r.status_code == 201 and r.json()["version"] == 1
    assert c.post(f"{API}/escaletas/{EVENTO}/publicaciones", headers=ADMIN).status_code == 409  # sin cambios

    escaleta = c.get(f"{API}/escaletas/{EVENTO}").json()
    # El pase de las 00:30 pertenece a la noche del 18
    assert [d["fecha"] for d in escaleta["dias"]] == ["2026-07-18"]
    assert [e["nombre"] for e in escaleta["dias"][0]["escenarios"]] == ["Main Stage", "Trance Stage"]
    assert c.get(f"{API}/escaletas/{EVENTO}/escenarios/esc-trance").json()["pases"][0]["artista"] == "Armin van Buuren"

    # Un cambio del borrador no se ve hasta publicar de nuevo
    c.patch(f"{API}/pases/{pase['id']}", headers=ADMIN, json={"version": 1, "estado": "CONFIRMADO"})
    assert c.get(f"{API}/escaletas/{EVENTO}").json()["version"] == 1
    assert c.post(f"{API}/escaletas/{EVENTO}/publicaciones", headers=ADMIN).json()["version"] == 2
    assert len(c.get(f"{API}/escaletas/{EVENTO}/publicaciones", headers=ADMIN).json()) == 2

    ficha = c.get(f"{API}/artistas/{armin['id']}").json()
    assert ficha["pases"][0]["estado"] == "CONFIRMADO"
    assert c.get(f"{API}/artistas?evento_id={EVENTO}").headers["X-Total-Count"] == "2"
    assert c.get(f"{API}/artistas?genero=trance").headers["X-Total-Count"] == "2"
    assert c.get(f"{API}/artistas/{armin['id']}/videos").json() == []  # sin clave de YouTube


def test_cancelar_evento_cancela_pases(cliente_http):
    c = cliente_http
    tiesto, _ = preparar(c)
    s1 = slot(c).json()
    pase = c.post(f"{API}/slots/{s1['id']}/pases", headers=ADMIN,
                  json={"artista_id": tiesto["id"], "formato": "DJ_SET"}).json()
    db = SessionLocal()
    escaleta_service.al_cambiar_estado_evento(db, EVENTO, "CANCELADO")
    db.close()
    assert c.get(f"{API}/pases/{pase['id']}").json()["estado"] == "CANCELADO"
    assert c.post(f"{API}/escaletas/{EVENTO}/publicaciones", headers=ADMIN).status_code == 409


def test_difusor_entrega_cambios_a_los_suscriptores():
    async def escenario():
        difusor = Difusor()
        cola = difusor.suscribir("evento-x")
        otra = difusor.suscribir("evento-y")
        # emitir() se llama desde los hilos de los endpoints síncronos
        await asyncio.to_thread(difusor.emitir, "evento-x", "pase.modificado", {"tipo": "pase.modificado"})
        mensaje = await asyncio.wait_for(cola.get(), timeout=1)
        assert mensaje.startswith("event: pase.modificado\ndata: ")
        assert otra.empty()
        difusor.cancelar("evento-x", cola)
        assert difusor.num_suscriptores("evento-x") == 0

    asyncio.run(escenario())
