from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
from database import connect_db, get_next_id
from decimal import Decimal
from functools import wraps
from flask import session

app = Flask(__name__)
app.secret_key = '29122020'

def check_credentials(username, password):
    return username == "allanh" and password == "ajhs2705"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if check_credentials(username, password):
            session['username'] = username
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('index'))
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

# Ruta principal
@app.route('/')
@login_required
def index():
    db = connect_db()
    cursor = db.cursor()
    
    # Obtener notificaciones de renovaciones pendientes y cuentas expiradas
    today = datetime.now().date()
    
    # Notificaciones de clientes que deben renovar
    cursor.execute("SELECT v.id, c.nombre FROM ventas v JOIN clientes c ON v.cliente = c.id WHERE v.fechaexp <= %s AND (v.estado IS NULL OR v.estado = '')", (today,))
    clientes_a_renovar = cursor.fetchall()
    
    # Notificaciones de cuentas expiradas
    cursor.execute("SELECT id, correoc FROM cuentas WHERE fechav <= %s", (today,))
    cuentas_expiradas = cursor.fetchall()
    
    # Crear lista de notificaciones
    notificaciones = []
    for cliente in clientes_a_renovar:
        notificaciones.append(f"Cliente {cliente[1]} (ID: {cliente[0]}) debe renovar")
    for cuenta in cuentas_expiradas:
        notificaciones.append(f"Renovación de cuenta ID: {cuenta[0]} pendiente")
    
    db.close()
    return render_template('index.html', notificaciones=notificaciones)


# Ruta para ver cuentas
@app.route('/ver_cuentas', methods=['GET', 'POST'])
@login_required
def ver_cuentas():
    db = connect_db()
    cursor = db.cursor()
    if request.method == 'POST':
        search_query = request.form['search']
        cursor.execute("SELECT * FROM cuentas WHERE correoc LIKE %s OR tipocuenta LIKE %s", 
                       ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("SELECT * FROM cuentas")
    cuentas = cursor.fetchall()
    db.close()
    return render_template('ver_cuentas.html', cuentas=cuentas)

# Ruta para ver clientes
@app.route('/ver_clientes', methods=['GET', 'POST'])
@login_required
def ver_clientes():
    db = connect_db()
    cursor = db.cursor()
    if request.method == 'POST':
        search_query = request.form['search']
        cursor.execute("SELECT * FROM clientes WHERE nombre LIKE %s OR numero LIKE %s", 
                       ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("SELECT * FROM clientes")
    clientes = cursor.fetchall()
    db.close()
    return render_template('ver_clientes.html', clientes=clientes)

# Ruta para ver ventas
@app.route('/ver_ventas', methods=['GET', 'POST'])
@login_required
def ver_ventas():
    db = connect_db()
    cursor = db.cursor()
    if request.method == 'POST':
        search_query = request.form['search']
        cursor.execute("SELECT * FROM ventas WHERE cliente LIKE %s OR tipocuenta LIKE %s", 
                       ('%' + search_query + '%', '%' + search_query + '%'))
    else:
        cursor.execute("SELECT * FROM ventas")
    ventas = cursor.fetchall()
    db.close()
    return render_template('ver_ventas.html', ventas=ventas)


# Ruta para agregar cuenta
@app.route('/agregar_cuenta', methods=['GET', 'POST'])
@login_required
def agregar_cuenta():
    if request.method == 'POST':
        tipo_cuenta = request.form['tipo_cuenta']
        correoc = request.form['correoc']
        password = request.form['password']
        fechac = request.form['fechac']
        fechav = request.form['fechav']
        perfiles = request.form['perfiles']
        inversion = request.form['inversion']
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO cuentas (tipocuenta, correoc, password, fechac, fechav, perfiles, inversion) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                       (tipo_cuenta, correoc, password, fechac, fechav, perfiles, inversion))
        db.commit()
        db.close()
        flash('Cuenta agregada exitosamente', 'success')
        return redirect(url_for('agregar_cuenta'))

    return render_template('agregar_cuenta.html', next_id=get_next_id('cuentas'))

# Ruta para agregar cliente
@app.route('/agregar_cliente', methods=['GET', 'POST'])
@login_required
def agregar_cliente():
    if request.method == 'POST':
        nombre = request.form['nombre']
        numero = request.form['numero']
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO clientes (nombre, numero) VALUES (%s, %s)", (nombre, numero))
        db.commit()
        db.close()
        flash('Cliente agregado exitosamente', 'success')
        return redirect(url_for('agregar_cliente'))

    return render_template('agregar_cliente.html', next_id=get_next_id('clientes'))

# Obtener la inversión según el correo de la cuenta seleccionada
def get_inversion(correo_cuenta):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT inversion FROM cuentas WHERE correoc = %s", (correo_cuenta,))
    inversion = cursor.fetchone()[0] or Decimal('0.0')  # Asegurarse de obtener un Decimal
    db.close()
    return float(inversion)  # Convertir a float antes de retornar 

# Función para restar un perfil de perfiles en cuentas
def restar_perfil(correo_cuenta):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("UPDATE cuentas SET perfiles = perfiles - 1 WHERE correoc = %s", (correo_cuenta,))
    db.commit()
    db.close()

# Ruta para agregar venta
@app.route('/agregar_venta', methods=['GET', 'POST'])
@login_required
def agregar_venta():
    if request.method == 'POST':
        cliente = request.form['cliente']
        tipo_cuenta = request.form['tipo_cuenta']
        cuenta_disponible = request.form['cuenta_disponible']
        fechaini = datetime.strptime(request.form['fechaini'], '%Y-%m-%d')
        dias = int(request.form['dias'])
        fechaexp = fechaini + timedelta(days=dias)
        monto = float(request.form['monto'])
        inversion = get_inversion(cuenta_disponible)
        ganancia = monto - inversion  # Calcular ganancia
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO ventas (cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                       (cliente, tipo_cuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion))
        db.commit()
        # Restar un perfil de perfiles en cuentas
        restar_perfil(cuenta_disponible)
        db.close()
        
        return redirect(url_for('index'))

    # Obtener datos necesarios para el formulario
    clientes = obtener_clientes()
    tipos_cuenta = ["netflix", "disneyplus", "max", "spotify", "youtube", "primevideo"]
    cuentas_disponibles = obtener_cuentas_disponibles()

    next_id = get_next_id('ventas')

    return render_template('agregar_venta.html', next_id=next_id, clientes=clientes, tipos_cuenta=tipos_cuenta, cuentas_disponibles=cuentas_disponibles)

@app.route('/get_cuentas_disponibles/<tipo_cuenta>')
def get_cuentas_disponibles(tipo_cuenta):
    cuentas_disponibles = obtener_cuentas_disponibles_por_tipo(tipo_cuenta)
    return jsonify(cuentas_disponibles)

# Función para obtener clientes desde la base de datos
def obtener_clientes():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, nombre FROM clientes")
    clientes = cursor.fetchall()
    db.close()
    return clientes

# Función para obtener cuentas disponibles desde la base de datos
def obtener_cuentas_disponibles():
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT correoc FROM cuentas WHERE perfiles BETWEEN 1 AND 8")
    cuentas_disponibles = cursor.fetchall()
    db.close()
    return cuentas_disponibles

def obtener_cuentas_disponibles_por_tipo(tipo_cuenta):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT correoc FROM cuentas WHERE tipocuenta = %s AND perfiles BETWEEN 1 AND 8", (tipo_cuenta,))
    cuentas_disponibles = cursor.fetchall()
    db.close()
    return [cuenta[0] for cuenta in cuentas_disponibles]

@app.route('/get_inversion')
def get_inversion_route():
    correo = request.args.get('correo')
    inversion = get_inversion(correo)
    return {'inversion': inversion}


# Ruta para ver ingresos
@app.route('/ver_ingresos')
@login_required
def ver_ingresos():
    db = connect_db()
    cursor = db.cursor()
    
    # Ingresos mensuales
    current_month = datetime.now().month
    cursor.execute("SELECT SUM(ganancia) FROM ventas WHERE MONTH(fechaini) = %s", (current_month,))
    ingresos_mensuales = cursor.fetchone()[0] or 0
    
    # Ingresos anuales
    current_year = datetime.now().year
    cursor.execute("SELECT SUM(ganancia) FROM ventas WHERE YEAR(fechaini) = %s", (current_year,))
    ingresos_anuales = cursor.fetchone()[0] or 0

    # Ingresos por referidos mensuales y anuales
    cursor.execute("SELECT referidos, SUM(ganancia) as ganancia_mensual FROM ventas WHERE MONTH(fechaini) = %s GROUP BY referidos", (current_month,))
    referidos_mensuales = cursor.fetchall()

    cursor.execute("SELECT referidos, SUM(ganancia) as ganancia_anual FROM ventas WHERE YEAR(fechaini) = %s GROUP BY referidos", (current_year,))
    referidos_anuales = cursor.fetchall()

    db.close()

    return render_template('ver_ingresos.html', ingresos_mensuales=ingresos_mensuales, ingresos_anuales=ingresos_anuales,
                           referidos_mensuales=referidos_mensuales, referidos_anuales=referidos_anuales)
    

# Ruta para ver clientes que deben renovar
@app.route('/ver_renovaciones')
@login_required
def ver_renovaciones():
    db = connect_db()
    cursor = db.cursor()
    today = datetime.now().date()
    cursor.execute("SELECT v.id, v.cliente, v.tipocuenta, v.cuenta_disponible, v.fechaini, v.fechaexp, c.nombre, c.numero "
                   "FROM ventas v JOIN clientes c ON v.cliente = c.id WHERE v.fechaexp <= %s AND (v.estado IS NULL OR v.estado = '')", (today,))
    renovaciones = cursor.fetchall()
    db.close()
    return render_template('ver_renovaciones.html', renovaciones=renovaciones)

# Ruta para renovar una venta
@app.route('/renovar_venta/<int:venta_id>', methods=['POST'])
@login_required
def renovar_venta(venta_id):
    dias = int(request.form['dias'])
    fechaini = datetime.now().date()
    fechaexp = fechaini + timedelta(days=dias)
    
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT cliente, tipocuenta, cuenta_disponible, monto, inversion FROM ventas WHERE id = %s", (venta_id,))
    venta = cursor.fetchone()
    
    cursor.execute("INSERT INTO ventas (cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                   (venta[0], venta[1], venta[2], fechaini, dias, fechaexp, venta[3], venta[4]))
    cursor.execute("UPDATE ventas SET estado = 'renovado' WHERE id = %s", (venta_id,))
    db.commit()
    db.close()
    
    flash('Venta renovada exitosamente', 'success')
    return redirect(url_for('ver_renovaciones'))

# Ruta para marcar como no renovado
@app.route('/no_renovo/<int:venta_id>', methods=['POST'])
def no_renovo(venta_id):
    db = connect_db()
    cursor = db.cursor()
    
    cursor.execute("SELECT cuenta_disponible FROM ventas WHERE id = %s", (venta_id,))
    cuenta_disponible = cursor.fetchone()[0]
    
    cursor.execute("UPDATE cuentas SET perfiles = perfiles + 1 WHERE correoc = %s", (cuenta_disponible,))
    cursor.execute("UPDATE ventas SET estado = 'inactivo' WHERE id = %s", (venta_id,))
    db.commit()
    db.close()
    
    flash('Perfil liberado exitosamente', 'success')
    return redirect(url_for('ver_renovaciones'))

# Ruta para editar cuenta
@app.route('/editar_cuenta/<int:cuenta_id>', methods=['GET', 'POST'])
def editar_cuenta(cuenta_id):
    db = connect_db()
    cursor = db.cursor()
    if request.method == 'POST':
        tipo_cuenta = request.form['tipo_cuenta']
        correoc = request.form['correoc']
        password = request.form['password']
        fechac = request.form['fechac']
        fechav = request.form['fechav']
        perfiles = request.form['perfiles']
        inversion = request.form['inversion']

        cursor.execute("UPDATE cuentas SET tipocuenta=%s, correoc=%s, password=%s, fechac=%s, fechav=%s, perfiles=%s, inversion=%s WHERE id=%s", 
                       (tipo_cuenta, correoc, password, fechac, fechav, perfiles, inversion, cuenta_id))
        db.commit()
        db.close()
        flash('Cuenta actualizada exitosamente', 'success')
        return redirect(url_for('ver_cuentas'))

    cursor.execute("SELECT id, tipocuenta, correoc, password, fechac, fechav, perfiles, inversion FROM cuentas WHERE id=%s", (cuenta_id,))
    cuenta = cursor.fetchone()
    db.close()
    return render_template('editar_cuenta.html', cuenta=cuenta)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=19132)
