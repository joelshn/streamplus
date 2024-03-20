from flask import Flask, render_template, request, redirect, url_for
import mysql.connector
from datetime import datetime 
import json

app = Flask(__name__)

# Configura la conexión a la base de datos
db = mysql.connector.connect(
    host="db4free.net",
    user="allanh",
    password="hernandez2210",
    database="registro504"
)
cursor = db.cursor()

@app.route('/registro_pedidos')
def mostrar_formulario_registro():
    return render_template('registro.html')

@app.route('/agregar_pedido', methods=['POST'])
def agregar_pedido():
    nombre = request.form['nombre']
    numero = request.form['numero']
    cuenta = request.form['cuenta']
    correo = request.form['correo']
    monto = request.form['monto']
    fecha = request.form['fecha']
    referido = request.form['referido']

    try:
        # Insertar el pedido en la tabla temporal
        cursor.execute("""
            INSERT INTO pedidos_temporales 
            (nombre, numero, cuenta, correo_cuenta, monto, fecha, estado_pago, referido)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (nombre, numero, cuenta, correo, monto, fecha, 'Pendiente', referido))
        db.commit()
        return "Pedido registrado exitosamente"
    except Exception as e:
        return f"Error al registrar pedido: {str(e)}"


@app.route('/confirmar_pedidos')
def mostrar_pedidos_por_confirmar():
    try:
        cursor.execute("SELECT * FROM pedidos_temporales")
        pedidos = cursor.fetchall()
        return render_template('confirmarp.html', pedidos=pedidos)
    except Exception as e:
        return f"Error al recuperar los pedidos: {str(e)}"


@app.route('/confirmar_pedido/<int:pedido_id>', methods=['POST'])
def confirmar_pedido(pedido_id):
    try:
        # Actualiza el estado del pedido a 'Confirmado' en la tabla temporal
        cursor.execute("UPDATE pedidos_temporales SET estado_pago='Pagado' WHERE id=%s", (pedido_id,))
        db.commit()
        # Mueve el pedido de la tabla temporal a la tabla principal de pedidos
        cursor.execute("""
            INSERT INTO ventas
            (nombre, numero, cuenta, correo_cuenta, monto, fecha, estado_pago, referido)
            SELECT nombre, numero, cuenta, correo_cuenta, monto, fecha, estado_pago, referido
            FROM pedidos_temporales
            WHERE id = %s
        """, (pedido_id,))
        cursor.execute("DELETE FROM pedidos_temporales WHERE id = %s", (pedido_id,))
        db.commit()
        return "Pedido confirmado exitosamente"
    except Exception as e:
        return f"Error al confirmar pedido: {str(e)}"


@app.route('/agregar', methods=['POST'])
def agregar_venta():
    # Manejar la inserción de una nueva venta aquí
    nombre_nuevo = request.form['nombre_nuevo']
    numero_nuevo = request.form['numero_nuevo']
    cuenta_nuevo = request.form['cuenta_nuevo']
    correo_nuevo = request.form['correo_nuevo']
    monto_nuevo = request.form['monto_nuevo']
    fecha_nuevo = request.form['fecha_nuevo']
    estado_pago_nuevo = request.form['estado_pago_nuevo']
    referido_nuevo = request.form['referido_nuevo']

    cursor.execute("INSERT INTO ventas (nombre, numero, cuenta, correo_cuenta, monto, fecha, estado_pago, referido) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                   (nombre_nuevo, numero_nuevo, cuenta_nuevo, correo_nuevo, monto_nuevo, fecha_nuevo, estado_pago_nuevo, referido_nuevo))
    db.commit()
    # Obtener el ID del cliente recién registrado
    nuevo_cliente_id = cursor.lastrowid
  
    return redirect(url_for('listar_ventas', cliente_id=nuevo_cliente_id))


@app.route('/')
def listar_ventas():
    cursor.execute("SELECT * FROM ventas")
    ventas = cursor.fetchall()
    
    # Inicializar variables para el cálculo de ingresos
    fecha_actual = datetime.now()
    mes = fecha_actual.strftime('%Y-%m')
    print(mes)
    total_ingresos = 0
    pagos_mes = 0
    pagos_pendientes = 0
    disney_monto = 0
    netflix_monto = 0
    hbomax_monto = 0
    spotify_monto = 0
    primevideo_monto = 0
    spotifyf_monto = 0
    youtube_monto = 0

    disney_monto_mes = 0
    netflix_monto_mes = 0
    hbomax_monto_mes = 0
    spotify_monto_mes = 0
    primevideo_monto_mes = 0
    spotifyf_monto_mes = 0
    youtube_monto_mes = 0

    # Convierte los datos en una estructura adecuada para JSON
    backup_data = []

    for venta in ventas:
        venta_dict = {
            'id': venta[0],
            'nombre': venta[1],
            'numero': venta[2],
            'cuenta': venta[3],
            'correo_cuenta': venta[4],
            'monto': float(venta[5]),
            'fecha': venta[6],
            'estado_pago': venta[7],
            'referido': venta[8]
        }
        backup_data.append(venta_dict)

    # Guarda los datos en un archivo JSON
    with open('datos.json', 'w') as json_file:
        json.dump(backup_data, json_file)
    # Calcular el "Total de ingresos" basado en los porcentajes
    for venta in ventas:
        monto = float(venta[5])  # Convierte el monto a tipo float
        cuenta = venta[3]  # Supongamos que el nombre de la columna es "cuenta"
        fecha = venta[6]
        estado_pago = venta[7]
        referido = venta[8]

        if estado_pago is not None and estado_pago.upper() == 'PENDIENTE':
            pagos_pendientes += 1

        if cuenta == 'disney':
           disney_monto += monto
        elif cuenta == 'netflix':
             netflix_monto += monto
        elif cuenta == 'hbomax':
             hbomax_monto += monto
        elif cuenta == 'spotify':
             spotify_monto += monto
        elif cuenta == 'primevideo':
             primevideo_monto += monto
        elif cuenta == 'spotifyf':
             spotifyf_monto += monto
        elif cuenta == 'youtube':
             youtube_monto += monto

        if cuenta == 'disney' and fecha.startswith(mes):
           disney_monto_mes += monto
        elif cuenta == 'netflix' and fecha.startswith(mes):
             netflix_monto_mes += monto
        elif cuenta == 'hbomax' and fecha.startswith(mes):
             hbomax_monto_mes += monto
        elif cuenta == 'spotify' and fecha.startswith(mes):
             spotify_monto_mes += monto
        elif cuenta == 'primevideo' and fecha.startswith(mes):
             primevideo_monto_mes+= monto
        elif cuenta == 'spotifyf' and fecha.startswith(mes):
             spotifyf_monto_mes += monto
        elif cuenta == 'youtube' and fecha.startswith(mes):
             youtube_monto_mes += monto
          
    pagos_mes = round((disney_monto_mes * 0.52381 + netflix_monto_mes * 0.45 + hbomax_monto_mes * 0.5 + spotify_monto_mes * 0.287 + primevideo_monto_mes * 0.5 + spotifyf_monto_mes + youtube_monto_mes*0.45), 2)

    total_ingresos = round((disney_monto * 0.52381 + netflix_monto * 0.45 + hbomax_monto * 0.5 + spotify_monto * 0.287 + primevideo_monto * 0.5 + spotifyf_monto + youtube_monto*0.45), 2)

    return render_template('ventas.html', ventas=ventas, total_ingresos=total_ingresos, total_pendientes=pagos_pendientes, total_mes=pagos_mes)

@app.route('/editar_venta', methods=['POST'])
def editar_venta():
    # Manejar la edición de una venta aquí
    id = request.form['id']
    nombre = request.form['nombre']
    numero = request.form['numero']
    cuenta = request.form['cuenta']
    correo = request.form['correo']
    monto = request.form['monto']
    fecha = request.form['fecha']
    estado_pago = request.form['estado_pago']
    referido = request.form['referido']

    cursor.execute("UPDATE ventas SET nombre=%s, numero=%s, cuenta=%s, correo_cuenta=%s, monto=%s, fecha=%s, estado_pago=%s, referido=%s WHERE id=%s",
                   (nombre, numero, cuenta, correo, monto, fecha, estado_pago, id, referido))
    db.commit()

    return "Actualización exitosa"  # Puedes personalizar la respuesta si es necesario

@app.route('/error')
def error_page():
    return render_template('error.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
