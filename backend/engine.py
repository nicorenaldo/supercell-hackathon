from typing import Dict, List, Any, Optional
import uuid
import logging

from emotion_detector.detector import EmotionDetector
from models import (
    Achievement,
    AchievementContext,
    DialogInputDCL,
    EndingType,
    GameResponse,
    GameStage,
    GameState,
    LLMResponse,
)
from recording_manager.manager import RecordingResult
from speech2text.speech2text import Speech2Text
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
            emotion_detector: Detector for analyzing emotions
            speech_parser: Parser for converting speech to text
        """
        self.llm_client = llm_client
        self.emotion_detector = emotion_detector
        self.speech_parser = speech_parser

        self.current_state: Optional[GameState] = None

        self.achievements: Dict[str, Achievement] = {
            "smart_ass": Achievement(
                name="Smart Ass",
                description="You're a smart ass",
                criteria="Acting smart ass",
            ),
            "not_afraid": Achievement(
                name="Not Afraid",
                description="You're not afraid",
                criteria="Asking for a fight instead of running away",
            ),
            "silver_tongue": Achievement(
                name="Silver Tongue",
                description="Talk your way out of danger",
                criteria="Convince the thug to leave without confrontation",
            ),
            "brave_heart": Achievement(
                name="Brave Heart",
                description="Show no fear in the face of danger",
                criteria="Maintain confident emotions throughout encounter",
            ),
        }

        logger.info("Game engine initialized")

    def create_new_game(self) -> str:
        """
        Create a new game session

        Returns:
            game_id: Unique identifier for the new game session
        """
        game_id = str(uuid.uuid4())
        self.current_state = GameState(
            game_id=game_id,
            game_over=False,
            achievements=[],
            dialog_history=[],
            threat_level=7,
            stage=GameStage.INITIAL_CONFRONTATION,
        )
        logger.info(f"Created new game session: {game_id}")
        return game_id

    def process_recording(self, recording_result: RecordingResult) -> GameResponse:
        """
        Process the recording and send the results to the LLM

        Args:
            recording_result: The result of the recording

        Returns:
            GameResponse: Response containing dialog, game state and achievements
        """
        try:
            if not self.current_state:
                logger.error(f"Game session not found")
                return GameResponse(
                    dialog="Error: Game session not found",
                    game_over=True,
                    ending_type=EndingType.ERROR,
                    achievements=[],
                )

            # Process the dialog input
            dialog_input = DialogInputDCL(recording_result.video_file)
            self.current_state.dialog_history.append(
                {"role": "user", "content": "\n".join(dialog_input.sentences)}
            )

            achievement_contexts = [
                AchievementContext(
                    id=ach_id, name=ach.name, description=ach.description, criteria=ach.criteria
                )
                for ach_id, ach in self.achievements.items()
                if ach_id not in self.current_state.achievements
            ]

            llm_result: LLMResponse = self.llm_client.generate_response(
                game_state=self.current_state,
                dialog_input=dialog_input,
                achievement_contexts=achievement_contexts,
            )

            # Update game state with LLM response
            self.current_state.stage = llm_result.stage
            self.current_state.threat_level = llm_result.threat_level
            self.current_state.game_over = llm_result.is_game_over
            self.current_state.dialog_history.append(
                {"role": "system", "content": llm_result.dialog}
            )

            # Process achievements from LLM response
            new_achievements = []
            if llm_result.achievements:
                new_achievements = llm_result.achievements
                for achievement_id in new_achievements:
                    if achievement_id not in self.current_state.achievements:
                        self.current_state.achievements.append(achievement_id)

            response = GameResponse(
                dialog=llm_result.dialog,
                game_over=llm_result.is_game_over,
                ending_type=llm_result.ending_type,
                achievements=new_achievements,
                next_scene=llm_result.stage,
                analysis=None,  # TODO: Add analysis only if game is over
            )

            return response
        except Exception as e:
            logger.error(f"Error processing recording: {e}")
            return GameResponse(
                dialog="Error: Failed to process recording",
                game_over=True,
                ending_type=EndingType.ERROR,
                achievements=[],
            )
