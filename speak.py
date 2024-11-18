import pyttsx3

def speak_titles_with_pyttsx3(movies):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    engine.setProperty('volume', 1.0)

    # Construir el mensaje completo
    message = "Te recomiendo las siguientes películas: "
    titles = [movie.get("title", "Título desconocido") for movie in movies]
    message += ", ".join(titles)
    message += ". Espero que disfrutes tus películas."

    print(f"Mensaje completo: {message}")  # Para depuración
    engine.say(message)
    engine.runAndWait()

# Ejemplo: Respuesta JSON
response_json = {
    'results': [
        {'title': 'Gladiator II', 'vote_average': 6.8},
        {'title': 'Terrifier 3', 'vote_average': 6.911}
    ]
}

movies = response_json['results']
speak_titles_with_pyttsx3(movies)
