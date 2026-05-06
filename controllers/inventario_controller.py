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
        SELECT p.nombre,
               SUM(l.cantidad_disponible) AS stock_total
        FROM productos p
        JOIN lotes l ON p.id_producto = l.id_producto
        GROUP BY p.id_producto
    """)
    datos = cursor.fetchall()
    conn.close()
    return render_template('inventario.html', datos=datos)