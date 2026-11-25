# ms-espacios/config/seguridad.py
# El API Gateway valida el JWT de Firebase y añade las cabeceras X-User-Id y X-User-Rol.
# Los microservicios solo leen esas cabeceras (no verifican tokens ni hablan con Firebase).
from dataclasses import dataclass
from fastapi import Header
from config.errores import ErrorApi


@dataclass
class UsuarioActual:
    id: str
    rol: str  # cliente | proveedor | admin | staff (en minúsculas)


def usuario_opcional(
    x_user_id: str | None = Header(default=None),
    x_user_rol: str | None = Header(default=None),
) -> UsuarioActual | None:
    """Para endpoints públicos que muestran más información a ciertos roles."""
    if x_user_id and x_user_rol:
        return UsuarioActual(id=x_user_id, rol=x_user_rol.lower())
    return None


def usuario_actual(
    x_user_id: str | None = Header(default=None),
    x_user_rol: str | None = Header(default=None),
) -> UsuarioActual:
    if not x_user_id or not x_user_rol:
        raise ErrorApi(401, "NO_AUTENTICADO", "Falta el token o no es válido")
    return UsuarioActual(id=x_user_id, rol=x_user_rol.lower())


def requiere_rol(*roles: str):
    """Dependencia que exige uno de los roles indicados."""

    def dependencia(
        x_user_id: str | None = Header(default=None),
        x_user_rol: str | None = Header(default=None),
    ) -> UsuarioActual:
        usuario = usuario_actual(x_user_id, x_user_rol)
        if usuario.rol not in roles:
            raise ErrorApi(403, "SIN_PERMISO", "El rol del usuario no permite esta operación")
        return usuario

    return dependencia


def servicio_interno(x_service_token: str | None = Header(default=None)) -> None:
    """Rutas /internal/v1: solo otros microservicios, con el token compartido de la red interna."""
    from config.settings import TOKEN_SERVICIO
    if x_service_token != TOKEN_SERVICIO:
        raise ErrorApi(401, "NO_AUTENTICADO", "Token de servicio no válido")
