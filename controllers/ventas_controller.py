from flask import Blueprint, render_template, request, send_file
from datetime import datetime, timedelta
from auth import login_requerido
from models.db_connection import get_connection
from models.producto import get_productos_select, get_producto_by_id
from models.lote import get_lotes_disponibles, get_lotes_por_producto, descontar_lote
from models.venta import crear_venta, actualizar_total_venta, insertar_detalle_venta
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

ventas_bp = Blueprint('ventas', __name__)


def procesar_venta(producto_id, cantidad):
    """
    Aplica lógica FIFO para procesar una venta.
    Retorna (error: str | None, total_venta: float)
    """
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        producto = get_producto_by_id(producto_id)
        if not producto:
            return "Producto no encontrado", 0

        precio = producto['precio_venta']
        lotes = get_lotes_por_producto(producto_id)
        total_disponible = sum(l['cantidad_disponible'] for l in lotes)

        if total_disponible < cantidad:
            return "Stock insuficiente", 0

        restante = cantidad
        total_venta = 0
        
        # ✅ CORREGIDO: pasar los parámetros correctos
        id_venta = crear_venta(cursor, 0, 'Venta realizada')

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
        return None, total_venta
        
    except Exception as e:
        conn.rollback()
        return f"Error al procesar venta: {str(e)}", 0
    finally:
        conn.close()


@ventas_bp.route('/ventas', methods=['GET', 'POST'])
@login_requerido
def ventas():
    error = None
    success = None

    if request.method == 'POST':
        producto_id = request.form['producto_id']
        cantidad_str = request.form['cantidad']
        
        # Validar cantidad positiva
        if not cantidad_str.isdigit() or int(cantidad_str) <= 0:
            error = "La cantidad debe ser un número positivo"
        else:
            cantidad = int(cantidad_str)
            error, total = procesar_venta(producto_id, cantidad)
            if not error:
                success = f"✅ Venta realizada con éxito. Total: Q{total:.2f}"

    productos = get_productos_select()
    lotes = get_lotes_disponibles()

    return render_template(
        'ventas.html',
        productos=productos,
        lotes=lotes,
        error=error,
        success=success,
        now=datetime.now().date(),
        timedelta=timedelta
    )


# ✅ NUEVO: Reporte PDF de productos próximos a vencer (REQUISITO OBLIGATORIO)
@ventas_bp.route('/reporte_pdf')
@login_requerido
def reporte_pdf():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT p.nombre, l.numero_lote, l.fecha_vencimiento, l.cantidad_disponible,
               DATEDIFF(l.fecha_vencimiento, CURDATE()) as dias
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        AND l.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        ORDER BY l.fecha_vencimiento ASC
    """)
    
    datos = cursor.fetchall()
    conn.close()
    
    # Crear PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elementos = []
    
    styles = getSampleStyleSheet()
    titulo = Paragraph("Reporte de Productos Próximos a Vencer", styles['Title'])
    elementos.append(titulo)
    
    # Espacio
    elementos.append(Paragraph("<br/><br/>", styles['Normal']))
    
    # Tabla de datos
    data = [['Producto', 'Lote', 'Vencimiento', 'Días', 'Stock']]
    for row in datos:
        data.append([
            row['nombre'], 
            row['numero_lote'], 
            str(row['fecha_vencimiento']), 
            str(row['dias']), 
            str(row['cantidad_disponible'])
        ])
    
    tabla = Table(data)
    tabla.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elementos.append(tabla)
    doc.build(elementos)
    buffer.seek(0)
    
    return send_file(
        buffer, 
        download_name='productos_proximos_vencer.pdf', 
        as_attachment=False,
        mimetype='application/pdf'
    )