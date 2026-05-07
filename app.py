from flask import Flask, render_template, request, redirect, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

load_dotenv()  # ← primero que todo

from models.db_connection import get_connection
from models.lote import get_lotes_por_vencer, get_total_lotes_activos
from models.producto import get_all_productos
from models.venta import get_ventas_hoy
from auth import login_requerido, rol_requerido

# Blueprints
from controllers.alertas_controller import alertas_bp, get_alertas_data
from controllers.inventario_controller import inventario_bp
from controllers.ventas_controller import ventas_bp

app = Flask(__name__, template_folder="views")
app.secret_key = os.getenv("SECRET_KEY", "secretkey")
 
# ── Registrar Blueprints
app.register_blueprint(alertas_bp)
app.register_blueprint(inventario_bp)
app.register_blueprint(ventas_bp)
 
 
# ── DASHBOARD 
@app.route('/')
@login_requerido
def home():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT COUNT(*) AS total FROM productos")
    total_productos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM lotes WHERE cantidad_disponible > 0")
    total_lotes = cursor.fetchone()['total']

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM lotes
        WHERE DATEDIFF(fecha_vencimiento, CURDATE()) BETWEEN 0 AND 7
        AND cantidad_disponible > 0
    """)
    por_vencer = cursor.fetchone()['total']

    cursor.execute("""
        SELECT IFNULL(SUM(total), 0) AS total
        FROM ventas
        WHERE DATE(fecha_venta) = CURDATE()
    """)
    ventas_hoy = cursor.fetchone()['total']

    cursor.execute("""
        SELECT p.nombre, l.numero_lote, l.fecha_vencimiento,
               l.cantidad_disponible,
               DATEDIFF(l.fecha_vencimiento, CURDATE()) AS dias
        FROM lotes l
        JOIN productos p ON p.id_producto = l.id_producto
        WHERE l.cantidad_disponible > 0
        ORDER BY l.fecha_vencimiento ASC
        LIMIT 10
    """)
    alertas = cursor.fetchall()

    conn.close()  # ← una sola conexión para todo

    return render_template(
        'dashboard.html',
        total_productos=total_productos,
        total_lotes=total_lotes,
        por_vencer=por_vencer,
        ventas_hoy=ventas_hoy,
        alertas=alertas
    )
 
 
# ── PRODUCTOS
@app.route('/productos')
@login_requerido
def productos():
    return render_template('productos.html', productos=get_all_productos())
 
 
# ── DEVOLUCIONES 
@app.route('/devoluciones')
@login_requerido
def devoluciones():
    return render_template('devoluciones.html')
 
 
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
 
    cursor.execute("SELECT * FROM proveedores")
    proveedores = cursor.fetchall()
    conn.close()
    return render_template('proveedores.html', proveedores=proveedores)
 
 
# ── REGISTRO
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
 
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
        conn.close()
        return redirect('/login')
 
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()
    conn.close()
    return render_template('registro.html', roles=roles)
 
 
# ── LOGIN 
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
            session['user'] = user['username']
            session['rol']  = user['rol']
            return redirect('/')
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