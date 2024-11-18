from flask import Flask, redirect, request, jsonify
import requests
import json
import os

# Configuración de la API de TMDb
API_KEY = "60c89628397ca3b3a7063a8c0d03bccb"  # Reemplaza con tu API Key
BASE_URL = "https://api.themoviedb.org/3"

# Archivo donde se guarda la sesión
SESSION_FILE = "session_data.json"

# Crear la app Flask
app = Flask(__name__)

# Función para cargar la sesión
def load_session():
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as file:
            data = json.load(file)
            return data.get("session_id")
    return None

# Función para guardar la sesión
def save_session(session_id):
    with open(SESSION_FILE, "w") as file:
        json.dump({"session_id": session_id}, file)

# Endpoint principal
@app.route("/")
def home():
    session_id = load_session()
    if session_id:
        return jsonify({
            "message": "Ya estás autenticado",
            "endpoints": {
                "Ver lista de seguimiento": "/get_watchlist"
            }
        })
    else:
        return redirect("/authenticate")

# Endpoint para autenticarse
@app.route("/authenticate")
def authenticate():
    # Paso 1: Obtener el request token
    url = f"{BASE_URL}/authentication/token/new"
    response = requests.get(url, params={"api_key": API_KEY})
    if response.status_code == 200:
        request_token = response.json()["request_token"]
        approval_url = f"https://www.themoviedb.org/authenticate/{request_token}?redirect_to=/callback"
        return redirect(approval_url)  # Redirigir al usuario para que apruebe la solicitud
    else:
        return jsonify({
            "error": "Error al obtener el request token",
            "details": response.json()
        }), 500

# Endpoint de callback para guardar el session_id
@app.route("/callback")
def callback():
    # Paso 2: Usar el token aprobado para generar un session_id
    request_token = request.args.get("request_token")
    if not request_token:
        return jsonify({"error": "No se recibió el token de autenticación"}), 400

    url = f"{BASE_URL}/authentication/session/new"
    response = requests.post(url, params={"api_key": API_KEY}, json={"request_token": request_token})
    if response.status_code == 200:
        session_id = response.json()["session_id"]
        save_session(session_id)
        return jsonify({"message": "Autenticación exitosa", "session_id": session_id})
    else:
        return jsonify({
            "error": "Error al obtener el session ID",
            "details": response.json()
        }), 500

# Endpoint para obtener la lista de seguimiento del usuario
@app.route("/get_watchlist")
def get_watchlist():
    session_id = load_session()
    if not session_id:
        return jsonify({"error": "No se ha autenticado ningún usuario"}), 403

    # Obtener información del usuario
    account_url = f"{BASE_URL}/account"
    account_response = requests.get(account_url, params={"api_key": API_KEY, "session_id": session_id})
    if account_response.status_code == 200:
        account_id = account_response.json()["id"]
        watchlist_url = f"{BASE_URL}/account/{account_id}/watchlist/movies"
        watchlist_response = requests.get(watchlist_url, params={"api_key": API_KEY, "session_id": session_id})
        if watchlist_response.status_code == 200:
            return jsonify(watchlist_response.json())
        else:
            return jsonify({
                "error": "Error al obtener la lista de seguimiento",
                "details": watchlist_response.json()
            }), 500
    else:
        return jsonify({
            "error": "Error al obtener los datos del usuario",
            "details": account_response.json()
        }), 500

if __name__ == "__main__":
    app.run(debug=True)
