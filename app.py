from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
import jwt
import datetime
import pymysql.cursors
from functools import wraps
import time
import random

app = Flask(__name__)
# Inicializamos Bcrypt para manejar el hashing/verificación de contraseñas
bcrypt = Bcrypt(app) 

# ------------------------------------------------
# CONFIGURACIÓN ESENCIAL
# ------------------------------------------------
MYSQL_HOST = 'localhost'
# ¡Usuario de MariaDB que creaste para la aplicación!
MYSQL_USER = 'usuario_app_libros' 
# ¡Contraseña segura de MariaDB para la aplicación!
MYSQL_PASSWORD = 'MiContraseñaSuperSegura!' 
MYSQL_DB = 'libros'
# ¡Clave secreta para firmar los JWTs!
JWT_SECRET_KEY = 'Una_Clave_Secreta_Para_JWT' 

# ------------------------------------------------
# FUNCIÓN DE CONEXIÓN A DB
# ------------------------------------------------
def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

# ------------------------------------------------
# MIDDLEWARE: VERIFICACIÓN JWT
# ------------------------------------------------
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Esperamos el formato: Authorization: Bearer <token>
        if 'Authorization' in request.headers:
            token_parts = request.headers['Authorization'].split(" ")
            if len(token_parts) == 2 and token_parts[0].lower() == 'bearer':
                token = token_parts[1]

        if not token:
            return jsonify({'message': 'Token de autenticación faltante!'}), 401

        try:
            # Decodificar y verificar la firma del token
            data = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            kwargs['user_id'] = data.get('user_id')
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token ha expirado!'}), 401
        except Exception:
            return jsonify({'message': 'Token inválido o error desconocido'}), 401

        return f(*args, **kwargs)
    return decorated

# ------------------------------------------------
# ENDPOINT DE AUTENTICACIÓN (LOGIN)
# ------------------------------------------------
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password') # Esperamos '123' del script de Locust

    if not email or not password:
        return jsonify({'message': 'Faltan email o contraseña'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    # 1. Buscar usuario por email
    cursor.execute("SELECT id, password_hash FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.check_password_hash(user['password_hash'], password):
        # 2. Generar el JWT
        token_payload = {
            'user_id': user['id'],
            # Token expira en 30 minutos
            'exp': datetime.datetime.utcnow() + datetime.timedelta(minutes=30),
            'iat': datetime.datetime.utcnow()
        }
        token = jwt.encode(token_payload, JWT_SECRET_KEY, algorithm='HS256')
        
        # Simula un pequeño retraso de red para la prueba de carga
        time.sleep(0.05) 
        
        return jsonify({'token': token}), 200
    else:
        # Credenciales incorrectas
        return jsonify({'message': 'Credenciales inválidas'}), 401

# ------------------------------------------------
# ENDPOINT PROTEGIDO: CREAR LIBRO (POST)
# ------------------------------------------------
@app.route('/api/v1/books', methods=['POST'])
@token_required # Se necesita un JWT válido para acceder
def create_book(user_id):
    data = request.get_json()
    title = data.get('title')
    author = data.get('author')
    year = data.get('year')

    if not title or not author:
        return jsonify({'message': 'Faltan título o autor'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # La tabla 'libros_data' debe haber sido creada previamente
        cursor.execute(
            "INSERT INTO libros_data (title, author, year) VALUES (%s, %s, %s)",
            (title, author, year)
        )
        conn.commit()
        time.sleep(0.01 + random.uniform(0, 0.05)) # Simulación de carga variable
        return jsonify({'message': 'Libro creado con éxito', 'id': cursor.lastrowid}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'message': f'Error de DB al crear libro: {e}'}), 500
    finally:
        cursor.close()
        conn.close()

# ------------------------------------------------
# ENDPOINT PROTEGIDO: OBTENER LIBROS (GET)
# ------------------------------------------------
@app.route('/api/v1/books', methods=['GET'])
@token_required # Se necesita un JWT válido para acceder
def get_all_books(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Obtener los libros (limitado a 100 para no sobrecargar)
    cursor.execute("SELECT title, author, year FROM libros_data LIMIT 100")
    books = cursor.fetchall()
    cursor.close()
    conn.close()
    
    time.sleep(0.02 + random.uniform(0, 0.03)) # Simulación de carga variable
    
    return jsonify(books), 200

# ------------------------------------------------
# EJECUCIÓN DEL SERVIDOR
# ------------------------------------------------
if __name__ == '__main__':
    # Ejecutamos en 0.0.0.0 para que sea accesible por Locust en tu VM
    app.run(host='0.0.0.0', port=8080, debug=True)