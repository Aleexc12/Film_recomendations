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

# Diccionario de géneros de TMDB (ID: Nombre)
GENRES = {
    28: "action",
    12: "adventure",
    16: "animation",
    35: "comedy",
    80: "crime",
    99: "documentary",
    18: "drama",
    10751: "family",
    14: "fantasy",
    36: "history",
    27: "horror",
    10402: "music",
    9648: "mystery",
    10749: "romance",
    878: "science fiction",
    10770: "tv movie",
    53: "thriller",
    10752: "war",
    37: "western"
}

# Inversión del diccionario para búsquedas
GENRES_REVERSE = {v: k for k, v in GENRES.items()}

# Endpoint para obtener la lista de seguimiento del usuario
@app.route("/get_watchlist", methods=["GET"])
def get_watchlist():
    session_id = load_session()
    if not session_id:
        return jsonify({"error": "No se ha autenticado ningún usuario"}), 403

    # Obtener información del usuario
    account_url = f"{BASE_URL}/account"
    account_response = requests.get(account_url, params={"api_key": API_KEY, "session_id": session_id})
    if account_response.status_code == 200:
        account_id = account_response.json().get("id")
        watchlist_url = f"{BASE_URL}/account/{account_id}/watchlist/movies"
        
        # Recuperar los parámetros de filtrado de la URL
        vote_count = request.args.get("vote_count", type=int)
        vote_average = request.args.get("vote_average", type=float)
        after_year = request.args.get("after_year", type=int)
        before_year = request.args.get("before_year", type=int)
        adult = request.args.get("adult", type=bool)
        language = request.args.get("language", type=str)
        genre = request.args.get("genre", type=str)  # Palabra clave del género
        
        # Realizar la solicitud a la watchlist
        watchlist_response = requests.get(watchlist_url, params={"api_key": API_KEY, "session_id": session_id})
        if watchlist_response.status_code == 200:
            results = watchlist_response.json().get("results", [])
            
            # Filtrar resultados según los parámetros
            filtered_results = []
            for movie in results:
                # Filtrar por vote_count
                if vote_count and movie.get("vote_count", 0) < vote_count:
                    continue
                # Filtrar por vote_average
                if vote_average and movie.get("vote_average", 0.0) < vote_average:
                    continue
                # Filtrar por after_year
                release_year = int(movie.get("release_date", "0000")[:4]) if movie.get("release_date") else 0
                if after_year and release_year < after_year:
                    continue
                # Filtrar por before_year
                if before_year and release_year > before_year:
                    continue
                # Filtrar por adult
                if adult is not None and movie.get("adult") != adult:
                    continue
                # Filtrar por language
                if language and movie.get("original_language") != language:
                    continue
                # Filtrar por genre
                if genre:
                    genre_id = GENRES_REVERSE.get(genre.lower())
                    if genre_id and genre_id not in movie.get("genre_ids", []):
                        continue
                
                filtered_results.append(movie)
            
            return jsonify({"results": filtered_results})
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
