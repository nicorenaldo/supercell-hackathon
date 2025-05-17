from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, model_serializer


class Achievement(BaseModel):
    name: str
    description: str


class GameStage(Enum):
    INTRODUCTION = "introduction"
    INVESTIGATION = "investigation"
    GAINING_TRUST = "gaining_trust"
    CHALLENGE = "challenge"
    DISCOVERY = "discovery"
    MISSION_EXECUTION = "mission_execution"
    EXTRACTION = "extraction"


class EndingType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class NPC(BaseModel):
    id: str
    description: str


class GameState(BaseModel):
    """Game state model to track progress and character states"""

    game_id: str
    game_over: bool = False
    achievements: List[Achievement] = Field(default_factory=list)
    dialog_history: List[Dict[str, str]] = Field(default_factory=list)
    suspicion_level: int = 5  # 0 to 10
    stage: GameStage = GameStage.INTRODUCTION
    npcs: List[NPC] = Field(default_factory=list)

    @property
    def achievement_names(self) -> List[str]:
        return [ach.name for ach in self.achievements]


class LLMResponse(BaseModel):
    """Model for the structured response from the LLM"""

    dialog: str
    npc_id: str
    suspicion_level: int
    stage: GameStage
    continue_story: bool
    ending_type: Optional[EndingType] = None
    achievement_unlocked: Optional[List[Achievement]] = None
    analysis: Optional[str] = None

    @property
    def is_game_over(self) -> bool:
        return not self.continue_story


class GameResponse(BaseModel):
    """Response sent back to the frontend"""

    dialog: str  # Dialog to read for the NPC
    npc_id: str  # ID of the NPC that is speaking
    suspicion_level: int  # Suspicion level of the NPC
    game_over: bool = False  # Whether the game is over
    ending_type: Optional[EndingType] = None  # Type of ending if game is over
    achievements: List[Achievement] = Field(default_factory=list)  # Achievements that were unlocked
    analysis: Optional[str] = None  # Analysis of the game when it's over

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "dialog": self.dialog,
            "npc_id": self.npc_id,
            "suspicion_level": self.suspicion_level,
            "game_over": self.game_over,
            "ending_type": self.ending_type.value if self.ending_type else None,
            "achievements": [ach.model_dump() for ach in self.achievements],
            "analysis": self.analysis,
        }


class Emotions:
    """Class representing emotion probabilities detected in frames"""

    def __init__(self, emotion_probs: dict):
        self.angry: float = emotion_probs.get("angry", 0)
        self.disgust: float = emotion_probs.get("disgust", 0)
        self.fear: float = emotion_probs.get("fear", 0)
        self.happy: float = emotion_probs.get("happy", 0)
        self.sad: float = emotion_probs.get("sad", 0)
        self.surprise: float = emotion_probs.get("surprise", 0)
        self.neutral: float = emotion_probs.get("neutral", 0)
        self.normalize()

    def normalize(self):
        """Normalize emotion values to ensure they sum to 1.0"""
        emotion_values = {k: v for k, v in self.__dict__.items() if not k.startswith("__")}
        total = sum(emotion_values.values())

        if total == 0:
            raise ValueError("Total sum of emotions is 0")

        # Normalize to percentages
        for k, v in emotion_values.items():
            setattr(self, k, (v / total))

    def to_dict(self) -> Dict[str, float]:
        """Convert emotions to dictionary format"""
        return {
            "angry": self.angry,
            "disgust": self.disgust,
            "fear": self.fear,
            "happy": self.happy,
            "sad": self.sad,
            "surprise": self.surprise,
            "neutral": self.neutral,
        }


class DialogInput:
    """Class representing the extracted dialog and emotions from a video"""

    def __init__(self, video_file: str, emotion_results: List[Dict[str, Any]]):
        """
        Initialize dialog input from emotion results

        Args:
            video_file: Path to the original video file
            emotion_results: Results from emotion detection
        """
        self.video_file: str = video_file
        self.emotions: List[Emotions] = []
        self.sentences: List[str] = []
        self.mid_timestamps: List[float] = []
        self.start_times: List[float] = []
        self.end_times: List[float] = []

        # Process emotion results
        for entry in emotion_results:
            self.emotions.append(Emotions(entry["emotions"]))
            self.sentences.append(entry["text"])
            self.mid_timestamps.append((entry["time"][0] + entry["time"][1]) / 2)
            self.start_times.append(entry["time"][0])
            self.end_times.append(entry["time"][1])

    def to_dict(self) -> List[Dict[str, Any]]:
        """Convert dialog input to dictionary format"""
        return [
            {
                "text": text,
                "emotions": emotion.to_dict(),
                "start_time": start,
                "end_time": end,
            }
            for text, emotion, start, end in zip(
                self.sentences,
                self.emotions,
                self.start_times,
                self.end_times,
            )
        ]
