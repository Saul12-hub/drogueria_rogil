from flask import Blueprint, render_template
from auth import login_requerido
from models.db_connection import get_connection

inventario_bp = Blueprint('inventario', __name__)


@inventario_bp.route('/inventario')
@login_requerido
def inventario():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Obtener productos con sus lotes (FIFO)
    cursor.execute("""
        SELECT 
            p.id_producto,
            p.nombre,
            SUM(l.cantidad_disponible) AS stock_total,
            GROUP_CONCAT(
                CONCAT(l.numero_lote, ' (', l.cantidad_disponible, ' unid)') 
                ORDER BY l.fecha_ingreso ASC 
                SEPARATOR ' | '
            ) AS lotes_fifo
        FROM productos p
        LEFT JOIN lotes l ON p.id_producto = l.id_producto AND l.cantidad_disponible > 0
        GROUP BY p.id_producto
        ORDER BY p.nombre ASC
    """)
    
    datos = cursor.fetchall()
    conn.close()
    
    # Procesar datos para mostrar
    for item in datos:
        if not item['lotes_fifo']:
            item['lotes_fifo'] = 'Sin stock'
    
    return render_template('inventario.html', datos=datos)