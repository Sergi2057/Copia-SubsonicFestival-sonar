# Tests de la plantilla. En cada microservicio ya existen config.settings y config.errores;
# aquí se simulan para poder probar la plantilla sola.
import sys
import types
from contextvars import ContextVar
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

settings = types.ModuleType("config.settings")
settings.NOMBRE_SERVICIO = "ms-prueba"
errores = types.ModuleType("config.errores")
errores.correlation_id_actual = ContextVar("correlation_id", default="")
config = types.ModuleType("config")
config.settings, config.errores = settings, errores
sys.modules.update({"config": config, "config.settings": settings, "config.errores": errores})
