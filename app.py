from flask import Flask, render_template, request, redirect, session, flash, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os
 
from models.db_connection import get_connection
from models.lote import get_lotes_por_vencer, get_total_lotes_activos
from models.producto import get_all_productos
from models.venta import get_ventas_hoy
from auth import login_requerido, rol_requerido
 
# Blueprints
from controllers.alertas_controller import alertas_bp
from controllers.inventario_controller import inventario_bp
from controllers.ventas_controller import ventas_bp
from controllers.productos_controller import productos_bp
 
load_dotenv()
 
app = Flask(__name__, template_folder="views")
app.secret_key = os.getenv("SECRET_KEY", "secretkey")
 
# ── Registrar Blueprints
app.register_blueprint(alertas_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(ventas_bp)
app.register_blueprint(productos_bp)
 
 
# ── DASHBOARD 
@app.route('/')
@login_requerido
def home():
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

    # Alertas (productos próximos a vencer - últimos 10)
    cursor.execute("""
        SELECT p.nombre, l.numero_lote, l.fecha_vencimiento,
               l.cantidad_disponible,
               DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        AND l.fecha_vencimiento BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        ORDER BY l.fecha_vencimiento ASC
        LIMIT 10
    """)
    alertas = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        total_productos=total_productos,
        total_lotes=total_lotes,
        por_vencer=por_vencer,
        ventas_hoy=ventas_hoy,
        alertas=alertas
    )
 
 
# ── PRODUCTOS (COMENTADO - AHORA USA EL BLUEPRINT)
# @app.route('/productos')
# @login_requerido
# def productos():
#     return render_template('productos.html', productos=get_all_productos())
 
 
# ── DEVOLUCIONES (AJUSTES DE INVENTARIO)
@app.route('/devoluciones', methods=['GET', 'POST'])
@login_requerido
def devoluciones():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Crear tabla bitacora_ajustes si no existe (con nuevos campos)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bitacora_ajustes (
            id_ajuste INT AUTO_INCREMENT PRIMARY KEY,
            tipo VARCHAR(20),
            id_producto INT,
            cantidad INT,
            justificacion VARCHAR(255),
            lote VARCHAR(50),
            fecha_ingreso DATE,
            fecha_vencimiento DATE,
            fecha DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    
    # Si es POST (guardar movimiento)
    if request.method == 'POST':
        tipo = request.form['tipo']
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])
        justificacion = request.form['justificacion']
        
        if tipo == 'entrada':
            lote = request.form.get('lote', f'LOTE-{producto_id}-{cantidad}')
            fecha_ingreso = request.form.get('fecha_ingreso')
            fecha_vencimiento = request.form.get('fecha_vencimiento')
            
            # Crear un nuevo lote con la cantidad ingresada
            cursor.execute("""
                INSERT INTO lotes (id_producto, numero_lote, fecha_ingreso, fecha_vencimiento, cantidad_inicial, cantidad_disponible)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (producto_id, lote, fecha_ingreso, fecha_vencimiento, cantidad, cantidad))
            flash(f'✅ Se agregaron {cantidad} unidades al inventario (Lote: {lote})', 'success')
            
            # Registrar en bitácora
            cursor.execute("""
                INSERT INTO bitacora_ajustes (tipo, id_producto, cantidad, justificacion, lote, fecha_ingreso, fecha_vencimiento)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (tipo, producto_id, cantidad, justificacion, lote, fecha_ingreso, fecha_vencimiento))
            
        elif tipo == 'salida':
            # Descontar del lote más antiguo (FIFO)
            cursor.execute("""
                SELECT id_lote, cantidad_disponible
                FROM lotes
                WHERE id_producto = %s AND cantidad_disponible > 0
                ORDER BY fecha_ingreso ASC
            """, (producto_id,))
            lotes = cursor.fetchall()
            
            restante = cantidad
            for l in lotes:
                if restante <= 0:
                    break
                descontar = min(l['cantidad_disponible'], restante)
                nueva_cantidad = l['cantidad_disponible'] - descontar
                
                if nueva_cantidad == 0:
                    cursor.execute("DELETE FROM lotes WHERE id_lote = %s", (l['id_lote'],))
                else:
                    cursor.execute("""
                        UPDATE lotes SET cantidad_disponible = %s WHERE id_lote = %s
                    """, (nueva_cantidad, l['id_lote']))
                restante -= descontar
            
            if restante > 0:
                flash(f'⚠️ Solo se pudieron descontar {cantidad - restante} unidades. Stock insuficiente.', 'warning')
            else:
                flash(f'✅ Se descontaron {cantidad} unidades del inventario', 'success')
            
            # Registrar en bitácora (sin fechas de lote)
            cursor.execute("""
                INSERT INTO bitacora_ajustes (tipo, id_producto, cantidad, justificacion)
                VALUES (%s, %s, %s, %s)
            """, (tipo, producto_id, cantidad, justificacion))
        
        conn.commit()
        return redirect(url_for('devoluciones'))
    
    # GET: mostrar formulario y movimientos
    # Obtener productos
    cursor.execute("SELECT id_producto, nombre FROM productos ORDER BY nombre")
    productos = cursor.fetchall()
    
    # Obtener historial de movimientos
    cursor.execute("""
        SELECT a.*, p.nombre as producto_nombre
        FROM bitacora_ajustes a
        JOIN productos p ON p.id_producto = a.id_producto
        ORDER BY a.fecha DESC
        LIMIT 50
    """)
    movimientos = cursor.fetchall()
    
    conn.close()
    
    from datetime import date
    return render_template('devoluciones.html', 
                         productos=productos, 
                         movimientos=movimientos,
                         now_date=date.today().isoformat())
 
 
# ── PROVEEDORES 
@app.route('/proveedores', methods=['GET', 'POST'])
@rol_requerido(['admin'])
def proveedores():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO proveedores (nombre, telefono, correo, direccion)
            VALUES (%s, %s, %s, %s)
        """, (
            request.form['nombre'],
            request.form['telefono'],
            request.form['correo'],
            request.form['direccion']
        ))
        conn.commit()
        flash('✅ Proveedor agregado correctamente', 'success')
 
    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)


# ── ELIMINAR PROVEEDOR
@app.route('/proveedores/eliminar/<int:id_proveedor>')
@rol_requerido(['admin'])
def eliminar_proveedor(id_proveedor):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verificar si el proveedor tiene lotes asociados
    cursor.execute("SELECT COUNT(*) as total FROM lotes WHERE id_proveedor = %s", (id_proveedor,))
    resultado = cursor.fetchone()
    
    if resultado[0] > 0:
        flash('⚠️ No se puede eliminar el proveedor porque tiene lotes asociados.', 'danger')
    else:
        cursor.execute("DELETE FROM proveedores WHERE id_proveedor = %s", (id_proveedor,))
        conn.commit()
        flash('✅ Proveedor eliminado correctamente', 'success')
    
    conn.close()
    return redirect(url_for('proveedores'))
 
 
# ── REGISTRO (SOLO CREA USUARIOS EMPLEADO)
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    if request.method == 'POST':
        # Siempre asignar rol de empleado (id_rol = 2)
        rol_id = 2
        
        # Verificar si el usuario ya existe
        cursor.execute("SELECT * FROM usuarios WHERE username = %s", (request.form['username'],))
        existe = cursor.fetchone()
        
        if existe:
            conn.close()
            return "El nombre de usuario ya existe. <a href='/registro'>Intentar de nuevo</a>", 400
        
        cursor.execute("""
            INSERT INTO usuarios (username, password, id_rol)
            VALUES (%s, %s, %s)
        """, (
            request.form['username'],
            generate_password_hash(request.form['password']),
            rol_id
        ))
        conn.commit()
        conn.close()
        flash('✅ Usuario registrado correctamente como EMPLEADO', 'success')
        return redirect('/login')
    
    conn.close()
    return render_template('registro.html')


# ── LOGIN (SOLO ADMIN Y EMPLEADO)
@app.route('/login', methods=['GET', 'POST'])
def login():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
    if request.method == 'POST':
        cursor.execute("""
            SELECT u.*, r.nombre AS rol
            FROM usuarios u
            JOIN roles r ON r.id_rol = u.id_rol
            WHERE username = %s
        """, (request.form['username'],))
        user = cursor.fetchone()
        conn.close()
 
        if user and check_password_hash(user['password'], request.form['password']):
            # Verificar que el rol sea admin o empleado
            if user['rol'] in ['admin', 'empleado']:
                session['user'] = user['username']
                session['rol']  = user['rol']
                return redirect('/')
            else:
                return "Acceso denegado. Solo administradores y empleados pueden ingresar.", 403
        return "Credenciales incorrectas", 401
 
    conn.close()
    return render_template('login.html')
 
 
# ── LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')
 
 
# ── EJECUCIÓN
if __name__ == '__main__':
    app.run(debug=True)