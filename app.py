from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, request, jsonify, current_app
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import bcrypt
import os
import base64
from functools import wraps
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
import datetime

#Cargamos la API key de SendGrid desde .env
load_dotenv()
SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY')

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

#Configuración Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

empleados = []

#Definimos roles y permisos
roles_con_permiso = {
    'empleado': ['ver_perfil'],
    'gestor_rrhh': ['ver_perfil', 'gestionar_empleados'],
    'administrador': ['ver_perfil', 'gestionar_empleados', 'eliminar_empleado']
}

#Clase de modelo de usuario para Flask-Login
class User(UserMixin):
    def __init__(self, id):
        self.id = id

#Autenticación de empleados
def autenticar_correo(correo, contrasena):
    for empleado in empleados:
        if empleado['correo'] == correo and bcrypt.checkpw(contrasena.encode(), empleado['contrasena'].encode()):
            user = User(empleado['id'])
            login_user(user)
            return empleado
    return None

#Verificar permisos de empleado
def verificar_permiso(empleado, permiso):
    return permiso in roles_con_permiso.get(empleado['rol'], [])

#Decorador para verificar permisos de acceso
def verificar_permisos(permiso):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not verificar_permiso(current_user, permiso):
                return jsonify({'error': 'No tienes permiso para acceder a esta información'}), 403
            return func(*args, **kwargs)
        return wrapper
    return decorator

#Decorador para cargar el usuario actual
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

#Rutas para la autenticación y gestión de empleados
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'correo' not in data or 'contrasena' not in data:
        return jsonify({'error': 'Credenciales incompletas'}), 400

    correo = data['correo']
    contrasena = data['contrasena']
    empleado = autenticar_correo(correo, contrasena)

    if empleado:
        return jsonify({'mensaje': 'Inicio de sesión exitoso', 'empleado': empleado}), 200
    else:
        return jsonify({'error': 'Credenciales incorrectas'}), 401

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({'mensaje': 'Sesión cerrada'}), 200

@app.route('/empleados', methods=['GET', 'POST'])
@login_required
@verificar_permisos('gestionar_empleados')
def gestion_empleados():
    if request.method == 'GET':
        return jsonify(empleados)
    elif request.method == 'POST':
        data = request.get_json()
        
        #Verificar si todos los campos tienen información
        required_fields = ['correo', 'nombre', 'apellido', 'rol', 'salario_base', 'deducciones', 'bonificaciones', 'contrasena', 'direccion', 'celular', 'superadmin']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': 'Datos incompletos'}), 400
        
        #Generar ID dependiendo del último registro
        if len(empleados) > 0:
            last_id = empleados[-1]['id']
            new_id = last_id + 1
        else:
            new_id = 1
            
        #Celular debe tener solo números y 10 dígitos
        celular = data.get('celular', '')
        if not celular.isdigit() or len(celular) != 10:
            return jsonify({'error': 'El número de celular debe contener solo números y tener una longitud de 10 dígitos'}), 400
        
        #Hashear la contraseña
        hashed_password = bcrypt.hashpw(data['contrasena'].encode(), bcrypt.gensalt()).decode()
        
        empleado = {
            'id': new_id,
            'correo': data['correo'],
            'nombre': data['nombre'],
            'apellido': data['apellido'],
            'rol': data['rol'],
            'salario_base': data['salario_base'],
            'deducciones': data['deducciones'],
            'bonificaciones': data['bonificaciones'],
            'contrasena': hashed_password,
            'direccion': data['direccion'],
            'celular': data['celular'],
            'superadmin': data['superadmin']
        }
        
        empleados.append(empleado)
        return jsonify(empleado), 201

@app.route('/empleados/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@verificar_permisos('gestionar_empleados')
def gestion_empleado(id):
    if request.method == 'GET':
        empleado = next((empleado for empleado in empleados if empleado['id'] == id), None)
        if empleado:
            return jsonify(empleado)
        else:
            return jsonify({'mensaje': 'Empleado no encontrado'}), 404
    elif request.method == 'PUT':
        empleado = next((empleado for empleado in empleados if empleado['id'] == id), None)
        if empleado:
            data = request.get_json()

            #Verificar si el usuario actual tiene permiso para modificar el salario y el cargo
            if current_user['rol'] != 'gestor_rrhh' and current_user.get('superadmin') != 'si':
                return jsonify({'error': 'No tienes permiso para modificar el salario y el cargo'}), 403

            #Actualizar los campos permitidos del empleado
            if 'salario' in data:
                empleado['salario'] = data['salario']
            if 'rol' in data:
                empleado['rol'] = data['rol']

            return jsonify({'mensaje': 'Empleado actualizado correctamente', 'empleado': empleado}), 200
        else:
            return jsonify({'mensaje': 'Empleado no encontrado'}), 404
    elif request.method == 'DELETE':
        empleado = next((empleado for empleado in empleados if empleado['id'] == id), None)
        if empleado:
            #Verificar permisos para eliminar empleados
            if not verificar_permiso(current_user, 'eliminar_empleado'):
                return jsonify({'error': 'No tienes permiso para eliminar empleados'}), 403
            
            empleados.remove(empleado)
            return jsonify({'mensaje': 'Empleado eliminado'})
        else:
            return jsonify({'mensaje': 'Empleado no encontrado'}), 404

#Rutas para la gestión de recursos humanos (solo accesible para gestores de RRHH)
@app.route('/gestion-humana/empleados', methods=['GET', 'POST'])
@login_required
@verificar_permisos('gestionar_empleados')
def gestion_empleados_rrhh():
    # Verificar si el correo autenticado es un gestor de RRHH
    if 'Authorization' in request.headers:
        auth_data = request.headers['Authorization'].split()
        if len(auth_data) == 2 and auth_data[0] == 'Bearer':
            token = auth_data[1]
            if token == 'TOKEN_GESTOR_RRHH':
                if request.method == 'GET':
                    empleados_gestion_humana = [empleado for empleado in empleados if empleado['rol'] == 'gestor_rrhh']
                    return jsonify(empleados_gestion_humana)
                elif request.method == 'POST':
                    data = request.get_json()
                    if 'correo' not in data or 'contrasena' not in data or 'rol' not in data:
                        return jsonify({'error': 'Datos incompletos'}), 400
                        
                    #Hashear la contraseña
                    hashed_password = bcrypt.hashpw(data['contrasena'].encode(), bcrypt.gensalt()).decode()
                    
                    if len(empleados) > 0:
                        last_id = empleados[-1]['id']
                        new_id = last_id + 1
                    else:
                        new_id = 1
                    
                    empleado = {
                        'id': new_id,
                        'correo': data['correo'],
                        'nombre': data['nombre'],
                        'apellido': data['apellido'],
                        'rol': data['rol'],
                        'salario_base': data['salario_base'],
                        'deducciones': data['deducciones'],
                        'bonificaciones': data['bonificaciones'],
                        'contrasena': hashed_password,
                        'direccion': data['direccion'],
                        'celular': data['celular'],
                        'superadmin': data['superadmin']
                    }
                    empleados.append(empleado)
                    return jsonify(empleado), 201
    return jsonify({'error': 'No tienes permiso para acceder a esta información'}), 403

@app.route('/gestion-humana/empleados/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
@verificar_permisos('gestionar_empleados')
def gestion_empleado_rrhh(id):
    #Verificar si el correo autenticado es un gestor de RRHH
    if 'Authorization' in request.headers:
        auth_data = request.headers['Authorization'].split()
        if len(auth_data) == 2 and auth_data[0] == 'Bearer':
            token = auth_data[1]
            if token == 'TOKEN_GESTOR_RRHH':
                if request.method == 'GET':
                    empleado = next((empleado for empleado in empleados if empleado['id'] == id and empleado['rol'] == 'gestor_rrhh'), None)
                    if empleado:
                        return jsonify(empleado)
                    else:
                        return jsonify({'mensaje': 'Empleado no encontrado'}), 404
                elif request.method == 'PUT':
                    empleado = next((empleado for empleado in empleados if empleado['id'] == id and empleado['rol'] == 'gestor_rrhh'), None)
                    if empleado:
                        data = request.get_json()
                        empleado.update(data)
                        return jsonify(empleado)
                    else:
                        return jsonify({'mensaje': 'Empleado no encontrado'}), 404
                elif request.method == 'DELETE':
                    empleado = next((empleado for empleado in empleados if empleado['id'] == id and empleado['rol'] == 'gestor_rrhh'), None)
                    if empleado:
                        empleados.remove(empleado)
                        return jsonify({'mensaje': 'Empleado eliminado'})
                    else:
                        return jsonify({'mensaje': 'Empleado no encontrado'}), 404
    return jsonify({'error': 'No tienes permiso para acceder a esta información'}), 403

def generar_desprendible_pago(empleado):
    try:
        desprendible_pago = f"Desprendible de pago para {empleado['nombre']} {empleado['apellido']}\n\n"
        desprendible_pago += f"Correo: {empleado['correo']}\n\n"
        desprendible_pago += f"ID Empleado: {empleado['id']}\n"
        desprendible_pago += f"Rol: {empleado['rol']}\n"
        desprendible_pago += f"Salario Base: {empleado['salario_base']}\n\n"
        desprendible_pago += "Deducciones:\n"
        for deduccion in empleado['deducciones']:
            desprendible_pago += f"- {deduccion['concepto']}: {deduccion['monto']}\n"
        desprendible_pago += "\nBonificaciones:\n"
        for bonificacion in empleado['bonificaciones']:
            desprendible_pago += f"- {bonificacion['concepto']}: {bonificacion['monto']}\n"
        total_deducciones = sum(deduccion['monto'] for deduccion in empleado['deducciones'])
        total_bonificaciones = sum(bonificacion['monto'] for bonificacion in empleado['bonificaciones'])
        desprendible_pago += f"\nTotal Deducciones: {total_deducciones}\n"
        desprendible_pago += f"Total Bonificaciones: {total_bonificaciones}\n"
        total_a_pagar = empleado['salario_base'] + total_bonificaciones - total_deducciones
        desprendible_pago += f"\nTotal a Pagar: {total_a_pagar}"
        
        file_name = f"desprendible_{empleado['nombre']}_{empleado['apellido']}.txt"
        file_path = f"desprendibles/{file_name}"  # Ruta local donde se guarda el archivo
        with open(file_path, 'w') as file:
            file.write(desprendible_pago)
        
        print(f"Desprendible de pago generado localmente: {file_name}")
        return file_path
    except Exception as e:
        print(f"Error al generar desprendible de pago para {empleado['nombre']} {empleado['apellido']}: {str(e)}")
        return None

def enviar_notificacion_correo(empleado, attachment_path):
    try:
        SENDER_EMAIL='tatigr211@gmail.com'
        correo = empleado['correo']
        nombre = empleado['nombre']
        apellido = empleado['apellido']
        saludo = f"Hola {nombre} {apellido},\n\n"
        message = Mail(
            from_email=SENDER_EMAIL,
            to_emails=correo,
            subject=f"Desprendible de pago para {nombre} {apellido}",
            html_content=saludo + "Adjunto encontrarás tu desprendible de pago."
        )

        with open(attachment_path, 'rb') as file:
            attachment_data = file.read()
            attachment_file = base64.b64encode(attachment_data).decode()
            message.attachment = Attachment(
                FileContent(attachment_file),
                FileName(os.path.basename(attachment_path)),
                FileType("application/octet-stream"),
                Disposition("attachment")
            )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        if response.status_code == 202:
            print("Correo electrónico enviado exitosamente.")
        else:
            print(f"Falló al enviar correo electrónico. Código de estado: {response.status_code}")
    except Exception as e:
        print(f"Error al enviar correo electrónico a {empleado['correo']}: {str(e)}")

#Inicializar el programador de tareas en segundo plano
scheduler = BackgroundScheduler()
scheduler.start()

#Definir la tarea para ejecutar a las 6:00 p.m.
@scheduler.scheduled_job('cron', hour=18, minute=0)
def ejecutar_tareas_diarias():
    for empleado in empleados:
        generar_desprendible_pago(empleado)
        enviar_notificacion_correo(empleado)

@app.route('/pago-nominas', methods=['POST'])
def pagar_nominas():
    data = request.json
    print("Datos recibidos:", data)
    if not data:
        print("Error: Datos incompletos en la solicitud")
        return jsonify({'error': 'Datos incompletos en la solicitud'}), 400
    
    #Verificar si son las 6:00 pm
    now = datetime.datetime.now()
    if now.hour != 18 or now.minute != 0:
        print("Error: Esta función solo se puede llamar alrededor de las 6:00 p.m.")
        return jsonify({'error': 'Esta función solo se puede llamar alrededor de las 6:00 p.m.'}), 400
    
    empleados_a_pagar = data
    print("Empleados a pagar:", empleados_a_pagar)
    
    if not empleados_a_pagar:
        print("Error: No se proporcionaron empleados para procesar")
        return jsonify({'error': 'No se proporcionaron empleados para procesar'}), 400
    
    for empleado in empleados_a_pagar:
        print("Procesando empleado:", empleado)
        attachment_path = generar_desprendible_pago(empleado)
        #Generar desprendible de pago y enviar notificación de correo para cada empleado
        generar_desprendible_pago(empleado)
        enviar_notificacion_correo(empleado, attachment_path)
        print("Desprendible generado y notificación de correo electrónico enviada para:", empleado)

    return jsonify({'mensaje': 'Pago de nóminas realizado'})

if __name__ == '__main__':
    app.run(debug=True)