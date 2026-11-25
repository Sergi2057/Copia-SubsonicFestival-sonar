# ms-tienda/scripts/poblar_bd.py
# Datos de prueba iniciales (los productos de la versión monolítica, ahora con stock por talla)
# Uso: python scripts/poblar_bd.py   (desde la carpeta ms-tienda)
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.database import SessionLocal, crear_tablas  # noqa: E402
from model.models import EventoRecogida, Producto, Variante  # noqa: E402

# Eventos que el poblar_bd.py de ms-espacios crea ya PUBLICADOS. Como ese script no publica
# eventos, aquí se dan de alta a mano como puntos de recogida.
EVENTOS_PUBLICADOS = ["evento-belgium", "evento-thailand", "evento-brasil"]

TALLAS_ROPA = ["XS", "S", "M", "L", "XL"]

PRODUCTOS = [
    # (producto, {talla: stock})
    (Producto(id="camiseta-2026", nombre="Camiseta Oficial", descripcion="Camiseta Subsonic 2026",
              precio=29.99, imagen_url="/camiseta.jpg"),
     {t: 30 for t in TALLAS_ROPA}),
    (Producto(id="gorra-black", nombre="Gorra Black", descripcion="Talla única ajustable",
              precio=19.99, imagen_url="/gorra.jpg"),
     {"UNICA": 100}),
    (Producto(id="sudadera-red", nombre="Sudadera Red", descripcion="Sudadera Subsonic",
              precio=49.99, imagen_url="/sudadera.jpg"),
     {t: 0 for t in TALLAS_ROPA}),
    (Producto(id="camiseta-belgium-2026", nombre="Camiseta Subsonic Belgium", descripcion="Edición exclusiva",
              precio=34.99, imagen_url="/camiseta.jpg", evento_id="evento-belgium"),
     {"M": 3, "L": 10}),
]

crear_tablas()
db = SessionLocal()
try:
    for producto, stock_por_talla in PRODUCTOS:
        if db.get(Producto, producto.id):
            continue
        db.add(producto)
        for talla, stock in stock_por_talla.items():
            db.add(Variante(producto_id=producto.id, talla=talla, stock=stock))
    for evento_id in EVENTOS_PUBLICADOS:
        if not db.get(EventoRecogida, evento_id):
            db.add(EventoRecogida(evento_id=evento_id, estado="PUBLICADO"))
    db.commit()
    print("[OK] Productos, variantes y puntos de recogida creados")
finally:
    db.close()
