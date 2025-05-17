from typing import Optional, Tuple
import uuid
import logging
import time

from video_processor import VideoProcessor
from models import (
    NPC,
    Achievement,
    EndingType,
    GameResponse,
    GameStage,
    GameState,
    LLMResponse,
)
from recording_manager.manager import RecordingResult
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
        video_processor: VideoProcessor,
    ):
        """
        Initialize the game engine

        Args:
            llm_client: Client for communicating with the LLM API
            video_processor: Processor for analyzing video recordings
        """
        self.llm_client = llm_client
        self.video_processor = video_processor

        self.current_state: Optional[GameState] = None

        logger.info("Game engine initialized")

    @property
    def current_game_id(self) -> Optional[str]:
        return self.current_state.game_id if self.current_state else None

    def create_new_game(self) -> Tuple[str, str]:
        """
        Create a new game session

        Returns:
            game_id: Unique identifier for the new game session
        """
        game_id = str(uuid.uuid4())

        initial_dialog = "Welcome to the cult, who is your name young padawan."
        self.current_state = GameState(
            game_id=game_id,
            game_over=False,
            achievements=[],
            dialog_history=[
                {"role": "npc_cult_leader", "content": initial_dialog},
            ],
            npcs=[
                NPC(
                    id="npc_cult_leader",
                    description="The cult leader, a tall figure with a hooded cloak. They are wearing a mask of a demonic face.",
                ),
                NPC(
                    id="npc_cult_member",
                    description="A cult member, a short figure with a hooded cloak. They are wearing a mask of a demonic face.",
                ),
            ],
            suspicion_level=5,
            stage=GameStage.INTRODUCTION,
        )
        logger.info(f"Created new game session: {game_id}")
        return game_id, initial_dialog

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

            # Process the video
            dialog_input = self.video_processor.process_video(recording_result.file_path)
            self.current_state.dialog_history.append(
                {"role": "user", "content": "\n".join(dialog_input.sentences)}
            )

            llm_result: LLMResponse = self.llm_client.generate_response(
                game_state=self.current_state,
                dialog_input=dialog_input,
            )

            # Update game state with LLM response
            self.current_state.stage = llm_result.stage
            self.current_state.suspicion_level = llm_result.suspicion_level
            self.current_state.game_over = llm_result.is_game_over
            self.current_state.dialog_history.append(
                {
                    "role": "system",
                    "content": llm_result.dialog,
                    "npc_id": llm_result.npc_id,
                }
            )

            # Process dynamic achievements from LLM response
            new_achievements = []
            if llm_result.achievement_unlocked:
                for ach in llm_result.achievement_unlocked:
                    new_ach = Achievement(
                        name=ach.name,
                        description=ach.description,
                    )
                    self.current_state.achievements.append(new_ach)
                    new_achievements.append(new_ach)

            response = GameResponse(
                dialog=llm_result.dialog,
                npc_id=llm_result.npc_id,
                suspicion_level=llm_result.suspicion_level,
                game_over=llm_result.is_game_over,
                ending_type=llm_result.ending_type,
                achievements=new_achievements,
                analysis=llm_result.analysis,
            )

            return response
        except Exception as e:
            logger.error(f"Error processing recording: {e}")
            return GameResponse(
                dialog="Error: Failed to process recording",
                npc_id="error",
                suspicion_level=0,
                game_over=True,
                ending_type=EndingType.ERROR,
                achievements=[],
                analysis=str(e),
            )
