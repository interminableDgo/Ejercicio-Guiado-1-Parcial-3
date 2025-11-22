from locust import HttpUser, task, between
import random

# Definimos una clase para simular un usuario
class BookUser(HttpUser):
    # Intervalo de espera entre peticiones
    wait_time = between(1, 3) 
    
    # URL base de tu microservicio (donde está corriendo Flask)
    host = "http://localhost:8080" 
    
    # Esta función se ejecuta UNA SOLA VEZ al inicio de cada usuario simulado
    def on_start(self):
        # 1. Petición de LOGIN con las credenciales de prueba
        login_data = {
            "email": "test_locust@libros.com",
            "password": "123" # Contraseña en texto plano para el request
        }
        
        # Endpoint de login del microservicio
        response = self.client.post("/auth/login", json=login_data, name="0. Login [POST]")
        
        if response.status_code == 200:
            # 2. Almacenar el JWT y preparar las cabeceras para futuras peticiones
            self.token = response.json().get('token')
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            print(f"Login fallido con status: {response.status_code}. Deteniendo usuario.")
            self.environment.runner.quit()

    # Tarea 1: Obtener todos los libros (Ruta Protegida, más frecuente)
    @task(3)
    def get_all_books_protected(self):
        self.client.get("/api/v1/books", headers=self.headers, name="/books [GET] - Auth")

    # Tarea 2: Crear un nuevo libro (Ruta Protegida, menos frecuente)
    @task(1) 
    def create_book_protected(self):
        book_data = {
            "title": f"Libro Test {random.randint(1, 10000)}",
            "author": "Locust",
            "year": 2025
        }
        self.client.post("/api/v1/books", json=book_data, headers=self.headers, name="/books [POST] - Auth")