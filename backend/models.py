from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, model_serializer


class Achievement(BaseModel):
    name: str
    description: str


class EndingType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class NPC(BaseModel):
    id: str
    description: str
    role: str


class GameState(BaseModel):
    """Game state model to track progress and character states"""

    game_id: str
    game_over: bool = False
    achievements: List[Achievement] = Field(default_factory=list)
    dialog_history: List[Dict[str, str]] = Field(default_factory=list)
    suspicion_level: int = 5  # 0 to 10
    npcs: List[NPC] = Field(default_factory=list)
    dialog_exchanges_count: int = 0  # Count of dialog exchanges between user and system

    @property
    def achievement_names(self) -> List[str]:
        return [ach.name for ach in self.achievements]


class NPCDialog(BaseModel):
    dialog: str
    npc_id: str


class LLMResponse(BaseModel):
    """Model for the structured response from the LLM"""

    dialogs: List[NPCDialog]
    suspicion_level: int
    continue_story: bool
    ending_type: Optional[EndingType] = None
    achievement_unlocked: Optional[List[Achievement]] = None
    analysis: Optional[str] = None
    new_npc: Optional[NPC] = None

    @property
    def is_game_over(self) -> bool:
        return not self.continue_story


class GameResponse(BaseModel):
    """Response sent back to the frontend"""

    dialogs: List[NPCDialog]  # Dialogs to read for the NPCs
    suspicion_level: int  # Suspicion level of the NPC
    game_over: bool = False  # Whether the game is over
    ending_type: Optional[EndingType] = None  # Type of ending if game is over
    achievements: List[Achievement] = Field(default_factory=list)  # Achievements that were unlocked
    analysis: Optional[str] = None  # Analysis of the game when it's over

    @model_serializer
    def serialize_model(self) -> Dict[str, Any]:
        return {
            "dialogs": [dialog.model_dump() for dialog in self.dialogs],
            "suspicion_level": self.suspicion_level,
            "game_over": self.game_over,
            "ending_type": self.ending_type.value if self.ending_type else None,
            "achievements": [ach.model_dump() for ach in self.achievements],
            "analysis": self.analysis,
        }


class Emotions:
    """Class representing emotion probabilities detected in frames,
    and advanced metrics to describe the emotion consistency

    value is between 0 and 100
    """

    def __init__(self, emotion_probs: dict):
        # Core emotion probabilities
        self.angry: float = emotion_probs.get("angry", 0)
        self.disgust: float = emotion_probs.get("disgust", 0)
        self.fear: float = emotion_probs.get("fear", 0)
        self.happy: float = emotion_probs.get("happy", 0)
        self.sad: float = emotion_probs.get("sad", 0)
        self.surprise: float = emotion_probs.get("surprise", 0)
        self.neutral: float = emotion_probs.get("neutral", 0)

        # Advanced emotion analysis metrics
        self.stability: float = emotion_probs.get("stability", 100)
        self.transition_score: float = emotion_probs.get("transition_score", 0)
        self.consistent_emotion: bool = emotion_probs.get("consistent_emotion", True)

        # Emotion variances (represent consistency)
        self.angry_variance: float = emotion_probs.get("angry_variance", 0)
        self.disgust_variance: float = emotion_probs.get("disgust_variance", 0)
        self.fear_variance: float = emotion_probs.get("fear_variance", 0)
        self.happy_variance: float = emotion_probs.get("happy_variance", 0)
        self.sad_variance: float = emotion_probs.get("sad_variance", 0)
        self.surprise_variance: float = emotion_probs.get("surprise_variance", 0)
        self.neutral_variance: float = emotion_probs.get("neutral_variance", 0)

        self.normalize()

    def get_dominant_emotion(self) -> str:
        """Get the most prominent emotion"""
        emotions = {
            "angry": self.angry,
            "disgust": self.disgust,
            "fear": self.fear,
            "happy": self.happy,
            "sad": self.sad,
            "surprise": self.surprise,
            "neutral": self.neutral,
        }
        return max(emotions.items(), key=lambda x: x[1])[0]

    def get_emotion_volatility(self) -> str:
        """
        Get a description of emotion volatility based on variance and transition metrics

        Returns:
            String describing emotion consistency: 'stable', 'moderate', or 'volatile'
        """
        if self.stability >= 80 and self.transition_score <= 20:
            return "stable"
        elif self.stability <= 40 or self.transition_score >= 60:
            return "volatile"
        else:
            return "moderate"

    def normalize(self):
        """Normalize emotion values to ensure they sum to 100.0"""
        # Get all core emotion attributes excluding metadata and methods
        emotion_values = {
            k: v
            for k, v in self.__dict__.items()
            if not k.startswith("__")
            and k
            not in [
                "stability",
                "transition_score",
                "consistent_emotion",
                "angry_variance",
                "disgust_variance",
                "fear_variance",
                "happy_variance",
                "sad_variance",
                "surprise_variance",
                "neutral_variance",
            ]
        }
        total = sum(emotion_values.values())

        if total == 0:
            raise ValueError("Total sum of emotions is 0")

        # Normalize to percentages (0-100) and round to 1 decimal place
        for k, v in emotion_values.items():
            setattr(self, k, round((v / total) * 100, 1))

    def to_dict(self) -> Dict[str, Any]:
        """Convert emotions to dictionary format including advanced metrics"""
        basic_emotions = {
            "angry": self.angry,
            "disgust": self.disgust,
            "fear": self.fear,
            "happy": self.happy,
            "sad": self.sad,
            "surprise": self.surprise,
            "neutral": self.neutral,
        }

        # Add advanced metrics
        metrics = {
            "stability": self.stability,
            "transition_score": self.transition_score,
            "consistent_emotion": self.consistent_emotion,
            "dominant_emotion": self.get_dominant_emotion(),
            "volatility": self.get_emotion_volatility(),
        }

        # Combine all data
        return {**basic_emotions, **metrics}


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
