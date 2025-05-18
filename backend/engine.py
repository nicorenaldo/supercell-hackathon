from typing import Optional, Tuple, Dict
import uuid
import logging
import time

from video_processor import VideoProcessor
from models import (
    NPC,
    Achievement,
    EndingType,
    GameResponse,
    GameState,
    LLMResponse,
)
from recording import RecordingResult
from llm_client import LLMClient

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

        # Dictionary to store all active game sessions
        self.game_sessions: Dict[str, GameState] = {}

        logger.info("Game engine initialized")

    def get_game_state(self, game_id: str) -> Optional[GameState]:
        """Get the game state for a specific game ID"""
        return self.game_sessions.get(game_id)

    def create_new_game(self) -> Tuple[str, str]:
        """
        Create a new game session

        Returns:
            game_id: Unique identifier for the new game session
            initial_dialog: Initial dialog for the new game session
        """
        game_id = str(uuid.uuid4())

        initial_dialog = (
            "Welcome to the initiation, quickly! You need to drink the blood of the cult leader!"
        )

        game_state = GameState(
            game_id=game_id,
            game_over=False,
            achievements=[],
            dialog_history=[
                {"role": "system", "content": initial_dialog, "npc_id": "npc_cult_leader"},
            ],
            npcs=[
                NPC(
                    id="npc_cult_leader",
                    description="Disembodied voice leading the initiation. Deep, slow, commanding.",
                    role="Tutorial narrator / cult leader",
                ),
                NPC(
                    id="npc_sara",
                    description="A quiet, hooded woman who watches you closely. Seems to judge silently.",
                    role="Suspicion mechanic trigger",
                ),
                NPC(
                    id="npc_elen",
                    description="Nervous new recruit, friendly and unsure.",
                    role="Emotion/ally interaction",
                ),
                NPC(
                    id="npc_alex",
                    description="Masked, silent enforcer who blocks exits and watches movements.",
                    role="Adds tension, responds to suspicion",
                ),
            ],
            suspicion_level=5,
        )

        # Store the new game session
        self.game_sessions[game_id] = game_state

        logger.info(f"Created new game session: {game_id}")
        return game_id, initial_dialog

    def process_recording(self, recording_result: RecordingResult, game_id: str) -> GameResponse:
        """
        Process the recording and send the results to the LLM

        Args:
            recording_result: The result of the recording
            game_id: The ID of the game session to update

        Returns:
            GameResponse: Response containing dialog, game state and achievements
        """
        try:
            game_state = self.get_game_state(game_id)

            if not game_state:
                logger.error(f"Game session not found: {game_id}")
                return GameResponse(
                    dialogs=[],
                    suspicion_level=0,
                    game_over=True,
                    ending_type=EndingType.ERROR,
                    achievements=[],
                    analysis=f"Error: Game session {game_id} not found",
                )

            # Process the video
            dialog_input = self.video_processor.process_video(recording_result.file_path)
            game_state.dialog_history.append(
                {"role": "user", "content": "\n".join(dialog_input.sentences)}
            )

            # Increment dialog exchange counter since user has spoken
            game_state.dialog_exchanges_count += 1

            llm_result: LLMResponse = self.llm_client.generate_response(
                game_state=game_state,
                dialog_input=dialog_input,
            )

            # Update game state with LLM response
            game_state.suspicion_level = llm_result.suspicion_level
            game_state.game_over = llm_result.is_game_over
            for dialog in llm_result.dialogs:
                game_state.dialog_history.append(
                    {
                        "role": "system",
                        "content": dialog.dialog,
                        "npc_id": dialog.npc_id,
                    }
                )

            # Add new NPC if provided by LLM
            if llm_result.new_npc:
                existing_npc_ids = [npc.id for npc in game_state.npcs]
                if llm_result.new_npc.id not in existing_npc_ids:
                    game_state.npcs.append(llm_result.new_npc)
                    logger.info(f"Added new NPC: {llm_result.new_npc.id}")

            # Process dynamic achievements from LLM response
            new_achievements = []
            if llm_result.achievement_unlocked:
                for ach in llm_result.achievement_unlocked:
                    new_ach = Achievement(
                        name=ach.name,
                        description=ach.description,
                    )
                    game_state.achievements.append(new_ach)
                    new_achievements.append(new_ach)

            # Clean up finished games after a while to prevent memory leaks
            if game_state.game_over:
                # In a real implementation, you might want to schedule this for later
                # or use a separate cleanup routine that runs periodically
                logger.info(f"Game {game_id} is over, will be removed from active sessions soon")

            response = GameResponse(
                dialogs=llm_result.dialogs,
                suspicion_level=llm_result.suspicion_level,
                game_over=llm_result.is_game_over,
                ending_type=llm_result.ending_type,
                achievements=new_achievements,
                analysis=llm_result.analysis,
            )

            return response
        except Exception as e:
            logger.error(f"Error processing recording for game {game_id}: {e}")
            return GameResponse(
                dialogs=[],
                suspicion_level=0,
                game_over=True,
                ending_type=EndingType.ERROR,
                achievements=[],
                analysis=str(e),
            )
