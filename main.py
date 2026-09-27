import os
import speech_recognition as sr
import pyttsx3
import webbrowser
import musicLibrary
import requests
from dotenv import load_dotenv

load_dotenv()

recognizer = sr.Recognizer()
engine = pyttsx3.init()
newsapi = os.getenv("NEWS_API_KEY")

def speak(text):
    engine.say(text)
    engine.runAndWait()


def processcommand(c):
    if "open google" in c.lower():
        webbrowser.open("https://www.google.com")
    elif "open youtube" in c.lower():
        webbrowser.open("https://www.youtube.com")
    elif "open facebook" in c.lower():
        webbrowser.open("https://www.facebook.com")
    elif "open instagram" in c.lower():
        webbrowser.open("https://www.instagram.com")
    elif "open linkedin" in c.lower():
        webbrowser.open("https://www.linkedin.com")
    elif "open spotify" in c.lower():
        webbrowser.open("https://www.spotify.com")
    elif c.lower().startswith("play"):
        song = c.lower().split(" ")[1]
        link = musicLibrary.music.get(song)
        if link:
            webbrowser.open(link)
    elif "news" in c.lower():
        r = requests.get(f"https://newsapi.org/v2/top-headlines?country=in&apiKey={newsapi}")
        if r.status_code == 200:
            data = r.json()
            articles = data.get('articles', [])
            for article in articles:
                speak(article["title"])


if __name__ == "__main__":
    speak("Initializing Jarvis.......")
    while True:
        # listen for wake word Jarvis
        r = sr.Recognizer()
        print("recognizing...")
        # Rec speech using Google Speech Recognition
        try:
            with sr.Microphone() as source:
                print("Listening...")
                audio = r.listen(source, timeout=2, phrase_time_limit=1)
                word = r.recognize_google(audio)
                if word.lower() == "jarvis":
                    speak("Yaa")
                    # listen for command
                    with sr.Microphone() as source:
                        print("jarvis active...")
                        audio = r.listen(source)
                        command = r.recognize_google(audio)
                        processcommand(command)
        except Exception as e:
            print("Error: {0}".format(e))