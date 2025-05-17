import asyncio
import os
from typing import Optional
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import logging

from models import GameResponse, GameStage
from engine import GameEngine
from llm_integration.llm_client import LLMClient
from recording_manager.manager import RecordingManager, RecordingResult, RecordingStatus
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

websocket_connection: Optional[WebSocket] = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
async def root():
    return {"status": "running", "service": "emotion-driven-game-backend"}


@app.post("/start-game")
async def start_game():
    """Initialize a new game session"""
    game_id, initial_dialog = game_engine.create_new_game()
    if websocket_connection:
        # Send dialog to start the convo
        await websocket_connection.send_text(f"new_game:{game_id}")
        await websocket_connection.send_json({"monolog": initial_dialog})
    return {"game_id": game_id, "initial_dialog": initial_dialog}


@app.post("/recording/start")
async def start_recording():
    """Start recording audio and video"""
    try:
        result = recording_manager.start_recording()
        return result
    except Exception as e:
        logger.error(f"Error starting recording: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recording/stop")
async def stop_recording():
    """Stop recording and start processing the results asynchronously"""
    try:
        result = recording_manager.stop_recording()
        asyncio.create_task(process_recording(result))
        return result
    except Exception as e:
        logger.error(f"Error stopping recording: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def process_recording(recording_result: RecordingResult):
    """Process the recording and send the results to the websocket"""

    game_response: GameResponse = game_engine.process_recording(recording_result)
    if websocket_connection:
        if game_response.dialog:
            await websocket_connection.send_json(
                {
                    "dialog": game_response.dialog,
                }
            )
        if game_response.game_over:
            await websocket_connection.send_json(
                {
                    "game_over": True,
                }
            )
        if game_response.achievements:
            await websocket_connection.send_json(
                {
                    "achievement_unlocked": [
                        ach.model_dump() for ach in game_response.achievements
                    ],
                }
            )
        if game_response.next_stage:
            await websocket_connection.send_json(
                {
                    "next_stage": game_response.next_stage.value,
                }
            )


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    global websocket_connection
    websocket_connection = websocket

    try:
        while True:
            data = await websocket.receive_text()
            if data == "stop":
                break
    except WebSocketDisconnect:
        websocket_connection = None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
