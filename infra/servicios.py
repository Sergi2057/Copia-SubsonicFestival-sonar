# infra/servicios.py
# Utilidades del docker-compose global, que construye cada servicio desde su carpeta del repositorio.
#
# Uso (desde la carpeta infra, con Python 3.10+ y todo ya arrancado):
#   python servicios.py poblar             -> carga los datos de prueba
#   python servicios.py limpiar            -> borra las copias de infra/servicios/ de antes de juntar las ramas
import subprocess
import sys
from pathlib import Path

INFRA = Path(__file__).resolve().parent
DESTINO = INFRA / "servicios"
SERVICIOS = ["ms-escaleta", "ms-espacios", "ms-usuarios", "ms-tienda", "ms-analitica", "gateway"]
# ms-analitica no se puebla: en el entorno global se alimenta de los eventos reales
POBLAR = ["ms-espacios", "ms-escaleta", "ms-usuarios", "ms-tienda"]
COMPOSE = ["docker", "compose", "-f", str(INFRA / "docker-compose.global.yml")]


def poblar() -> None:
    for servicio in POBLAR:
        print(f"Poblando {servicio}…")
        subprocess.run([*COMPOSE, "exec", "-T", servicio, "python", "scripts/poblar_bd.py"], check=True)


def limpiar() -> None:
    for servicio in SERVICIOS:
        carpeta = DESTINO / servicio
        if carpeta.exists():
            subprocess.run(["git", "worktree", "remove", "--force", str(carpeta)], cwd=INFRA, check=True)
            print(f"  borrada la copia de {servicio}")


if __name__ == "__main__":
    orden = sys.argv[1] if len(sys.argv) > 1 else ""
    if orden == "poblar":
        poblar()
    elif orden == "limpiar":
        limpiar()
    else:
        print(open(__file__, encoding="utf-8").read().split("import")[0])
        sys.exit(1)
