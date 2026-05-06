from flask import Blueprint, render_template
from auth import login_requerido
from models.db_connection import get_connection
 
alertas_bp = Blueprint('alertas', __name__)
 
 
def get_alertas_data():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            p.nombre,
            l.numero_lote,
            l.fecha_vencimiento,
            l.cantidad_disponible,
            DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY l.fecha_vencimiento ASC
    """)
    datos = cursor.fetchall()
    conn.close()
    return datos
 
 
@alertas_bp.route('/alertas')
@login_requerido
def alertas():
    datos = get_alertas_data()
    return render_template('alertas.html', datos=datos)
