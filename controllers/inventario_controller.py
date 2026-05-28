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
            p.id_producto,
            p.nombre,
            l.numero_lote,
            l.cantidad_disponible,
            l.fecha_ingreso,
            l.fecha_vencimiento
        FROM productos p
        LEFT JOIN lotes l 
            ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY 
            p.nombre ASC,
            l.fecha_ingreso ASC
    """)

    rows = cursor.fetchall()

    conn.close()

    productos = {}

    for row in rows:

        id_producto = row['id_producto']

        if id_producto not in productos:

            productos[id_producto] = {
                'nombre': row['nombre'],
                'stock_total': 0,
                'lotes_fifo': []
            }

        productos[id_producto]['stock_total'] += row['cantidad_disponible']

        productos[id_producto]['lotes_fifo'].append({
            'numero_lote': row['numero_lote'],
            'cantidad': row['cantidad_disponible'],
            'fecha_ingreso': row['fecha_ingreso'],
            'fecha_vencimiento': row['fecha_vencimiento']
        })

    datos = list(productos.values())

    return render_template(
        'inventario.html',
        datos=datos
    )