from models.db_connection import get_connection
 
 
def get_lotes_disponibles():
    """Retorna todos los lotes con stock > 0, ordenados por fecha de ingreso (FIFO)."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT l.*, p.nombre
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY l.fecha_ingreso ASC
    """)
    lotes = cursor.fetchall()
    conn.close()
    return lotes
 
 
def get_lotes_por_producto(producto_id):
    """Retorna los lotes disponibles de un producto específico, ordenados FIFO."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT * FROM lotes
        WHERE id_producto = %s AND cantidad_disponible > 0
        ORDER BY fecha_ingreso ASC
    """, (producto_id,))
    lotes = cursor.fetchall()
    conn.close()
    return lotes
 
 
def get_total_lotes_activos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS total FROM lotes WHERE cantidad_disponible > 0")
    total = cursor.fetchone()['total']
    conn.close()
    return total
 
 
def get_lotes_por_vencer(dias=7):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM lotes
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) BETWEEN 0 AND %s
        AND cantidad_disponible > 0
    """, (dias,))
    total = cursor.fetchone()['total']
    conn.close()
    return total
 
 
def descontar_lote(cursor, id_lote, cantidad):
    """Descuenta una cantidad del lote dado. Usa cursor externo para transacciones."""
    cursor.execute("""
        UPDATE lotes
        SET cantidad_disponible = cantidad_disponible - %s
        WHERE id_lote = %s
    """, (cantidad, id_lote))
 