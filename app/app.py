from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
from database import connect_db, get_next_id
from decimal import Decimal
from functools import wraps
from flask import session
import random
import string

app = Flask(__name__)
app.secret_key = '29122020'

PORCENTAJE_REFERIDO = 0.5

def check_credentials(username, password):
    db = connect_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, rol FROM usuarios WHERE nombre_usuario = %s AND contraseña = %s", (username, password))
    user = cursor.fetchone()
    db.close()
    if user:
        session['user_id'] = user[0]
        session['username'] = username
        session['rol'] = user[1]
        return True
    return False


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session or session.get('rol') != 'admin':
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
            if session.get('rol') == 'admin':
                return redirect(url_for('index'))  # Redirige a un dashboard de administrador
            else:
                return redirect(url_for('streamplus'))  # Redirige a la página principal
        else:
            flash('Nombre de usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

#Ruta de Registro
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nombre_usuario = request.form['nombre_usuario']
        contraseña = request.form['contraseña']
        numero_telefono = request.form['numero_telefono']
        correo_electronico = request.form['correo_electronico']
        codigo_referido = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        rol = 'usuario'

        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO usuarios (nombre_usuario, contraseña, numero_telefono, correo_electronico, codigo_referido, rol) VALUES (%s, %s, %s, %s, %s, %s)",
                       (nombre_usuario, contraseña, numero_telefono, correo_electronico, codigo_referido, rol))
        db.commit()
        db.close()
        flash('Usuario registrado exitosamente', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

#Ruta de Usuarios
@app.route('/streamplus')
@login_required
def streamplus():
    db = connect_db()
    cursor = db.cursor()
    
    # Obtener el saldo actual del usuario
    user_id = session['user_id']
    cursor.execute("SELECT saldo FROM usuarios WHERE id = %s", (user_id,))
    saldo_actual = cursor.fetchone()[0]
    
    db.close()
    return render_template('streamplus.html', saldo_actual=saldo_actual)



# Ruta principal Admin
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
        gananciaref = "0.00"
        referido = request.form['referido']
       
        if dias == '60':
                inversion *= 2
                ganancia = monto - inversion
        elif dias == '90':
                inversion *= 3
                ganancia = monto - inversion

        if referido != '' and referido == 'STREAMPLUS':
            ganancia = monto - inversion
        else :
            gananciaref = float(monto - inversion) * PORCENTAJE_REFERIDO
        
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO ventas (cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (cliente, tipo_cuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref))
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
    cursor.execute("SELECT referido, SUM(gananciaref) as ganancia_mensual FROM ventas WHERE referido IS NOT NULL AND referido != '' AND MONTH(fechaini) = %s GROUP BY referido", (current_month,))
    referidos_mensuales = cursor.fetchall()

    cursor.execute("SELECT referido, SUM(gananciaref) as ganancia_anual FROM ventas WHERE referido IS NOT NULL AND referido != '' AND YEAR(fechaini) = %s GROUP BY referido", (current_year,))
    referidos_anuales = cursor.fetchall()

    # Ventas mensuales y anuales de STREAMPLUS
    cursor.execute("SELECT SUM(ganancia) FROM ventas WHERE referido = 'STREAMPLUS' AND MONTH(fechaini) = %s", (current_month,))
    ventas_streamplus_mensual = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(ganancia) FROM ventas WHERE referido = 'STREAMPLUS' AND YEAR(fechaini) = %s", (current_year,))
    ventas_streamplus_anual = cursor.fetchone()[0] or 0

    db.close()

    return render_template('ver_ingresos.html', 
                           ingresos_mensuales=ingresos_mensuales, 
                           ingresos_anuales=ingresos_anuales,
                           referidos_mensuales=referidos_mensuales, 
                           referidos_anuales=referidos_anuales,
                           ventas_streamplus_mensual=ventas_streamplus_mensual,
                           ventas_streamplus_anual=ventas_streamplus_anual)
    

#Ruta Agregar Pedido
@app.route('/agregar_pedido', methods=['GET', 'POST'])
@login_required
def agregar_pedido():
    if request.method == 'POST':
        cliente = request.form['cliente']
        tipo_cuenta = request.form['tipo_cuenta']
        cuenta_disponible = request.form['cuenta_disponible']
        fechaini = datetime.strptime(request.form['fechaini'], '%Y-%m-%d')
        dias = int(request.form['dias'])
        fechaexp = fechaini + timedelta(days=dias)
        monto = float(request.form['monto'])
        inversion = get_inversion(cuenta_disponible)
        user_id = session['user_id']
        # obtener referido
        db = connect_db()
        cursor = db.cursor()
        cursor.execute("SELECT codigo_referido FROM usuarios WHERE id = %s", (user_id,))
        referido = cursor.fetchone()[0]

        gananciaref = "0.00"
       
        if dias == '60':
                inversion *= 2
                ganancia = monto - inversion
        elif dias == '90':
                inversion *= 3
                ganancia = monto - inversion
        gananciaref = (monto - inversion) * PORCENTAJE_REFERIDO

        db = connect_db()
        cursor = db.cursor()
        cursor.execute("INSERT INTO pedidos (cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (cliente, tipo_cuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref))
        db.commit()
        db.close()

        flash('Pedido agregado exitosamente', 'success')
        return redirect(url_for('streamplus'))
    
    # Obtener datos necesarios para el formulario
    clientes = obtener_clientes()
    tipos_cuenta = ["netflix", "disneyplus", "max", "spotify", "youtube", "primevideo"]
    cuentas_disponibles = obtener_cuentas_disponibles()

    next_id = get_next_id('ventas')

    return render_template('agregar_pedido.html', next_id=next_id, clientes=clientes, tipos_cuenta=tipos_cuenta, cuentas_disponibles=cuentas_disponibles)


#Ruta Ver Ventas Usuario
@app.route('/ver_ventas_usuario')
@login_required
def ver_ventas_usuario():
    db = connect_db()
    cursor = db.cursor()
    user_referido = session['username']
    cursor.execute("SELECT * FROM ventas WHERE referido = %s", (user_referido,))
    ventas = cursor.fetchall()
    db.close()
    return render_template('ver_ventas_usuario.html', ventas=ventas)


#Ruta ver ingresos del usuario
@app.route('/ver_ingresos_usuario')
@login_required
def ver_ingresos_usuario():
    db = connect_db()
    cursor = db.cursor()
    user_referido = session['username']
    current_month = datetime.now().month
    current_year = datetime.now().year

    cursor.execute("SELECT SUM(gananciaref) FROM ventas WHERE referido = %s AND MONTH(fechaini) = %s", (user_referido, current_month))
    ingresos_mensuales = cursor.fetchone()[0] or 0

    cursor.execute("SELECT SUM(gananciaref) FROM ventas WHERE referido = %s AND YEAR(fechaini) = %s", (user_referido, current_year))
    ingresos_anuales = cursor.fetchone()[0] or 0

    db.close()
    return render_template('ver_ingresos_usuario.html', ingresos_mensuales=ingresos_mensuales, ingresos_anuales=ingresos_anuales)


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

# Ruta para ver y confirmar pedidos
@app.route('/ver_pedidos', methods=['GET', 'POST'])
@login_required
def ver_pedidos():
    db = connect_db()
    cursor = db.cursor()

    if request.method == 'POST':
        pedido_id = request.form['pedido_id']
        
        # Obtener detalles del pedido
        cursor.execute("SELECT cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref FROM pedidos WHERE id = %s", (pedido_id,))
        pedido = cursor.fetchone()

        # Mover a tabla ventas
        cursor.execute(
            "INSERT INTO ventas (cliente, tipocuenta, cuenta_disponible, fechaini, dias, fechaexp, monto, inversion, referido, gananciaref) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (pedido[0], pedido[1], pedido[2], pedido[3], pedido[4], pedido[5], pedido[6], pedido[7], pedido[8], pedido[9])
        )

        # Borrar de la tabla pedidos
        cursor.execute("DELETE FROM pedidos WHERE id = %s", (pedido_id,))
        db.commit()
        db.close()

        flash('Pedido confirmado y movido a ventas exitosamente', 'success')
        return redirect(url_for('ver_pedidos'))

    cursor.execute("SELECT * FROM pedidos")
    pedidos = cursor.fetchall()
    db.close()
    return render_template('ver_pedidos.html', pedidos=pedidos)


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


@app.route('/retirar', methods=['GET'])
@login_required
def retirar():
    db = connect_db()
    cursor = db.cursor()
    user_id = session['user_id']

    # Recuperar el historial de retiros
    cursor.execute("SELECT id, cantidad, metpago, estado FROM retiros WHERE user_id = %s", (user_id,))
    retiros = cursor.fetchall()

    db.close()
    return render_template('retirar.html', retiros=retiros)



#Ruta para Retirar
@app.route('/retirar_dinero', methods=['POST'])
@login_required
def retirar_dinero():
    user_id = session['user_id']
    cantidad = float(request.form['cantidad'])
    metpago = request.form['metpago']
    infopago = ''

    if metpago == 'transferencia':
        banco = request.form['banco']
        cuenta = request.form['cuenta']
        infopago = f'Banco: {banco}, Cuenta: {cuenta}'
    elif metpago == 'tigo_money':
        telefono = request.form['telefono']
        infopago = f'Teléfono: {telefono}'
    elif metpago == 'paypal':
        paypal_email = request.form['paypal_email']
        infopago = f'Correo PayPal: {paypal_email}'

    db = connect_db()
    cursor = db.cursor()
    
    # Obtener el saldo actual del usuario
    cursor.execute("SELECT saldo FROM usuarios WHERE id = %s", (user_id,))
    saldo_actual = cursor.fetchone()[0]

    if cantidad > saldo_actual:
        flash('Saldo insuficiente para retirar esa cantidad.', 'danger')
        db.close()
        return redirect(url_for('retirar'))

    # Calcular el nuevo saldo del usuario
    nuevo_saldo = saldo_actual - cantidad
    
    # Insertar en la tabla de retiros
    cursor.execute("INSERT INTO retiros (usuario, cantidad, metpago, infopago, saldo_actual, estado) VALUES (%s, %s, %s, %s, %s, 'pendiente')",
                   (user_id, cantidad, metpago, infopago, nuevo_saldo))
    
    # Actualizar el saldo del usuario
    cursor.execute("UPDATE usuarios SET saldo = %s WHERE id = %s", (nuevo_saldo, user_id))
    
    db.commit()
    db.close()
    
    flash('Solicitud de retiro realizada exitosamente.', 'success')
    return redirect(url_for('retirar'))


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=19132)
