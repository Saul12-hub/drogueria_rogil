from flask import Blueprint, render_template
from auth import login_requerido
from models.db_connection import get_connection
 
inventario_bp = Blueprint('inventario', __name__)
 
 
@inventario_bp.route('/inventario')
@login_requerido
def inventario():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            p.nombre,
            l.numero_lote,
            l.fecha_ingreso,
            l.fecha_vencimiento,
            l.cantidad_disponible
        FROM productos p
        JOIN lotes l 
            ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY 
            p.nombre ASC,
            l.fecha_ingreso ASC
    """)
    datos = cursor.fetchall()
    conn.close()
    return render_template('inventario.html', datos=datos)