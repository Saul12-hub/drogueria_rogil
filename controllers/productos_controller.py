from flask import Blueprint, render_template, request, redirect, url_for, flash
from auth import login_requerido
from models.db_connection import get_connection

productos_bp = Blueprint('productos', __name__)

@productos_bp.route('/productos', methods=['GET', 'POST'])
@login_requerido
def productos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Si es POST (enviaron el formulario)
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        
        # Verificar si el producto ya existe
        cursor.execute("SELECT * FROM productos WHERE nombre = %s", (nombre,))
        existe = cursor.fetchone()
        
        if existe:
            flash(f'⚠️ El producto "{nombre}" ya existe', 'warning')
        else:
            # Insertar producto (sin lote ni fecha)
            cursor.execute("""
                INSERT INTO productos (nombre, precio_venta)
                VALUES (%s, %s)
            """, (nombre, precio))
            conn.commit()
            flash(f'✅ Producto "{nombre}" agregado correctamente', 'success')
        
        return redirect(url_for('productos.productos'))
    
    # GET: mostrar productos con SUMA de stock
    cursor.execute("""
        SELECT 
            p.id_producto, 
            p.nombre, 
            p.precio_venta,
            COALESCE(SUM(l.cantidad_disponible), 0) AS stock_total
        FROM productos p
        LEFT JOIN lotes l ON p.id_producto = l.id_producto
        GROUP BY p.id_producto
        ORDER BY p.id_producto DESC
    """)
    productos = cursor.fetchall()
    conn.close()
    
    return render_template('productos.html', productos=productos)