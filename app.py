from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
from dotenv import load_dotenv
import os
import mysql.connector

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__, template_folder="views")
app.secret_key = os.getenv("SECRET_KEY", "clave_secreta")

#  CONEXIÓN
def get_connection():
    return mysql.connector.connect(
        host="127.0.0.1", 
        user="root",
        password="Clave_tu_baseDatos", 
        database="drogueria_rogil"
    )
    
#  DECORADOR LOGIN
def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return wrapper

# 🔒 DECORADOR ROL
def rol_requerido(roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user' not in session:
                return redirect('/login')
            if session.get('rol') not in roles:
                return "Acceso restringido"
            return f(*args, **kwargs)
        return wrapper
    return decorator

#  DASHBOARD
@app.route('/')
@login_requerido
def home():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
        
    cursor.execute("SELECT COUNT(*) AS total FROM productos")
    total_productos = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total 
        FROM lotes 
        WHERE cantidad_disponible > 0
    """)
    total_lotes = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM lotes
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) BETWEEN 0 AND 7
        AND cantidad_disponible > 0
    """)
    por_vencer = cursor.fetchone()['total']

    cursor.execute("""
        SELECT IFNULL(SUM(total),0) AS total
        FROM ventas
        WHERE DATE(fecha_venta) = CURDATE()
    """)
    ventas_hoy = cursor.fetchone()['total']

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

#  PRODUCTOS
@app.route('/productos')
@login_requerido
def productos():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    conn.close()
    return render_template('productos.html', productos=productos)

#  VENTAS (FIFO)
@app.route('/ventas', methods=['GET', 'POST'])
@login_requerido
def ventas():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    error = None

    if request.method == 'POST':
        producto_id = request.form['producto_id']
        cantidad = int(request.form['cantidad'])

        cursor.execute("""
            SELECT precio_venta 
            FROM productos 
            WHERE id_producto = %s
        """, (producto_id,))
        producto = cursor.fetchone()

        if not producto:
            error = "Producto no encontrado"
        else:
            precio = producto['precio_venta']

            cursor.execute("""
                SELECT * FROM lotes
                WHERE id_producto = %s AND cantidad_disponible > 0
                ORDER BY fecha_ingreso ASC
            """, (producto_id,))
            
            lotes = cursor.fetchall()
            total_disponible = sum(l['cantidad_disponible'] for l in lotes)

            if total_disponible < cantidad:
                error = "Stock insuficiente"
            else:
                restante = cantidad
                total_venta = 0

                cursor.execute("""
                    INSERT INTO ventas (fecha_venta, total, observaciones)
                    VALUES (NOW(), 0, 'Venta realizada')
                """)
                id_venta = cursor.lastrowid

                for lote in lotes:
                    if restante <= 0:
                        break

                    usar = min(lote['cantidad_disponible'], restante)
                    subtotal = usar * precio

                    cursor.execute("""
                        UPDATE lotes
                        SET cantidad_disponible = cantidad_disponible - %s
                        WHERE id_lote = %s
                    """, (usar, lote['id_lote']))

                    cursor.execute("""
                        INSERT INTO detalle_ventas 
                        (id_venta, id_producto, id_lote, cantidad, precio_unitario, subtotal)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (id_venta, producto_id, lote['id_lote'], usar, precio, subtotal))

                    total_venta += subtotal
                    restante -= usar

                cursor.execute("""
                    UPDATE ventas 
                    SET total = %s 
                    WHERE id_venta = %s
                """, (total_venta, id_venta))

                conn.commit()

    # Datos para la vista
    cursor.execute("SELECT id_producto, nombre FROM productos")
    productos = cursor.fetchall()

    cursor.execute("""
        SELECT l.*, p.nombre
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY l.fecha_ingreso ASC
    """)
    lotes = cursor.fetchall()

    conn.close()

    return render_template(
        'ventas.html',
        productos=productos,
        lotes=lotes,
        error=error,
        now=datetime.now().date(),
        timedelta=timedelta
    )

#  INVENTARIO
@app.route('/inventario')
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

# ALERTAS
@app.route('/alertas')
@login_requerido
def alertas():
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

    return render_template('alertas.html', datos=datos)


@app.route('/devoluciones')
@login_requerido
def devoluciones():
    return render_template('devoluciones.html')

# PROVEEDORES
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

    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()

    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)

#  REGISTRO
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    conn = get_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        cursor.execute("""
            INSERT INTO usuarios (username, password, id_rol)
            VALUES (%s, %s, %s)
        """, (
            request.form['username'],
            generate_password_hash(request.form['password']),
            request.form['rol']
        ))
        conn.commit()
        return redirect('/login')

    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()

    return render_template('registro.html', roles=roles)

#  LOGIN
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

        if user and check_password_hash(user['password'], request.form['password']):
            session['user'] = user['username']
            session['rol'] = user['rol']
            return redirect('/')
        else:
            return "Credenciales incorrectas"

    return render_template('login.html')

#  LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

#  EJECUCIÓN
if __name__ == '__main__':
    app.run(debug=True)