import asyncio
import os
from typing import Dict, List, Optional
import uuid
from fastapi import (
    FastAPI,
    WebSocket,
    HTTPException,
    WebSocketDisconnect,
    BackgroundTasks,
    UploadFile,
    File,
)
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging
import tempfile
from pydantic import BaseModel
import google.auth
import google.auth.transport.requests
from google.oauth2 import service_account
import requests

from flask import json

from models import GameResponse
from engine import GameEngine
from llm_client import LLMClient
from recording import RecordingManager, RecordingResult
from video_processor import VideoProcessor

load_dotenv()

app = FastAPI(title="Sensory Game Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

video_processor = VideoProcessor()
llm_client = LLMClient(api_key=os.getenv("OPENAI_API_KEY"))
game_engine = GameEngine(llm_client, video_processor)
recording_manager = RecordingManager()

# Dictionary to store active WebSocket connections by game_id
websocket_connections: Dict[str, WebSocket] = {}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextToSpeechRequest(BaseModel):
    text: str
    npcId: str
    voiceOptions: dict


@app.get("/")
async def root():
    return {"status": "running", "service": "emotion-driven-game-backend"}


@app.delete("/game/{game_id}")
async def end_game(game_id: str, background_tasks: BackgroundTasks):
    """End a game session and clean up resources"""
    if game_id not in game_engine.game_sessions:
        raise HTTPException(status_code=404, detail=f"Game session {game_id} not found")

    # Clean up recording resources
    background_tasks.add_task(cleanup_game_resources, game_id)

    return {"status": "success", "message": f"Game {game_id} ended and cleanup scheduled"}


async def cleanup_game_resources(game_id: str):
    """Clean up resources for a game session"""
    # Clean up recording resources
    recording_manager.cleanup(game_id)

    # Remove the game session from the engine
    if game_id in game_engine.game_sessions:
        del game_engine.game_sessions[game_id]

    # Close and remove the WebSocket connection if it exists
    if game_id in websocket_connections:
        try:
            await websocket_connections[game_id].close()
        except Exception as e:
            logger.error(f"Error closing WebSocket for game {game_id}: {e}")
        del websocket_connections[game_id]

    logger.info(f"Cleaned up resources for game {game_id}")


@app.post("/recording/upload/{game_id}")
async def upload_recording(
    game_id: str, video: UploadFile = File(...), background_tasks: BackgroundTasks = None
):
    """Upload a video recording directly and process it"""
    try:
        if game_id not in game_engine.game_sessions:
            raise HTTPException(status_code=404, detail=f"Game session {game_id} not found")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
            content = await video.read()
            tmp_file.write(content)
            file_path = tmp_file.name

        recording_result = recording_manager.handle_uploaded_file(game_id, file_path)

        print(f"Processing recording for game {game_id}, file path: {recording_result.file_path}")
        await process_recording(recording_result, game_id)
        # background_tasks.add_task(cleanup_temp_file, file_path)

        return {"status": "success", "message": "Video uploaded and processing started"}
    except Exception as e:
        logger.error(f"Error processing uploaded video: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def cleanup_temp_file(file_path: str):
    """Clean up temporary file after processing"""
    try:
        if os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Temporary file {file_path} removed")
    except Exception as e:
        logger.error(f"Error removing temporary file {file_path}: {str(e)}")


async def process_recording(recording_result: RecordingResult, game_id: str):
    """Process the recording and send the results to the websocket"""

    websocket = websocket_connections.get(game_id)
    if not websocket:
        logger.warning(f"No active WebSocket connection for game {game_id}")
        return

    game_response: GameResponse = game_engine.process_recording(recording_result, game_id)

    try:
        if game_response.game_over:
            await websocket.send_json(
                {
                    "game_over": True,
                    "ending_type": game_response.ending_type.value,
                    "suspicion_level": game_response.suspicion_level,
                    "analysis": game_response.analysis,
                }
            )
        if game_response.achievements:
            await websocket.send_json(
                {
                    "achievement_unlocked": [
                        ach.model_dump() for ach in game_response.achievements
                    ],
                }
            )
        if game_response.dialogs:
            for dialog in game_response.dialogs:
                await websocket.send_json(
                    {
                        "dialog": dialog.dialog,
                        "npc_id": dialog.npc_id,
                        "suspicion_level": game_response.suspicion_level,
                    }
                )
    except Exception as e:
        logger.error(f"Error sending response to websocket for game {game_id}: {e}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint that handles connections with a client identifier"""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            if payload.get("action") == "start":
                game_id, initial_dialog = game_engine.create_new_game()
                websocket_connections[game_id] = websocket
                await websocket.send_json({"game_id": game_id})
                await websocket.send_json({"dialog": initial_dialog})
            elif payload.get("action") == "stop":
                break
    except WebSocketDisconnect:
        # Remove the websocket connection when it's disconnected
        logger.info(f"WebSocket connection closed for client")


@app.get("/active-games")
async def get_active_games():
    """Get all active game sessions"""
    return {
        "active_games": list(game_engine.game_sessions.keys()),
        "active_connections": list(websocket_connections.keys()),
    }


@app.get("/game/{game_id}")
async def get_game_details(game_id: str):
    """Get details for a specific game session"""
    game_state = game_engine.get_game_state(game_id)
    if not game_state:
        raise HTTPException(status_code=404, detail=f"Game session {game_id} not found")

    # Convert the game state to a dict and return relevant information
    return {
        "game_id": game_state.game_id,
        "game_over": game_state.game_over,
        "suspicion_level": game_state.suspicion_level,
        "dialog_exchanges_count": game_state.dialog_exchanges_count,
        "achievements": [ach.model_dump() for ach in game_state.achievements],
        "npcs": [npc.model_dump() for npc in game_state.npcs],
        "has_websocket_connection": game_id in websocket_connections,
    }


@app.on_event("shutdown")
async def shutdown_event():
    """Event handler for application shutdown"""
    logger.info("Application shutting down, cleaning up resources")
    recording_manager.cleanup()


@app.post("/api/synthesize-speech")
async def synthesize_speech(request: TextToSpeechRequest):
    """Proxy requests to Google Text-to-Speech API"""
    try:
        # Get Google Cloud credentials from environment
        project_id = os.getenv("GOOGLE_PROJECT_ID")
        print(f"Project ID: {project_id}")
        # Use a service account key file or Application Default Credentials
        # Option 1: Using service account key file
        service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        if service_account_key:
            credentials = service_account.Credentials.from_service_account_file(
                service_account_key, scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
        else:
            # Option 2: Use Application Default Credentials
            credentials, project = google.auth.default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )

        # Make sure credentials are valid
        auth_req = google.auth.transport.requests.Request()
        credentials.refresh(auth_req)

        # Prepare request to Google TTS API
        voice_options = request.voiceOptions
        tts_request = {
            "input": {"text": request.text},
            "voice": {
                "languageCode": voice_options["languageCode"],
                "name": voice_options["name"],
            },
            "audioConfig": {"audioEncoding": "MP3"},
        }

        headers = {
            "Authorization": f"Bearer {credentials.token}",
            "Content-Type": "application/json",
        }

        response = requests.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize",
            headers=headers,
            json=tts_request,
        )

        if not response.ok:
            return {"error": {"message": f"TTS API error: {response.text}"}}

        return response.json()

    except Exception as e:
        logger.error(f"Error in text-to-speech: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
