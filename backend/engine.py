import uuid
import logging

from backend.emotion_detector.detector import EmotionDetector
from .models import GameResponse
from backend.recording_manager.manager import RecordingResult
from backend.speech2text.speech2text import Speech2Text
from llm_integration.llm_client import LLMClient

logger = logging.getLogger(__name__)


class GameEngine:
    """
    Game engine for managing the state and flow of the emotion-driven game.

    This engine:
    1. Tracks active game sessions
    2. Maintains state for each session
    3. Processes inputs (emotions, speech)
    4. Communicates with the LLM to generate responses

    # TODO: Add achievement list and system
    # TODO: Add game state (game over or not)
    # TODO: Add game dialog and prompt
    """

    def __init__(
        self,
        llm_client: LLMClient,
        emotion_detector: EmotionDetector,
        speech_parser: Speech2Text,
    ):
        """
        Initialize the game engine

        Args:
            llm_client: Client for communicating with the LLM API
        """
        self.llm_client = llm_client
        self.emotion_detector = emotion_detector
        self.speech_parser = speech_parser

        logger.info("Game engine initialized")

    def create_new_game(self) -> str:
        """
        Create a new game session

        Returns:
            game_id: Unique identifier for the new game session
        """
        game_id = str(uuid.uuid4())
        logger.info(f"Created new game session: {game_id}")
        return game_id

    def process_recording(self, recording_result: RecordingResult) -> GameResponse:
        """
        Process the recording and send the results to the LLM
        """
        # TODO: Process the recording by using the emotion detector and speech parser
        # TODO: Serialize the results of the recording into a format that can be sent to the LLM
        # TODO: Send the results of the recording to the LLM
        # TODO: Send the response from the LLM to the websocket

        pass
