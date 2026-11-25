# gateway/tests/test_gateway.py
import httpx
import pytest
from firebase_admin import auth

from service import autenticacion

DAVID = {"Authorization": "Bearer dev:uid-cliente-david:CLIENTE:david@example.com"}


# ── Enrutado ─────────────────────────────────────────────────

@pytest.mark.parametrize("ruta, servicio", [
    ("escaletas/evento-belgium", "ms-escaleta:8001"), ("artistas", "ms-escaleta:8001"),
    ("eventos", "ms-espacios:8002"), ("tipos-espacio", "ms-espacios:8002"), ("alquileres/x", "ms-espacios:8002"),
    ("usuarios/me", "ms-usuarios:8003"), ("entradas/validaciones", "ms-usuarios:8003"),
    ("productos/camiseta-2026/variantes", "ms-tienda:8004"), ("pedidos", "ms-tienda:8004"),
    ("estadisticas/resumen", "ms-analitica:8005"), ("interacciones", "ms-analitica:8005"),
])
def test_cada_recurso_va_a_su_microservicio(cliente_http, servicios, ruta, servicio, monkeypatch):
    from config import settings
    monkeypatch.setitem(settings.SERVICIOS, "ms-escaleta", "http://ms-escaleta:8001")
    monkeypatch.setitem(settings.SERVICIOS, "ms-espacios", "http://ms-espacios:8002")
    monkeypatch.setitem(settings.SERVICIOS, "ms-usuarios", "http://ms-usuarios:8003")
    monkeypatch.setitem(settings.SERVICIOS, "ms-analitica", "http://ms-analitica:8005")

    assert cliente_http.get(f"/api/v1/{ruta}").status_code == 200
    assert str(servicios.ultima.url) == f"http://{servicio}/api/v1/{ruta}"


def test_reenvia_metodo_cuerpo_y_parametros(cliente_http, servicios):
    cliente_http.post("/api/v1/pedidos?origen=web&origen=app", json={"entrega": "DOMICILIO"}, headers=DAVID)

    assert servicios.ultima.method == "POST"
    assert servicios.ultima.url.params.get_list("origen") == ["web", "app"]
    assert servicios.ultima.content == b'{"entrega":"DOMICILIO"}'


def test_devuelve_estado_cuerpo_y_cabeceras_del_microservicio(cliente_http, servicios):
    servicios.responder = lambda _: httpx.Response(
        201, json={"id": "pedido-1"}, headers={"Location": "/api/v1/pedidos/pedido-1", "X-Total-Count": "7"})

    r = cliente_http.post("/api/v1/pedidos", json={}, headers=DAVID)

    assert r.status_code == 201 and r.json() == {"id": "pedido-1"}
    assert r.headers["Location"] == "/api/v1/pedidos/pedido-1" and r.headers["X-Total-Count"] == "7"


def test_reenvia_los_errores_del_microservicio_sin_tocarlos(cliente_http, servicios):
    servicios.responder = lambda _: httpx.Response(409, json={"codigo": "SIN_STOCK", "mensaje": "No hay stock"})

    r = cliente_http.post("/api/v1/pedidos", json={}, headers=DAVID)

    assert r.status_code == 409 and r.json()["codigo"] == "SIN_STOCK"


def test_recurso_desconocido_da_404_con_el_formato_comun(cliente_http, servicios):
    r = cliente_http.get("/api/v1/facturas")

    assert r.status_code == 404
    assert r.json()["codigo"] == "RUTA_NO_ENCONTRADA" and r.json()["correlation_id"]
    assert servicios.peticiones == []


def test_las_rutas_internas_no_son_accesibles(cliente_http, servicios):
    assert cliente_http.post("/internal/v1/eventos/evento-belgium/reservas-aforo").status_code == 404
    assert cliente_http.post("/api/v1/internal/v1/eventos/x/reservas-aforo").status_code == 404
    assert servicios.peticiones == []


def test_rechaza_rutas_con_puntos(cliente_http, servicios):
    r = cliente_http.get("/api/v1/productos/%2E%2E/internal")

    assert r.status_code == 400 and r.json()["codigo"] == "RUTA_NO_VALIDA"
    assert servicios.peticiones == []


# ── Identidad ────────────────────────────────────────────────

def test_sin_token_no_envia_identidad(cliente_http, servicios):
    assert cliente_http.get("/api/v1/productos").status_code == 200
    assert "x-user-id" not in servicios.ultima.headers and "x-user-rol" not in servicios.ultima.headers


def test_el_cliente_no_puede_inventarse_la_identidad(cliente_http, servicios):
    cliente_http.get("/api/v1/usuarios", headers={
        "X-User-Id": "uid-admin-jose", "X-User-Rol": "ADMIN", "X-Service-Token": "token-servicio-dev"})

    cabeceras = servicios.ultima.headers
    assert "x-user-id" not in cabeceras and "x-user-rol" not in cabeceras and "x-service-token" not in cabeceras


def test_con_token_envia_la_identidad_y_no_el_token(cliente_http, servicios):
    cliente_http.get("/api/v1/usuarios/me", headers={**DAVID, "X-User-Rol": "ADMIN"})

    cabeceras = servicios.ultima.headers
    assert cabeceras["x-user-id"] == "uid-cliente-david"
    assert cabeceras["x-user-rol"] == "CLIENTE"  # el del token, no el que mandó el cliente
    assert cabeceras["x-user-email"] == "david@example.com"
    assert "authorization" not in cabeceras


def test_usuario_sin_rol_todavia_puede_registrarse(cliente_http, servicios):
    cliente_http.post("/api/v1/usuarios", json={"nombre": "Nuevo", "rol": "CLIENTE"},
                      headers={"Authorization": "Bearer dev:uid-nuevo::nuevo@example.com"})

    assert servicios.ultima.headers["x-user-id"] == "uid-nuevo"
    assert "x-user-rol" not in servicios.ultima.headers


@pytest.mark.parametrize("cabecera", ["Basic abc", "Bearer", "Bearer dev:", "Bearer dev::CLIENTE"])
def test_cabecera_authorization_no_valida_da_401(cliente_http, servicios, cabecera):
    r = cliente_http.get("/api/v1/usuarios/me", headers={"Authorization": cabecera})

    assert r.status_code == 401 and r.json()["codigo"] == "TOKEN_NO_VALIDO"
    assert servicios.peticiones == []


def test_tokens_de_desarrollo_desactivados_fuera_del_modo_desarrollo(cliente_http, servicios, monkeypatch):
    monkeypatch.setattr(autenticacion, "MODO_AUTENTICACION", "firebase")

    r = cliente_http.get("/api/v1/usuarios/me", headers=DAVID)

    assert r.status_code == 401 and servicios.peticiones == []


def test_token_de_firebase_valido(cliente_http, servicios, monkeypatch):
    monkeypatch.setattr(autenticacion.auth, "verify_id_token", lambda token, app: {
        "uid": "uid-firebase-1", "email": "ana@example.com", "rol": "proveedor"})

    cliente_http.get("/api/v1/alquileres", headers={"Authorization": "Bearer eyJhbGciOi.token.real"})

    assert servicios.ultima.headers["x-user-id"] == "uid-firebase-1"
    assert servicios.ultima.headers["x-user-rol"] == "PROVEEDOR"
    assert servicios.ultima.headers["x-user-email"] == "ana@example.com"


@pytest.mark.parametrize("error, codigo", [
    (auth.ExpiredIdTokenError("caducado", None), "TOKEN_CADUCADO"),
    (auth.InvalidIdTokenError("firma no válida"), "TOKEN_NO_VALIDO"),
])
def test_token_de_firebase_no_valido_da_401(cliente_http, servicios, monkeypatch, error, codigo):
    def verificar(token, app):
        raise error
    monkeypatch.setattr(autenticacion.auth, "verify_id_token", verificar)

    r = cliente_http.get("/api/v1/usuarios/me", headers={"Authorization": "Bearer eyJhbGciOi.token.malo"})

    assert r.status_code == 401 and r.json()["codigo"] == codigo
    assert servicios.peticiones == []


# ── Correlation-id, errores de red, CORS y SSE ───────────────

def test_propaga_el_correlation_id(cliente_http, servicios):
    r = cliente_http.get("/api/v1/productos", headers={"X-Correlation-Id": "cid-123"})

    assert servicios.ultima.headers["x-correlation-id"] == "cid-123"
    assert r.headers["X-Correlation-Id"] == "cid-123"


def test_crea_un_correlation_id_si_no_llega(cliente_http, servicios):
    r = cliente_http.get("/api/v1/productos")

    assert servicios.ultima.headers["x-correlation-id"] == r.headers["X-Correlation-Id"] != ""


def test_microservicio_caido_da_503(cliente_http, servicios):
    def caido(peticion):
        raise httpx.ConnectError("Connection refused", request=peticion)
    servicios.responder = caido

    r = cliente_http.get("/api/v1/productos")

    assert r.status_code == 503
    assert r.json()["codigo"] == "SERVICIO_NO_DISPONIBLE" and r.json()["detalles"] == {"servicio": "ms-tienda"}


def test_microservicio_lento_da_504(cliente_http, servicios):
    def lento(peticion):
        raise httpx.ReadTimeout("timeout", request=peticion)
    servicios.responder = lento

    assert cliente_http.get("/api/v1/productos").json()["codigo"] == "TIEMPO_AGOTADO"


def test_cors_permite_el_front_end_y_expone_las_cabeceras(cliente_http):
    r = cliente_http.options("/api/v1/productos", headers={
        "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Authorization, Content-Type"})
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"

    r = cliente_http.get("/api/v1/productos", headers={"Origin": "http://localhost:5173"})
    assert "X-Total-Count" in r.headers["access-control-expose-headers"]


def test_cors_rechaza_otros_origenes(cliente_http):
    r = cliente_http.get("/api/v1/productos", headers={"Origin": "https://web-maliciosa.example"})

    assert "access-control-allow-origin" not in r.headers


def test_sse_se_reenvia_como_flujo(cliente_http, servicios):
    servicios.responder = lambda _: httpx.Response(
        200, headers={"Content-Type": "text/event-stream"},
        content=b'data: {"tipo": "pase.modificado", "version": 5}\n\n')

    with cliente_http.stream("GET", "/api/v1/escaletas/evento-belgium/cambios",
                             headers={"Accept": "text/event-stream"}) as r:
        assert r.headers["content-type"].startswith("text/event-stream")
        assert b"pase.modificado" in r.read()
    assert servicios.ultima.extensions["timeout"]["read"] is None


def test_salud_resume_el_estado_de_cada_microservicio(cliente_http, servicios):
    servicios.responder = lambda p: (httpx.Response(200, json={"estado": "ok"}) if "tienda" in p.url.host
                                     else httpx.Response(500))

    r = cliente_http.get("/salud").json()

    assert r["estado"] == "ok"
    assert r["servicios"]["ms-tienda"] == "ok" and r["servicios"]["ms-escaleta"] == "error 500"
