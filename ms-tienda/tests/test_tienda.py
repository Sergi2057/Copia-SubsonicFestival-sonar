# ms-tienda/tests/test_tienda.py
from conftest import ADMIN, CLIENTE, OTRO_CLIENTE, habilitar_recogida

API = "/api/v1"


def crear_camiseta(c, stock_m=10):
    habilitar_recogida("evento-belgium")  # los pedidos de prueba se recogen ahí
    r = c.post(f"{API}/productos", headers=ADMIN, json={"id": "camiseta-2026", "nombre": "Camiseta", "precio": 25})
    assert r.status_code == 201
    r = c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN, json={"talla": "M", "stock": stock_m})
    assert r.status_code == 201
    return r.json()["id"]


def pedido(variante_id, cantidad=2, token="tok_ok"):
    return {"lineas": [{"variante_id": variante_id, "cantidad": cantidad}],
            "entrega": "RECOGIDA_EVENTO", "evento_id_recogida": "evento-belgium", "token_pago": token}


def test_catalogo_publico_y_admin_requerido(cliente_http):
    c = cliente_http
    crear_camiseta(c)
    r = c.get(f"{API}/productos")
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1"
    assert r.json()[0]["variantes"][0]["talla"] == "M"
    assert c.post(f"{API}/productos", json={"id": "x", "nombre": "x", "precio": 1}).status_code == 401
    r = c.post(f"{API}/productos", headers=CLIENTE, json={"id": "x", "nombre": "x", "precio": 1})
    assert r.status_code == 403 and r.json()["codigo"] == "SIN_PERMISO"


def test_errores_de_validacion_y_duplicados(cliente_http):
    c = cliente_http
    crear_camiseta(c)
    r = c.post(f"{API}/productos", headers=ADMIN, json={"id": "Con Espacios", "nombre": "x", "precio": 1})
    assert r.status_code == 400 and r.json()["codigo"] == "PETICION_NO_VALIDA"
    assert c.post(f"{API}/productos", headers=ADMIN,
                  json={"id": "camiseta-2026", "nombre": "x", "precio": 1}).status_code == 409
    assert c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN,
                  json={"talla": "M", "stock": 1}).status_code == 409


def test_retirar_producto_lo_oculta(cliente_http):
    c = cliente_http
    crear_camiseta(c)
    assert c.delete(f"{API}/productos/camiseta-2026", headers=ADMIN).status_code == 204
    assert c.get(f"{API}/productos").json() == []
    assert c.get(f"{API}/productos/camiseta-2026").status_code == 404
    assert c.get(f"{API}/productos/camiseta-2026", headers=ADMIN).json()["activo"] is False


def test_compra_descuenta_stock(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    r = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 3))
    assert r.status_code == 201, r.text
    cuerpo = r.json()
    assert r.headers["Location"] == f"/api/v1/pedidos/{cuerpo['id']}"
    assert cuerpo["estado"] == "PAGADO" and cuerpo["importe_total"] == 75
    assert cuerpo["lineas"][0]["producto_nombre"] == "Camiseta"
    assert c.get(f"{API}/productos/camiseta-2026").json()["variantes"][0]["stock"] == 7


def test_compra_sin_stock_o_pago_rechazado_no_toca_stock(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=2)
    r = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 3))
    assert r.status_code == 409 and r.json()["codigo"] == "SIN_STOCK"
    r = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1, token="tok_rechazado_1"))
    assert r.status_code == 402
    assert c.get(f"{API}/productos/camiseta-2026").json()["variantes"][0]["stock"] == 2


def test_solo_clientes_compran_y_entrega_validada(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c)
    assert c.post(f"{API}/pedidos", headers=ADMIN, json=pedido(variante_id)).status_code == 403
    datos = pedido(variante_id) | {"entrega": "DOMICILIO"}
    assert c.post(f"{API}/pedidos", headers=CLIENTE, json=datos).status_code == 400


def test_estados_del_pedido(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 2)).json()["id"]
    url = f"{API}/pedidos/{pedido_id}"

    assert c.get(url, headers=OTRO_CLIENTE).status_code == 403
    assert c.get(f"{API}/pedidos", headers=OTRO_CLIENTE).json() == []
    # El admin no puede saltarse estados ni enviar un pedido de recogida
    assert c.patch(url, headers=ADMIN, json={"estado": "ENTREGADO"}).status_code == 409
    assert c.patch(url, headers=ADMIN, json={"estado": "PREPARADO"}).json()["estado"] == "PREPARADO"
    assert c.patch(url, headers=ADMIN, json={"estado": "ENVIADO"}).status_code == 409
    assert c.patch(url, headers=ADMIN, json={"estado": "LISTO_RECOGIDA"}).status_code == 200
    # Ya no está PAGADO: el cliente no puede cancelar
    assert c.patch(url, headers=CLIENTE, json={"estado": "CANCELADO"}).status_code == 409


def test_cancelar_devuelve_stock(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 4)).json()["id"]
    r = c.patch(f"{API}/pedidos/{pedido_id}", headers=CLIENTE, json={"estado": "CANCELADO"})
    assert r.status_code == 200 and r.json()["estado"] == "CANCELADO"
    assert c.get(f"{API}/productos/camiseta-2026").json()["variantes"][0]["stock"] == 10


# ── Ciclo de vida de las variantes ──────────────────────────

def url_variante(variante_id):
    return f"{API}/productos/camiseta-2026/variantes/{variante_id}"


def tallas_publicas(c):
    return [v["talla"] for v in c.get(f"{API}/productos/camiseta-2026").json()["variantes"]]


def entregar(c, pedido_id):
    for estado in ("PREPARADO", "LISTO_RECOGIDA", "ENTREGADO"):
        assert c.patch(f"{API}/pedidos/{pedido_id}", headers=ADMIN, json={"estado": estado}).status_code == 200


def test_cambiar_talla(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    r = c.patch(url_variante(variante_id), headers=ADMIN, json={"talla": "L"})
    assert r.status_code == 200, r.text
    assert r.json() == {"id": variante_id, "talla": "L", "stock": 10, "activa": True}  # el stock no cambia
    assert tallas_publicas(c) == ["L"]
    r = c.patch(url_variante(variante_id), headers=ADMIN, json={"talla": "XL", "stock": 3})
    assert r.json()["talla"] == "XL" and r.json()["stock"] == 3


def test_cambiar_a_una_talla_repetida_da_409(cliente_http):
    c = cliente_http
    variante_m = crear_camiseta(c)
    c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN, json={"talla": "L", "stock": 5})
    r = c.patch(url_variante(variante_m), headers=ADMIN, json={"talla": "L"})
    assert r.status_code == 409 and r.json()["codigo"] == "TALLA_DUPLICADA"
    # Enviar su propia talla no es un conflicto
    assert c.patch(url_variante(variante_m), headers=ADMIN, json={"talla": "M"}).status_code == 200


def test_patch_vacio_da_400(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c)
    for cuerpo in ({}, {"talla": None, "stock": None}):
        r = c.patch(url_variante(variante_id), headers=ADMIN, json=cuerpo)
        assert r.status_code == 400 and r.json()["codigo"] == "PETICION_NO_VALIDA"
    assert c.patch(url_variante(variante_id), headers=CLIENTE, json={"stock": 1}).status_code == 403


def test_borrar_variante_sin_ventas_la_elimina(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c)
    assert c.delete(url_variante(variante_id), headers=ADMIN).status_code == 204
    assert c.get(f"{API}/productos/camiseta-2026", headers=ADMIN).json()["variantes"] == []
    # Ya no existe: 404, y la talla se puede volver a crear
    assert c.delete(url_variante(variante_id), headers=ADMIN).status_code == 404
    assert c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN,
                  json={"talla": "M", "stock": 1}).status_code == 201


def test_borrar_variante_vendida_la_retira(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1)).json()["id"]
    entregar(c, pedido_id)

    assert c.delete(url_variante(variante_id), headers=ADMIN).status_code == 204
    assert tallas_publicas(c) == []
    assert c.get(f"{API}/productos?disponible=true").json() == []
    variantes_admin = c.get(f"{API}/productos/camiseta-2026", headers=ADMIN).json()["variantes"]
    assert [(v["id"], v["activa"]) for v in variantes_admin] == [(variante_id, False)]
    # El pedido antiguo sigue mostrando su talla
    assert c.get(f"{API}/pedidos/{pedido_id}", headers=CLIENTE).json()["lineas"][0]["talla"] == "M"


def test_retirar_y_volver_a_anadir_reactiva_la_talla(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1)).json()["id"]
    entregar(c, pedido_id)
    assert c.delete(url_variante(variante_id), headers=ADMIN).status_code == 204
    assert tallas_publicas(c) == []

    r = c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN, json={"talla": "M", "stock": 20})
    assert r.status_code == 201, r.text
    # Es la misma variante (mismo id), activa y con el stock nuevo
    assert r.json() == {"id": variante_id, "talla": "M", "stock": 20, "activa": True}
    assert tallas_publicas(c) == ["M"]
    # Conserva su historial y se puede volver a comprar
    assert c.get(f"{API}/pedidos/{pedido_id}", headers=CLIENTE).json()["lineas"][0]["variante_id"] == variante_id
    assert c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1)).status_code == 201
    # Si ya está activa, sigue siendo un duplicado
    r = c.post(f"{API}/productos/camiseta-2026/variantes", headers=ADMIN, json={"talla": "M", "stock": 1})
    assert r.status_code == 409 and r.json()["codigo"] == "TALLA_DUPLICADA"


def test_borrar_variante_con_pedido_pendiente_da_409(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1)).json()["id"]
    assert c.patch(f"{API}/pedidos/{pedido_id}", headers=ADMIN, json={"estado": "PREPARADO"}).status_code == 200

    r = c.delete(url_variante(variante_id), headers=ADMIN)
    assert r.status_code == 409 and r.json()["codigo"] == "VARIANTE_CON_PEDIDOS_PENDIENTES"
    assert tallas_publicas(c) == ["M"]  # no se ha tocado


def test_comprar_variante_retirada_da_409(cliente_http):
    c = cliente_http
    variante_id = crear_camiseta(c, stock_m=10)
    pedido_id = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1)).json()["id"]
    entregar(c, pedido_id)
    c.delete(url_variante(variante_id), headers=ADMIN)

    r = c.post(f"{API}/pedidos", headers=CLIENTE, json=pedido(variante_id, 1))
    assert r.status_code == 409 and r.json()["codigo"] == "VARIANTE_RETIRADA"
    variantes_admin = c.get(f"{API}/productos/camiseta-2026", headers=ADMIN).json()["variantes"]
    assert variantes_admin[0]["stock"] == 9  # no se ha descontado nada
