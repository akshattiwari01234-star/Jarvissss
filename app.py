"""
Jarvis AI Assistant – FastAPI Backend
Serves the web UI and exposes REST + WebSocket endpoints for all Jarvis features.
"""

import json
import os
import webbrowser
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv
# pyrefly: ignore [missing-import]
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
# pyrefly: ignore [missing-import]
from fastapi.responses import HTMLResponse, JSONResponse
# pyrefly: ignore [missing-import]
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


import musicLibrary

load_dotenv()

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

# ──────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────
app = FastAPI(title="Jarvis AI Assistant", version="2.0")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# In-memory command history
command_history: list[dict] = []


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────
class CommandRequest(BaseModel):
    command: str


class MusicAddRequest(BaseModel):
    name: str
    url: str


# ──────────────────────────────────────────────
# WebSocket Manager (real-time log streaming)
# ──────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


# ──────────────────────────────────────────────
# Helper – process a text command
# ──────────────────────────────────────────────
def process_command(command: str) -> dict:
    """Process a command string and return a result dict."""
    c = command.strip()
    cl = c.lower()
    timestamp = datetime.now().strftime("%H:%M:%S")

    # ── Website commands ──
    sites = {
        "open google": "https://www.google.com",
        "open youtube": "https://www.youtube.com",
        "open facebook": "https://www.facebook.com",
        "open instagram": "https://www.instagram.com",
        "open linkedin": "https://www.linkedin.com",
        "open spotify": "https://www.spotify.com",
        "open github": "https://www.github.com",
        "open twitter": "https://www.twitter.com",
        "open reddit": "https://www.reddit.com",
    }

    for trigger, url in sites.items():
        if trigger in cl:
            webbrowser.open(url)
            site_name = trigger.replace("open ", "").title()
            return {
                "type": "site",
                "status": "success",
                "message": f"Opening {site_name}…",
                "url": url,
                "timestamp": timestamp,
            }

    # ── Play music ──
    if cl.startswith("play"):
        parts = cl.split(" ", 1)
        if len(parts) > 1:
            song_name = parts[1].strip()
            link = musicLibrary.music.get(song_name)
            if link:
                webbrowser.open(link)
                return {
                    "type": "music",
                    "status": "success",
                    "message": f"🎵 Playing '{song_name}'",
                    "url": link,
                    "timestamp": timestamp,
                }
            else:
                return {
                    "type": "music",
                    "status": "error",
                    "message": f"Song '{song_name}' not found in library.",
                    "timestamp": timestamp,
                }
        return {
            "type": "music",
            "status": "error",
            "message": "Please specify a song name. E.g. 'play believer'",
            "timestamp": timestamp,
        }

    # ── News ──
    if "news" in cl:
        try:
            r = requests.get(
                f"https://newsapi.org/v2/everything?q=india&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}",
                timeout=10,
            )
            if r.status_code == 200:
                articles = r.json().get("articles", [])[:10]
                headlines = []
                for a in articles:
                    headlines.append(
                        {
                            "title": a.get("title", ""),
                            "description": a.get("description", ""),
                            "url": a.get("url", ""),
                            "image": a.get("urlToImage", ""),
                            "source": a.get("source", {}).get("name", ""),
                        }
                    )
                return {
                    "type": "news",
                    "status": "success",
                    "message": f"Fetched {len(headlines)} headlines",
                    "articles": headlines,
                    "timestamp": timestamp,
                }
            else:
                return {
                    "type": "news",
                    "status": "error",
                    "message": f"News API returned status {r.status_code}",
                    "timestamp": timestamp,
                }
        except Exception as e:
            return {
                "type": "news",
                "status": "error",
                "message": f"Failed to fetch news: {e}",
                "timestamp": timestamp,
            }

    # ── Time ──
    if "time" in cl:
        now = datetime.now().strftime("%I:%M %p")
        return {
            "type": "info",
            "status": "success",
            "message": f"🕐 The current time is {now}",
            "timestamp": timestamp,
        }

    # ── Date ──
    if "date" in cl:
        today = datetime.now().strftime("%A, %B %d, %Y")
        return {
            "type": "info",
            "status": "success",
            "message": f"📅 Today is {today}",
            "timestamp": timestamp,
        }

    # ── Help ──
    if "help" in cl:
        return {
            "type": "help",
            "status": "success",
            "message": "Available commands",
            "commands": [
                {"cmd": "open google/youtube/…", "desc": "Open a website in your browser"},
                {"cmd": "play <song>", "desc": "Play a song from the music library"},
                {"cmd": "news", "desc": "Fetch latest Indian headlines"},
                {"cmd": "time", "desc": "Get current time"},
                {"cmd": "date", "desc": "Get today's date"},
                {"cmd": "help", "desc": "Show this help message"},
            ],
            "timestamp": timestamp,
        }

    # ── Fallback ──
    return {
        "type": "unknown",
        "status": "info",
        "message": f"I'm not sure how to handle: \"{c}\". Type 'help' for available commands.",
        "timestamp": timestamp,
    }


# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))


@app.post("/api/command")
async def handle_command(body: CommandRequest):
    result = process_command(body.command)
    command_history.append({"command": body.command, **result})
    # Broadcast to all connected WebSocket clients
    await manager.broadcast({"event": "command_result", "data": result})
    return JSONResponse(result)


@app.get("/api/music")
async def get_music_library():
    return JSONResponse(
        {"music": [{"name": k, "url": v} for k, v in musicLibrary.music.items()]}
    )


@app.post("/api/music")
async def add_music(body: MusicAddRequest):
    musicLibrary.music[body.name.lower()] = body.url
    return JSONResponse({"status": "success", "message": f"Added '{body.name}' to library"})


@app.delete("/api/music/{name}")
async def delete_music(name: str):
    if name.lower() in musicLibrary.music:
        del musicLibrary.music[name.lower()]
        return JSONResponse({"status": "success", "message": f"Removed '{name}'"})
    return JSONResponse({"status": "error", "message": f"'{name}' not found"}, status_code=404)


@app.get("/api/history")
async def get_history():
    return JSONResponse({"history": command_history[-50:]})


# ── WebSocket ──
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("type") == "command":
                result = process_command(payload["command"])
                command_history.append({"command": payload["command"], **result})
                await manager.broadcast({"event": "command_result", "data": result})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
