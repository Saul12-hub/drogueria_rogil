from flask import Blueprint, render_template, request
from datetime import datetime, timedelta
from auth import login_requerido
from models.db_connection import get_connection
from models.producto import get_productos_select, get_producto_by_id
from models.lote import get_lotes_disponibles, get_lotes_por_producto, descontar_lote
from models.venta import crear_venta, actualizar_total_venta, insertar_detalle_venta
 
ventas_bp = Blueprint('ventas', __name__)
 
 
def procesar_venta(producto_id, cantidad):
    """
    Aplica lógica FIFO para procesar una venta.
    Retorna (error: str | None, total_venta: float)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    producto = get_producto_by_id(producto_id)
    if not producto:
        conn.close()
        return "Producto no encontrado", 0
 
    precio = producto['precio_venta']
    lotes = get_lotes_por_producto(producto_id)
    total_disponible = sum(l['cantidad_disponible'] for l in lotes)
 
    if total_disponible < cantidad:
        conn.close()
        return "Stock insuficiente", 0
 
    # Reabrir conexión para la transacción
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    restante = cantidad
    total_venta = 0
    id_venta = crear_venta(cursor)
 
    for lote in lotes:
        if restante <= 0:
            break
        usar = min(lote['cantidad_disponible'], restante)
        subtotal = usar * precio
        descontar_lote(cursor, lote['id_lote'], usar)
        insertar_detalle_venta(cursor, id_venta, producto_id, lote['id_lote'], usar, precio, subtotal)
        total_venta += subtotal
        restante -= usar
 
    actualizar_total_venta(cursor, id_venta, total_venta)
    conn.commit()
    conn.close()
    return None, total_venta
 
 
@ventas_bp.route('/ventas', methods=['GET', 'POST'])
@login_requerido
def ventas():
    error = None
 
    if request.method == 'POST':
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])
        error, _ = procesar_venta(producto_id, cantidad)
 
    productos = get_productos_select()
    lotes = get_lotes_disponibles()
 
    return render_template(
        'ventas.html',
        productos=productos,
        lotes=lotes,
        error=error,
        now=datetime.now().date(),
        timedelta=timedelta
    )