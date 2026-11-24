"""Prueba de carga de FinanBot (Taller 6 - RNF de Eficiencia de Desempeño).

Uso (con el backend corriendo en http://127.0.0.1:8000):
    locust -f locustfile.py --host http://127.0.0.1:8000
y abrir http://localhost:8089  (ej. 50 usuarios, spawn rate 5).

Variables opcionales: FINANBOT_LOAD_EMAIL, FINANBOT_LOAD_PASSWORD
(cuenta de prueba que ya exista en la base de datos).
"""
import os

from locust import HttpUser, between, task

CORREO = os.getenv('FINANBOT_LOAD_EMAIL', 'auditor@finanbot.test')
CONTRASENA = os.getenv('FINANBOT_LOAD_PASSWORD', 'Clave#12345')


class UsuarioFinanBot(HttpUser):
    wait_time = between(1, 2)  # Pausa de 1 a 2 segundos entre peticiones

    def on_start(self):
        respuesta = self.client.post(
            '/api/auth/login',
            json={'correo': CORREO, 'contrasena': CONTRASENA},
            name='POST /api/auth/login',
        )
        token = respuesta.json().get('token', '') if respuesta.ok else ''
        self.client.headers.update({'Authorization': f'Bearer {token}'})

    @task(3)
    def consultar_transacciones(self):
        self.client.get('/api/transacciones/', name='GET /api/transacciones/')

    @task(2)
    def consultar_metas(self):
        self.client.get('/api/metas/', name='GET /api/metas/')

    @task(2)
    def consultar_recomendaciones(self):
        self.client.get('/api/recomendaciones/', name='GET /api/recomendaciones/')

    @task(1)
    def consultar_perfil(self):
        self.client.get('/api/perfil/', name='GET /api/perfil/')

    @task(1)
    def consultar_conversaciones(self):
        self.client.get('/api/chat-historial/conversaciones', name='GET /api/chat-historial/conversaciones')
