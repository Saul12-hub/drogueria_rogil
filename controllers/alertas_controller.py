from flask import Blueprint, render_template
from auth import login_requerido
from models.db_connection import get_connection

alertas_bp = Blueprint('alertas', __name__)


@alertas_bp.route('/alertas')
@login_requerido
def alertas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    # Total de productos
    cursor.execute("SELECT COUNT(*) AS total FROM productos")
    total_productos = cursor.fetchone()['total']

    # Total de lotes activos (con stock > 0)
    cursor.execute("SELECT COUNT(*) AS total FROM lotes WHERE cantidad_disponible > 0")
    total_lotes = cursor.fetchone()['total']

    # Productos por vencer (próximos 7 días)
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM lotes
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) BETWEEN 0 AND 7
        AND cantidad_disponible > 0
    """)
    por_vencer = cursor.fetchone()['total']

    # Ventas de hoy
    cursor.execute("""
        SELECT IFNULL(SUM(total), 0) AS total
        FROM ventas
        WHERE DATE(fecha_venta) = CURDATE()
    """)
    ventas_hoy = cursor.fetchone()['total']

    # TODOS los lotes con colores según estado (para el listado completo)
    cursor.execute("""
        SELECT 
            p.nombre,
            l.numero_lote,
            l.fecha_vencimiento,
            l.cantidad_disponible,
            DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias,
            CASE 
                WHEN DATEDIFF(l.fecha_vencimiento, CURDATE()) < 0 THEN 'vencido'
                WHEN DATEDIFF(l.fecha_vencimiento, CURDATE()) <= 7 THEN 'por_vencer'
                ELSE 'buen_estado'
            END AS estado
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY l.fecha_vencimiento ASC
    """)
    todos_lotes = cursor.fetchall()

    conn.close()

    return render_template(
        'alertas.html',
        total_productos=total_productos,
        total_lotes=total_lotes,
        por_vencer=por_vencer,
        ventas_hoy=ventas_hoy,
        lotes=todos_lotes
    )