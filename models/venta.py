from models.db_connection import get_connection
 
 
def get_ventas_hoy():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT IFNULL(SUM(total), 0) AS total
        FROM ventas
        WHERE DATE(fecha_venta) = CURDATE()
    """)
    total = cursor.fetchone()['total']
    conn.close()
    return total
 
 
def crear_venta(cursor, total=0, observaciones='Venta realizada'):
    """Inserta una nueva venta y retorna su ID. Usa cursor externo para transacciones."""
    cursor.execute("""
        INSERT INTO ventas (fecha_venta, total, observaciones)
        VALUES (NOW(), %s, %s)
    """, (total, observaciones))
    return cursor.lastrowid
 
 
def actualizar_total_venta(cursor, id_venta, total):
    cursor.execute("""
        UPDATE ventas SET total = %s WHERE id_venta = %s
    """, (total, id_venta))
 
 
def insertar_detalle_venta(cursor, id_venta, id_producto, id_lote, cantidad, precio, subtotal):
    cursor.execute("""
        INSERT INTO detalle_ventas
            (id_venta, id_producto, id_lote, cantidad, precio_unitario, subtotal)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (id_venta, id_producto, id_lote, cantidad, precio, subtotal))