from unittest.mock import Mock
from uuid import UUID

import pytest

from eventos import manejadores


@pytest.mark.parametrize(
    ("tipo", "datos", "servicio", "funcion", "argumentos"),
    [
        (
            "usuarios.entrada.comprada",
            {"reserva_id": "11111111-1111-4111-8111-111111111111"},
            "aforo_service",
            "confirmar_reserva",
            (UUID("11111111-1111-4111-8111-111111111111"),),
        ),
        (
            "usuarios.entrada.cancelada",
            {"evento_id": "evento-test", "tipo_pase": "WEEKEND"},
            "aforo_service",
            "liberar_plaza_vendida",
            ("evento-test", "WEEKEND"),
        ),
        (
            "usuarios.proveedor.actualizado",
            {"proveedor_id": "prov-1", "activo": True},
            "espacio_service",
            "actualizar_replica_proveedor",
            ({"proveedor_id": "prov-1", "activo": True},),
        ),
        (
            "usuarios.proveedor.desactivado",
            {"proveedor_id": "prov-1", "activo": False},
            "espacio_service",
            "actualizar_replica_proveedor",
            ({"proveedor_id": "prov-1", "activo": False},),
        ),
        (
            "usuarios.usuario.eliminado",
            {"usuario_id": "prov-1"},
            "espacio_service",
            "anonimizar_alquileres",
            ("prov-1",),
        ),
    ],
)
def test_manejar_despacha_evento_y_cierra_sesion(
    monkeypatch, tipo, datos, servicio, funcion, argumentos
):
    db = Mock()
    crear_sesion = Mock(return_value=db)
    manejar_accion = Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", crear_sesion)
    monkeypatch.setattr(getattr(manejadores, servicio), funcion, manejar_accion)

    manejadores.manejar({"id_evento": f"test-{tipo}", "tipo": tipo, "datos": datos})

    crear_sesion.assert_called_once_with()
    manejar_accion.assert_called_once_with(db, *argumentos)
    db.close.assert_called_once_with()


def test_manejar_rechaza_evento_desconocido_y_cierra_sesion(monkeypatch):
    db = Mock()
    monkeypatch.setattr(manejadores, "SessionLocal", Mock(return_value=db))

    with pytest.raises(ValueError, match="Evento no soportado"):
        manejadores.manejar({"tipo": "usuarios.entrada.desconocida", "datos": {}})

    db.close.assert_called_once_with()


def test_consumidor_escucha_solo_eventos_de_entrada_relevantes():
    assert manejadores.consumidor.claves == [
        "usuarios.entrada.comprada",
        "usuarios.entrada.cancelada",
        "usuarios.proveedor.*",
        "usuarios.usuario.eliminado",
    ]
