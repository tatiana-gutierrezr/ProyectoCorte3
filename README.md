# Sistema de nómina y recursos humanos

Este proyecto consiste en una API REST para la gestión eficiente de la nómina y los recursos humanos de una empresa. Proporciona funcionalidades para la gestión integral de empleados, el pago de nóminas diario, y el envío automático de desprendibles de pago por correo electrónico.

## Integrantes
- Tatiana Gutierrez Rodriguez
- Juan Pablo Vargas Balli

## Instalación y configuración
1. Clona este repositorio en tu máquina local.
2. Instala las dependencias ejecutando `pip install -r requirements.txt`.
3. Crea un archivo `.env` en el directorio raíz y configura las variables de entorno necesarias (Para el profesor, ver mensaje en AVATA).
4. Inicia la aplicación ejecutando `python app.py`.

## Endpoints de la API

### Autenticación
- `POST /login`: Permite a los usuarios iniciar sesión proporcionando sus credenciales.
- `GET /logout`: Cierra la sesión del usuario actual.

### Gestión de Empleados
- `GET /empleados`: Obtiene la lista de todos los empleados.
- `GET /empleados/<id>`: Obtiene los detalles de un empleado específico.
- `POST /empleados`: Crea un nuevo empleado.
- `PUT /empleados/<id>`: Actualiza los detalles de un empleado existente.
- `DELETE /empleados/<id>`: Elimina un empleado existente.

### Pago de Nóminas
- `POST /pago-nominas`: Realiza el pago de nóminas diario.

### Generación de desprendible de pago
- No hay endpoints específicos, la generación de desprendibles de pago se realiza automáticamente después del pago de nóminas.

## Ejemplos de uso
---
### Iniciar sesión
```json
POST /login
{
  "correo": "juan@example.com",
  "contrasena": "juan123"
}
```

### Obtener lista de empleados
```json
GET /empleados
```

### Crear un nuevo empleado
```json
POST /empleados
{
  "correo": "laura@example.com",
  "nombre": "Laura",
  "apellido": "Martinez",
  "rol": "recepcionista",
  "salario_base": 24000,
  "deducciones": [
    {"concepto": "Pago EPS", "monto": 1100},
    {"concepto": "Impuestos", "monto": 2000}
  ],
  "contrasena": "laura789",
  "direccion": "Calle 64 #1-15",
  "celular": "3099871232",
  "superadmin": "no"
}
```

### Actualizar datos de un empleado
```json
PUT /empleados/2
{
  "direccion": "Calle 64 #112-82, Bogotá"
}
```

### Eliminar un empleado
```json
DELETE /empleados/3
```

### Realizar pago de nóminas
```json
POST /pago-nominas
```

## Errores y Manejo de Excepciones
- Códigos de Estado:
  - 200: Solicitud exitosa.
  - 400: Error en la solicitud.
  - 401: No autorizado, credenciales incorrectas.
  - 403: Prohibido, falta de permisos.
  - 404: Recurso no encontrado.

## Seguridad
- Las contraseñas de los usuarios se almacenan de forma segura utilizando el algoritmo bcrypt.
- Se requiere autenticación para acceder a ciertos endpoints, como la gestión de empleados y el pago de nóminas.

## Referencias
- [Documentación de Flask](https://flask.palletsprojects.com/)
- [Documentación de Flask-RESTful](https://flask-restful.readthedocs.io/)
- [Documentación de Twilio SendGrid](https://sendgrid.com/docs/)
- [Documentación de Python Bcrypt](https://github.com/pyca/bcrypt/)

---
