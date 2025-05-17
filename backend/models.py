import os
from typing import Optional, List, Dict, Any, Tuple, Union
from enum import Enum
from pydantic import BaseModel, Field, model_serializer


class Achievement(BaseModel):
    name: str
    description: str
    criteria: str
    unlocked: bool = False


class AchievementContext(BaseModel):
    """Context for an achievement that can be passed to the LLM"""

    id: str
    name: str
    description: str
    criteria: str


class GameStage(Enum):
    INITIAL_CONFRONTATION = "initial_confrontation"
    ESCALATING = "escalating"
    NEGOTIATING = "negotiating"
    DE_ESCALATING = "de_escalating"
    FINAL_CONFRONTATION = "final_confrontation"
    RESOLUTION = "resolution"


class EndingType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class GameState(BaseModel):
    """Game state model to track progress and character states"""

    game_id: str
    game_over: bool = False
    achievements: List[str] = []  # List of achievement IDs
    dialog_history: List[Dict[str, str]] = Field(default_factory=list)
    threat_level: int = 7  # 0 to 10
    stage: GameStage = GameStage.INITIAL_CONFRONTATION


class LLMResponse(BaseModel):
    """Model for the structured response from the LLM"""

    dialog: str
    internal_state: Dict[str, Any]
    game_status: Dict[str, Any]
    achievements: Optional[List[str]] = None

    @property
    def game_over(self) -> bool:
        return not self.game_status.get("continue", True)

    @property
    def threat_level(self) -> int:
        threat_level = self.internal_state.get("threat_level")
        if threat_level is None:
            raise ValueError("Threat level is not set")
        return threat_level

    @property
    def is_game_over(self) -> bool:
        return not self.game_status.get("continue", True)

    @property
    def ending_type(self) -> Optional[EndingType]:
        return self.game_status.get("ending_type")

    @property
    def stage(self) -> GameStage:
        stage = self.internal_state.get("stage")
        if stage is None:
            raise ValueError("Stage is not set")
        return stage


class GameResponse(BaseModel):
    """Response sent back to the frontend"""

    dialog: str  # Dialog to read for the NPC
    game_over: bool = False  # Whether the game is over
    ending_type: Optional[EndingType] = None  # Type of ending if game is over
    achievements: List[str] = Field(
        default_factory=list
    )  # ID of the achievements that were unlocked
    next_scene: Optional[GameStage] = None  # Next scene to play
    analysis: Optional[Dict[str, Any]] = None  # Analysis of the game when it's over

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "dialog": self.dialog,
            "game_over": self.game_over,
            "ending_type": self.ending_type.value if self.ending_type else None,
            "achievements": self.achievements,
            "next_scene": self.next_scene.value if self.next_scene else None,
            "analysis": self.analysis,
        }


def transcribe_audio(video_file: str) -> List[Dict[str, Any]]:
    """Placeholder function to transcribe audio from video file"""
    return [
        {
            "start": 2.1,
            "end": 5.5,
            "text": " I really like this and it was gift for my parents.",
        }
    ]


def extract_frames(video_file: str, segments: List[Dict[str, Any]]) -> Tuple:
    """Placeholder function to extract frames from video file"""
    return [
        (
            f"frame_{i}.jpg",
            segment["start"],
            segment["end"],
            segment["text"],
        )
        for i, segment in enumerate(segments)
    ]


def detect_emotions(frames: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Placeholder function to detect emotions from frames"""
    # In a real implementation, this would analyze frames and detect emotions
    return [
        {
            "emotion": {
                "anger": 0.0,
                "disgust": 0.0,
                "fear": 0.0,
                "happiness": 0.0,
                "neutral": 0.0,
                "sadness": 0.0,
                "surprise": 0.0,
            },
            "time": (start, end),
            "text": text,
        }
        for frame_path, start, end, text in frames
    ]


class DialogInputDCL:
    def __init__(self, video_file: str):
        self.emotions: list[str] = []
        self.sentences: list[str] = []
        self.mid_timestamps: list[float] = []
        self.start_times: list[float] = []
        self.end_times: list[float] = []
        self.video_file: str = video_file
        self.get_dialog_input(video_file)

    def get_dialog_input(self, file_path: str):
        if not os.path.isabs(file_path):
            # If relative path is provided, make it absolute relative to script location
            video_file = os.path.join(os.path.dirname(__file__), file_path)
        else:
            video_file = file_path

        if not os.path.exists(video_file):
            raise FileNotFoundError(f"Video file not found: {video_file}")

        segments = transcribe_audio(video_file)
        frames = extract_frames(video_file, segments)
        emotions = detect_emotions(frames)

        for entry in emotions:
            self.emotions.append(entry["emotion"])
            self.sentences.append(entry["text"])
            self.mid_timestamps.append((entry["time"][0] + entry["time"][1]) / 2)
            self.start_times.append(entry["time"][0])
            self.end_times.append(entry["time"][1])
