from models.db_connection import get_connection
 
 
def get_all_productos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return productos
 
 
def get_producto_by_id(producto_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos WHERE id_producto = %s", (producto_id,))
    producto = cursor.fetchone()
    conn.close()
    return producto
 
 
def get_productos_select():
    """Retorna solo id y nombre, útil para dropdowns."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_producto, nombre FROM productos")
    productos = cursor.fetchall()
    conn.close()
    return productos
 