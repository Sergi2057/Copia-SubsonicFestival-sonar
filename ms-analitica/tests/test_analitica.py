# ms-analitica/tests/test_analitica.py
import uuid
from datetime import datetime, timedelta, timezone
from conftest import ADMIN, CLIENTE, PROVEEDOR
from eventos.procesador import procesar

API = "/api/v1"
HOY = datetime.now(timezone.utc)
A1, A2, A3, A4 = (f"22222222-2222-4222-8222-00000000000{i}" for i in range(1, 5))


def sobre(tipo, datos, dias_atras=0, id_evento=None):
    return {"id_evento": id_evento or str(uuid.uuid4()), "tipo": tipo, "version": 1, "origen": "test",
            "fecha": (HOY - timedelta(days=dias_atras)).isoformat(), "datos": datos}


def pase(pid, artista_id, nombre, escenario, inicio, fin):
    return {"pase_id": pid, "artista_id": artista_id, "artista": nombre, "escenario": escenario,
            "inicio": inicio, "fin": fin, "estado": "CONFIRMADO"}


def escenario_base():
    procesar(sobre("espacios.evento.publicado", {"evento_id": "ev-1", "titulo": "Subsonic Test", "estado": "PUBLICADO"}))
    procesar(sobre("espacios.espacio.creado", {"espacio_id": "main", "evento_id": "ev-1", "tipo": "ESCENARIO",
                                               "nombre": "Main", "aforo": 100, "disponible": False}))
    for esp, tipo, precio in (("fb-1", "FOOD_BEVERAGE", 1000.0), ("fb-2", "FOOD_BEVERAGE", 500.0),
                              ("merch-1", "MERCHANDISING", 800.0)):
        procesar(sobre("espacios.espacio.creado", {"espacio_id": esp, "evento_id": "ev-1", "tipo": tipo,
                                                   "nombre": esp, "precio_alquiler": precio, "disponible": True}))
    for aid, nombre, generos in ((A1, "Armin van Buuren", ["trance", "progressive"]), (A2, "Above & Beyond", ["trance"]),
                                 (A3, "Tiësto", ["house", "trance"]), (A4, "Skrillex", ["dubstep"])):
        procesar(sobre("escaleta.artista.creado", {"artista_id": aid, "nombre": nombre, "generos": generos}))
    procesar(sobre("escaleta.publicada", {"evento_id": "ev-1", "version": 1, "dias": [{"fecha": "2026-07-18", "escenarios": [
        {"espacio_id": "main", "nombre": "Main", "pases": [
            pase("p1", A1, "Armin van Buuren", "Main", "2026-07-18T20:00:00Z", "2026-07-18T22:00:00Z"),
            pase("p3", A3, "Tiësto", "Main", "2026-07-18T22:00:00Z", "2026-07-19T00:00:00Z")]},
        {"espacio_id": "second", "nombre": "Second", "pases": [
            pase("p2", A2, "Above & Beyond", "Second", "2026-07-18T21:00:00Z", "2026-07-18T23:00:00Z")]},
    ]}]}))


def test_procesar_es_idempotente(cliente_http):
    evento = sobre("usuarios.entrada.comprada", {"entrada_id": "e1", "usuario_id": "u1", "evento_id": "ev-1",
                                                 "tipo_pase": "WEEKEND", "precio_pagado": 199.0}, id_evento="fijo")
    assert procesar(evento) is True
    assert procesar(evento) is False  # mensaje repetido por RabbitMQ
    resumen = cliente_http.get(f"{API}/estadisticas/resumen", headers=ADMIN).json()
    assert resumen["entradas_vendidas"] == 1 and resumen["ingresos_entradas"] == 199.0


def test_ventas_y_resumen(cliente_http):
    c = cliente_http
    for i, (tipo, precio) in enumerate((("DAY", 89.0), ("WEEKEND", 199.0), ("WEEKEND", 199.0))):
        procesar(sobre("usuarios.entrada.comprada", {"entrada_id": f"e{i}", "usuario_id": f"u{i}", "evento_id": "ev-1",
                                                     "tipo_pase": tipo, "precio_pagado": precio}, dias_atras=i))
    procesar(sobre("usuarios.entrada.cancelada", {"entrada_id": "e0", "usuario_id": "u0", "evento_id": "ev-1",
                                                  "tipo_pase": "DAY", "precio_pagado": 89.0}))
    procesar(sobre("usuarios.entrada.validada", {"entrada_id": "e1", "usuario_id": "u1", "evento_id": "ev-1",
                                                 "tipo_pase": "WEEKEND", "precio_pagado": 199.0}))
    por_tipo = {v["periodo"]: v for v in c.get(f"{API}/estadisticas/ventas?agrupar_por=TIPO_PASE",
                                               headers=ADMIN).json()}
    assert por_tipo["WEEKEND"]["entradas"] == 2 and por_tipo["DAY"]["cancelaciones"] == 1
    assert len(c.get(f"{API}/estadisticas/ventas", headers=ADMIN).json()) == 3  # por día
    resumen = c.get(f"{API}/estadisticas/resumen?evento_id=ev-1", headers=ADMIN).json()
    assert resumen["entradas_vendidas"] == 2 and resumen["ingresos_entradas"] == 398.0
    assert resumen["asistentes_hoy"] == 1
    hoy = HOY.date().isoformat()
    assert c.get(f"{API}/estadisticas/ventas?desde={hoy}&hasta=2000-01-01", headers=ADMIN).status_code == 400
    assert c.get(f"{API}/estadisticas/resumen", headers=CLIENTE).status_code == 403


def test_ocupacion_tienda_y_afluencia(cliente_http):
    c = cliente_http
    escenario_base()
    procesar(sobre("espacios.alquiler.aprobado", {"alquiler_id": "al1", "espacio_id": "fb-1", "evento_id": "ev-1",
                                                  "proveedor_id": "prov-9", "importe": 1500.0, "estado": "APROBADO"}))
    ocupacion = {o["tipo_espacio"]: o for o in c.get(f"{API}/estadisticas/ocupacion?evento_id=ev-1",
                                                     headers=ADMIN).json()}
    assert ocupacion["FOOD_BEVERAGE"] == {"evento_id": "ev-1", "tipo_espacio": "FOOD_BEVERAGE", "total": 2,
                                          "alquilados": 1, "ingresos_alquiler": 1500.0}
    assert "ESCENARIO" not in ocupacion
    assert c.get(f"{API}/estadisticas/ocupacion?evento_id=otro", headers=ADMIN).status_code == 404

    lineas = [{"variante_id": "v1", "producto_id": "camiseta", "talla": "M", "cantidad": 2, "precio_unitario": 25.0}]
    procesar(sobre("tienda.pedido.creado", {"pedido_id": "p1", "estado": "PAGADO", "lineas": lineas}))
    procesar(sobre("tienda.pedido.creado", {"pedido_id": "p2", "estado": "PAGADO", "lineas": lineas}))
    procesar(sobre("tienda.pedido.actualizado", {"pedido_id": "p2", "estado": "CANCELADO"}))
    procesar(sobre("tienda.stock.bajo", {"variante_id": "v1", "producto_id": "camiseta", "talla": "M", "stock": 3}))
    tienda = c.get(f"{API}/estadisticas/tienda", headers=ADMIN).json()
    assert tienda["ventas"] == [{"producto_id": "camiseta", "talla": "M", "unidades": 2, "ingresos": 50.0}]
    assert tienda["stock_bajo"][0]["stock"] == 3

    # Afluencia: 90 entradas; Armin (3 fans) y Above & Beyond (0) coinciden entre las 21 y las 22
    for i in range(90):
        procesar(sobre("usuarios.entrada.comprada", {"entrada_id": f"e{i}", "usuario_id": f"u{i}", "evento_id": "ev-1",
                                                     "tipo_pase": "DAY", "precio_pagado": 10.0}))
    for u in ("x", "y", "z"):
        procesar(sobre("usuarios.favorito.anadido", {"usuario_id": u, "artista_id": A1, "artista_nombre": "Armin"}))
    afluencia = c.get(f"{API}/estadisticas/afluencia?evento_id=ev-1", headers=ADMIN).json()
    main = next(e for e in afluencia if e["escenario"] == "Main")
    armin = main["franjas"][0]
    assert armin["artista"] == "Armin van Buuren"
    assert armin["asistentes_estimados"] == 72 and armin["porcentaje_aforo"] == 0.72  # 90 * 4/5


def test_recomendaciones_de_cliente(cliente_http):
    c = cliente_http
    escenario_base()
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "cliente-1", "artista_id": A1}))
    # Otro cliente con Armin en favoritos también sigue a Skrillex (colaborativo)
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "otro", "artista_id": A1}))
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "otro", "artista_id": A4}))

    r = c.get(f"{API}/recomendaciones/me", headers=CLIENTE).json()
    artistas = {a["artista"]: a for a in r["artistas"]}
    assert artistas["Above & Beyond"]["motivo"] == "Porque te gusta Armin van Buuren"
    assert "Skrillex" in artistas  # recomendado por similitud con otros clientes
    assert r["eventos"][0]["evento_id"] == "ev-1" and "1 de tus artistas favoritos" in r["eventos"][0]["motivo"]
    assert [p["artista"] for p in r["mi_escaleta"]] == ["Armin van Buuren"]

    # Al añadir un favorito se recalculan; Armin y Above & Beyond se solapan de 21 a 22
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "cliente-1", "artista_id": A2}))
    r = c.get(f"{API}/recomendaciones/me", headers=CLIENTE).json()
    mi = {p["pase_id"]: p for p in r["mi_escaleta"]}
    assert mi["p1"]["solapa_con"] == ["p2"] and mi["p2"]["solapa_con"] == ["p1"]
    assert c.get(f"{API}/recomendaciones/me", headers=PROVEEDOR).status_code == 403


def test_populares_e_interacciones(cliente_http):
    c = cliente_http
    escenario_base()
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "u1", "artista_id": A3}))
    r = c.post(f"{API}/interacciones", json={"sesion_id": str(uuid.uuid4()), "interacciones": [
        {"accion": "VER_ARTISTA", "objetivo_id": A2, "fecha": HOY.isoformat()},
        {"accion": "VER_ARTISTA", "objetivo_id": "no-existe", "fecha": HOY.isoformat()},
        {"accion": "BUSCAR", "objetivo_id": "trance", "fecha": HOY.isoformat()}]})
    assert r.status_code == 202
    assert c.post(f"{API}/interacciones", json={"interacciones": [
        {"accion": "BUSCAR", "objetivo_id": "x", "fecha": HOY.isoformat()}]}).status_code == 400  # ni token ni sesión

    ranking = c.get(f"{API}/estadisticas/artistas-populares").json()
    # Tiësto (1 favorito) > Above & Beyond (1 visita) > el resto, sin actividad
    assert [a["artista"] for a in ranking[:2]] == ["Tiësto", "Above & Beyond"]
    assert ranking[0]["tendencia_7d"] == 1.0 and ranking[-1]["favoritos"] == ranking[-1]["visitas"] == 0
    populares = c.get(f"{API}/recomendaciones/populares").json()
    assert populares["eventos"][0]["evento_id"] == "ev-1"


def test_populares_sin_seguidores_no_dicen_que_sean_los_mas_seguidos(cliente_http):
    c = cliente_http
    escenario_base()
    procesar(sobre("espacios.evento.publicado", {"evento_id": "ev-2", "titulo": "Subsonic Vacío", "estado": "PUBLICADO"}))
    procesar(sobre("escaleta.publicada", {"evento_id": "ev-2", "version": 1, "dias": [{"fecha": "2026-08-08", "escenarios": [
        {"espacio_id": "x", "nombre": "X", "pases": [
            pase("p9", A4, "Skrillex", "X", "2026-08-08T20:00:00Z", "2026-08-08T22:00:00Z")]}]}]}))
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "u1", "artista_id": A1}))

    eventos = {e["evento_id"]: e for e in c.get(f"{API}/recomendaciones/populares").json()["eventos"]}
    assert eventos["ev-1"] == {"evento_id": "ev-1", "titulo": "Subsonic Test", "puntuacion": 1.0,
                               "motivo": "Sus artistas son de los más seguidos"}
    assert eventos["ev-2"]["puntuacion"] == 0 and eventos["ev-2"]["motivo"] == "Próxima edición del festival"


def test_espacios_para_proveedor(cliente_http):
    c = cliente_http
    escenario_base()
    # El proveedor ya alquiló un FOOD_BEVERAGE (fb-1): se le recomiendan otros de ese tipo libres
    procesar(sobre("espacios.alquiler.aprobado", {"alquiler_id": "al1", "espacio_id": "fb-1", "evento_id": "ev-1",
                                                  "proveedor_id": "prov-1", "importe": 1000.0, "estado": "APROBADO"}))
    r = c.get(f"{API}/recomendaciones/espacios", headers=PROVEEDOR).json()
    assert [e["espacio_id"] for e in r] == ["fb-2"]
    # Un proveedor nuevo ve todos los alquilables libres
    nuevo = {"X-User-Id": "prov-nuevo", "X-User-Rol": "PROVEEDOR"}
    assert {e["espacio_id"] for e in c.get(f"{API}/recomendaciones/espacios", headers=nuevo).json()} == {"fb-2",
                                                                                                         "merch-1"}


def test_borrado_de_usuario_rgpd(cliente_http):
    c = cliente_http
    escenario_base()
    procesar(sobre("usuarios.usuario.registrado", {"usuario_id": "cliente-1", "rol": "CLIENTE"}))
    procesar(sobre("usuarios.favorito.anadido", {"usuario_id": "cliente-1", "artista_id": A1}))
    c.post(f"{API}/interacciones", headers=CLIENTE, json={"interacciones": [
        {"accion": "VER_EVENTO", "objetivo_id": "ev-1", "fecha": HOY.isoformat()}]})
    procesar(sobre("usuarios.usuario.eliminado", {"usuario_id": "cliente-1"}))
    from config.database import get_db
    db = get_db()
    assert db.favoritos.count_documents({"usuario_id": "cliente-1"}) == 0
    assert db.interacciones.count_documents({"sujeto": "cliente-1"}) == 0
    assert db.eventos_dominio.count_documents({"datos.usuario_id": "cliente-1"}) == 0
    assert c.get(f"{API}/estadisticas/resumen", headers=ADMIN).json()["usuarios_registrados"] == 0
