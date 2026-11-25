# ms-espacios/tests/test_espacios.py
from config.database import SessionLocal
from conftest import ADMIN, CLIENTE, PROVEEDOR, SERVICIO
from service import aforo_service, espacio_service

API = "/api/v1"
INTERNO = "/internal/v1"


def preparar_evento(c, publicar=True, cupo=2):
    recinto = c.post(f"{API}/recintos", headers=ADMIN,
                     json={"nombre": "Dreamville", "ciudad": "Boom", "pais": "Bélgica", "aforo_maximo": 70000}).json()
    r = c.post(f"{API}/eventos", headers=ADMIN, json={
        "id": "evento-test", "titulo": "Subsonic Test", "pais": "Bélgica", "recinto_id": recinto["id"],
        "fecha_inicio": "2026-07-18", "fecha_fin": "2026-07-27", "tags": ["techno", "verano"]})
    assert r.status_code == 201, r.text
    assert r.json()["estado"] == "BORRADOR"
    tarifa = c.post(f"{API}/eventos/evento-test/tarifas", headers=ADMIN,
                    json={"tipo_pase": "WEEKEND", "precio": 199, "cupo_total": cupo}).json()
    if publicar:
        assert c.patch(f"{API}/eventos/evento-test", headers=ADMIN, json={"estado": "PUBLICADO"}).status_code == 200
    return tarifa


def crear_recinto(c):
    r = c.post(f"{API}/recintos", headers=ADMIN, json={
        "nombre": "Dreamville", "ciudad": "Boom", "pais": "Bélgica", "aforo_maximo": 70000})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def crear_espacio_alquilable(c):
    r = c.post(f"{API}/espacios", headers=ADMIN, json={
        "evento_id": "evento-test", "tipo": "FOOD_BEVERAGE", "nombre": "Puesto F&B", "precio_alquiler": 100,
        "disponible": True})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def alta_proveedor(proveedor_id="prov-1", activo=True):
    db = SessionLocal()
    espacio_service.actualizar_replica_proveedor(
        db, {"proveedor_id": proveedor_id, "nombre_comercial": "Food Truck Ana", "activo": activo})
    db.close()


def test_eliminar_recinto_sin_eventos(cliente_http):
    c = cliente_http
    recinto_id = crear_recinto(c)

    assert c.delete(f"{API}/recintos/{recinto_id}", headers=ADMIN).status_code == 204
    assert c.get(f"{API}/recintos/{recinto_id}").status_code == 404


def test_no_eliminar_recinto_con_eventos(cliente_http):
    c = cliente_http
    preparar_evento(c, publicar=False)
    recinto_id = c.get(f"{API}/recintos").json()[0]["id"]

    assert c.delete(f"{API}/recintos/{recinto_id}", headers=ADMIN).status_code == 409
    assert c.get(f"{API}/recintos/{recinto_id}").status_code == 200


def test_eliminar_recinto_inexistente(cliente_http):
    c = cliente_http

    assert c.delete(f"{API}/recintos/00000000-0000-0000-0000-000000000000",
                    headers=ADMIN).status_code == 404


def test_eliminar_recinto_requiere_admin(cliente_http):
    c = cliente_http
    recinto_id = crear_recinto(c)

    assert c.delete(f"{API}/recintos/{recinto_id}", headers=CLIENTE).status_code == 403


def test_borradores_solo_para_admin(cliente_http):
    c = cliente_http
    preparar_evento(c, publicar=False)
    assert c.get(f"{API}/eventos").json() == []
    assert c.get(f"{API}/eventos/evento-test").status_code == 404
    assert c.get(f"{API}/eventos", headers=ADMIN).headers["X-Total-Count"] == "1"
    assert c.patch(f"{API}/eventos/evento-test", headers=ADMIN, json={"estado": "PUBLICADO"}).status_code == 200
    detalle = c.get(f"{API}/eventos/evento-test").json()
    assert detalle["recinto"]["ciudad"] == "Boom"
    assert len(c.get(f"{API}/eventos?tag=techno&pais=bélgica").json()) == 1
    assert c.get(f"{API}/eventos?tag=rock").json() == []


def test_transiciones_de_evento(cliente_http):
    c = cliente_http
    preparar_evento(c)
    url = f"{API}/eventos/evento-test"
    assert c.patch(url, headers=ADMIN, json={"estado": "CANCELADO"}).status_code == 400  # falta motivo
    assert c.patch(url, headers=ADMIN, json={"estado": "FINALIZADO"}).status_code == 200
    assert c.patch(url, headers=ADMIN, json={"estado": "PUBLICADO"}).status_code == 409
    assert c.delete(url, headers=ADMIN).status_code == 409  # ya no está en BORRADOR


def test_tipos_y_espacio_no_alquilable(cliente_http):
    c = cliente_http
    preparar_evento(c)
    tipos = {t["codigo"]: t["alquilable"] for t in c.get(f"{API}/tipos-espacio").json()}
    assert tipos["ESCENARIO"] is False and tipos["FOOD_BEVERAGE"] is True
    r = c.post(f"{API}/espacios", headers=ADMIN, json={
        "evento_id": "evento-test", "tipo": "ESCENARIO", "nombre": "Main", "precio_alquiler": 10, "disponible": True})
    assert r.status_code == 400


def test_alquiler_completo(cliente_http):
    c = cliente_http
    preparar_evento(c)
    espacio_id = crear_espacio_alquilable(c)
    cuerpo = {"fecha_inicio": "2026-07-16T08:00:00+02:00", "fecha_fin": "2026-07-28T20:00:00+02:00"}

    # Proveedor que no está en la réplica -> 403
    r = c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo)
    assert r.status_code == 403

    alta_proveedor()
    r = c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo)
    assert r.status_code == 201, r.text
    alquiler = r.json()
    assert alquiler["estado"] == "PENDIENTE" and alquiler["importe"] == 1300  # 13 días x 100
    assert alquiler["proveedor_nombre"] == "Food Truck Ana"

    # Otro proveedor no lo ve; el admin lo aprueba
    otro = {"X-User-Id": "prov-2", "X-User-Rol": "proveedor"}
    assert c.get(f"{API}/alquileres/{alquiler['id']}", headers=otro).status_code == 403
    assert c.patch(f"{API}/alquileres/{alquiler['id']}", headers=PROVEEDOR,
                   json={"estado": "APROBADO"}).status_code == 409
    r = c.patch(f"{API}/alquileres/{alquiler['id']}", headers=ADMIN, json={"estado": "APROBADO"})
    assert r.json()["estado"] == "APROBADO"

    # Solapes: nueva solicitud en las mismas fechas -> 409; el espacio no se puede borrar
    assert c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo).status_code == 409
    assert c.delete(f"{API}/espacios/{espacio_id}", headers=ADMIN).status_code == 409
    assert c.get(f"{API}/alquileres", headers=PROVEEDOR).headers["X-Total-Count"] == "1"


def test_no_se_aprueban_dos_alquileres_solapados(cliente_http):
    c = cliente_http
    preparar_evento(c)
    espacio_id = crear_espacio_alquilable(c)
    alta_proveedor("prov-1")
    alta_proveedor("prov-2")
    cuerpo = {"fecha_inicio": "2026-07-16T08:00:00Z", "fecha_fin": "2026-07-20T08:00:00Z"}
    a1 = c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo).json()
    a2 = c.post(f"{API}/espacios/{espacio_id}/alquileres",
                headers={"X-User-Id": "prov-2", "X-User-Rol": "proveedor"}, json=cuerpo).json()
    assert c.patch(f"{API}/alquileres/{a1['id']}", headers=ADMIN, json={"estado": "APROBADO"}).status_code == 200
    assert c.patch(f"{API}/alquileres/{a2['id']}", headers=ADMIN, json={"estado": "APROBADO"}).status_code == 409


def test_proveedor_desactivado_rechaza_pendientes(cliente_http):
    c = cliente_http
    preparar_evento(c)
    espacio_id = crear_espacio_alquilable(c)
    alta_proveedor()
    cuerpo = {"fecha_inicio": "2026-07-16T08:00:00Z", "fecha_fin": "2026-07-20T08:00:00Z"}
    alquiler = c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo).json()
    alta_proveedor(activo=False)
    assert c.get(f"{API}/alquileres/{alquiler['id']}", headers=ADMIN).json()["estado"] == "RECHAZADO"
    assert c.post(f"{API}/espacios/{espacio_id}/alquileres", headers=PROVEEDOR, json=cuerpo).status_code == 403


def test_reserva_de_aforo(cliente_http):
    c = cliente_http
    preparar_evento(c, cupo=2)
    url = f"{INTERNO}/eventos/evento-test/reservas-aforo"
    cuerpo = {"tipo_pase": "WEEKEND", "usuario_id": "cliente-1"}

    assert c.post(url, json=cuerpo).status_code == 401  # sin token de servicio
    r1 = c.post(url, headers=SERVICIO, json=cuerpo)
    assert r1.status_code == 201 and r1.json()["precio"] == 199
    r2 = c.post(url, headers=SERVICIO, json=cuerpo)
    assert r2.status_code == 201
    r3 = c.post(url, headers=SERVICIO, json=cuerpo)
    assert r3.status_code == 409 and r3.json()["codigo"] == "SIN_CUPO"
    assert c.get(f"{API}/eventos/evento-test/tarifas").json()[0]["disponibles"] == 0

    # Pago fallido: ms-usuarios libera la reserva y la plaza vuelve a estar disponible
    assert c.delete(f"{INTERNO}/reservas-aforo/{r2.json()['reserva_id']}", headers=SERVICIO).status_code == 204
    assert c.get(f"{API}/eventos/evento-test/tarifas").json()[0]["disponibles"] == 1


def test_confirmar_reserva_es_idempotente(cliente_http):
    import uuid
    c = cliente_http
    tarifa = preparar_evento(c, cupo=5)
    r = c.post(f"{INTERNO}/eventos/evento-test/reservas-aforo", headers=SERVICIO,
               json={"tipo_pase": "WEEKEND", "usuario_id": "cliente-1"})
    reserva_id = uuid.UUID(r.json()["reserva_id"])
    db = SessionLocal()
    assert aforo_service.confirmar_reserva(db, reserva_id) is True
    assert aforo_service.confirmar_reserva(db, reserva_id) is False  # mensaje repetido: no suma dos veces
    db.close()
    assert c.delete(f"{INTERNO}/reservas-aforo/{reserva_id}", headers=SERVICIO).status_code == 409
    # 5 de cupo - 1 vendida
    assert c.get(f"{API}/eventos/evento-test/tarifas").json()[0]["disponibles"] == 4
    # No se puede bajar el cupo por debajo de lo vendido ni borrar la tarifa
    url = f"{API}/eventos/evento-test/tarifas/{tarifa['id']}"
    assert c.put(url, headers=ADMIN, json={"tipo_pase": "WEEKEND", "precio": 199, "cupo_total": 0}).status_code == 400
    assert c.delete(url, headers=ADMIN).status_code == 409


def test_cancelacion_repetida_no_libera_dos_plazas(cliente_http):
    from uuid import UUID

    from eventos.manejadores import manejar
    from model.models import TarifaAcceso

    c = cliente_http
    preparar_evento(c, cupo=3)
    reservas = []
    for usuario_id in ("cliente-1", "cliente-2"):
        respuesta = c.post(
            f"{INTERNO}/eventos/evento-test/reservas-aforo",
            headers=SERVICIO,
            json={"tipo_pase": "WEEKEND", "usuario_id": usuario_id},
        )
        assert respuesta.status_code == 201
        reservas.append(UUID(respuesta.json()["reserva_id"]))

    db = SessionLocal()
    try:
        for reserva_id in reservas:
            aforo_service.confirmar_reserva(db, reserva_id)
    finally:
        db.close()

    sobre = {
        "id_evento": "evento-cancelacion-repetido",
        "tipo": "usuarios.entrada.cancelada",
        "datos": {"evento_id": "evento-test", "tipo_pase": "WEEKEND"},
    }
    manejar(sobre)
    manejar(sobre)

    db = SessionLocal()
    try:
        tarifa = db.query(TarifaAcceso).filter_by(evento_id="evento-test", tipo_pase="WEEKEND").one()
        assert tarifa.cupo_vendido == 1
    finally:
        db.close()


def test_evento_no_publicado_no_vende(cliente_http):
    c = cliente_http
    preparar_evento(c, publicar=False)
    r = c.post(f"{INTERNO}/eventos/evento-test/reservas-aforo", headers=SERVICIO,
               json={"tipo_pase": "WEEKEND", "usuario_id": "cliente-1"})
    assert r.status_code == 409
    assert c.post(f"{API}/eventos/evento-test/tarifas", headers=CLIENTE,
                  json={"tipo_pase": "DAY", "precio": 1, "cupo_total": 1}).status_code == 403


def test_tareas_periodicas_caducan_reservas_y_activan_alquileres(cliente_http):
    import uuid
    from datetime import datetime, timedelta, timezone

    from model.models import Alquiler, ReservaAforo
    from service.tareas_periodicas import ejecutar_tareas_periodicas

    c = cliente_http
    preparar_evento(c, cupo=2)
    reserva_respuesta = c.post(
        f"{INTERNO}/eventos/evento-test/reservas-aforo",
        headers=SERVICIO,
        json={"tipo_pase": "WEEKEND", "usuario_id": "cliente-1"},
    )
    assert reserva_respuesta.status_code == 201
    reserva_id = uuid.UUID(reserva_respuesta.json()["reserva_id"])

    espacio_id = crear_espacio_alquilable(c)
    alta_proveedor()
    ahora = datetime.now(timezone.utc)
    alquiler_respuesta = c.post(
        f"{API}/espacios/{espacio_id}/alquileres",
        headers=PROVEEDOR,
        json={
            "fecha_inicio": (ahora - timedelta(days=2)).isoformat(),
            "fecha_fin": (ahora + timedelta(days=2)).isoformat(),
        },
    )
    assert alquiler_respuesta.status_code == 201
    alquiler_id = uuid.UUID(alquiler_respuesta.json()["id"])
    aprobacion = c.patch(
        f"{API}/alquileres/{alquiler_id}",
        headers=ADMIN,
        json={"estado": "APROBADO"},
    )
    assert aprobacion.status_code == 200
    assert aprobacion.json()["estado"] == "APROBADO"

    db = SessionLocal()
    try:
        reserva = db.get(ReservaAforo, reserva_id)
        assert reserva is not None
        reserva.expira_en = ahora - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    ejecutar_tareas_periodicas()

    db = SessionLocal()
    try:
        reserva = db.get(ReservaAforo, reserva_id)
        alquiler = db.get(Alquiler, alquiler_id)
        assert reserva is not None and reserva.estado == "LIBERADA"
        assert alquiler is not None and alquiler.estado == "ACTIVO"
    finally:
        db.close()
