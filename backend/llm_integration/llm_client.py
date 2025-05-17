import json
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI

from models import (
    DialogInputDCL,
    GameStage,
    AchievementContext,
    GameState,
    LLMResponse,
)

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM APIs (e.g., OpenAI)"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM client

        Args:
            api_key: API key for the LLM service
            model: Model to use for generating responses
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url="https://proxy.merkulov.ai")
        self.model = model

        logger.info(f"LLM client initialized with model {model}")

    def generate_response(
        self,
        game_state: GameState,
        dialog_input: DialogInputDCL,
        achievement_contexts: Optional[List[AchievementContext]] = None,
    ) -> LLMResponse:
        """
        Generate a game response based on the current state and user inputs

        Args:
            game_state: Current game state including scenario and history
            achievement_contexts: List of available achievements that can be unlocked

        Returns:
            Response containing dialog and game state updates
        """
        try:
            context = self._build_context(game_state, dialog_input, achievement_contexts)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": json.dumps(context)},
                ],
                functions=[
                    {
                        "name": "generate_response",
                        "description": "Generate the thug's next response and update the game state",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "dialog": {
                                    "type": "string",
                                    "description": "The thug's next line of dialog",
                                },
                                "internal_state": {
                                    "type": "object",
                                    "properties": {
                                        "threat_level": {
                                            "type": "number",
                                            "description": "Current threat level (0-10)",
                                        },
                                        "stage": {
                                            "type": "string",
                                            "description": "Current stage of the confrontation",
                                            "enum": [
                                                GameStage.INITIAL_CONFRONTATION.value,
                                                GameStage.ESCALATING.value,
                                                GameStage.NEGOTIATING.value,
                                                GameStage.DE_ESCALATING.value,
                                                GameStage.FINAL_CONFRONTATION.value,
                                                GameStage.RESOLUTION.value,
                                            ],
                                        },
                                    },
                                },
                                "game_status": {
                                    "type": "object",
                                    "properties": {
                                        "continue": {
                                            "type": "boolean",
                                            "description": "Whether the game should continue",
                                        },
                                        "ending_type": {
                                            "type": "string",
                                            "enum": ["success", "failure", None],
                                            "description": "Type of ending if game is over",
                                        },
                                    },
                                },
                                "achievements": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "description": "List of achievement IDs that should be unlocked based on user's response",
                                },
                            },
                            "required": ["dialog", "internal_state", "game_status"],
                        },
                    }
                ],
                function_call={"name": "generate_response"},
                temperature=0.7,
            )

            function_call = response.choices[0].message.function_call

            if function_call and function_call.name == "generate_response":
                result = json.loads(function_call.arguments)
                logger.info(f"Generated response: {result['dialog'][:50]}...")
                return LLMResponse(
                    dialog=result["dialog"],
                    internal_state=result["internal_state"],
                    game_status=result["game_status"],
                    achievements=result.get("achievements", None),
                )
            else:
                logger.warning("Function calling failed, using fallback")
                return LLMResponse(
                    dialog="What do you want? Just give me your purse and nobody gets hurt.",
                    internal_state={
                        "threat_level": 7,
                        "stage": GameStage.INITIAL_CONFRONTATION.value,
                    },
                    game_status={"continue": True, "ending_type": None},
                    achievements=[],
                )

        except Exception as e:
            logger.error(f"Error in LLM API call: {str(e)}")
            return LLMResponse(
                dialog="Hey, I'm talking to you! Hand over the purse now!",
                internal_state={
                    "threat_level": 8,
                    "stage": GameStage.ESCALATING.value,
                },
                game_status={"continue": True, "ending_type": None},
                achievements=[],
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """
        You are the AI controlling a thug character in an interactive emotion-based scenario. The user is walking at night and you (the thug) want to steal their purse. The user needs to convince you not to do so by acting confidently and speaking appropriately.

        Your role:
        1. Generate realistic dialog for the thug character
        2. Update the threat level (0-10) based on the user's emotions and responses
        3. Track the stage of the confrontation
        4. Decide when the scenario should end
        5. Award achievements when appropriate based on the user's actions and words

        Guidelines for threat level:
        - If the user shows confidence (detected emotions show high confidence value), gradually reduce threat level
        - If the user shows nervousness or fear (detected emotions show low confidence value), gradually increase threat level
        - If the user says something calming or de-escalating, reduce the threat level
        - If the user says something provocative or threatening, increase the threat level sharply
        - End with SUCCESS if threat level goes below 3 (thug gives up and leaves)
        - End with FAILURE if threat level reaches 10 (thug takes the purse)

        Stages of confrontation:
        - initial_confrontation: First encounter, thug demands the purse
        - escalating: Thug becomes more threatening
        - negotiating: User is trying to negotiate
        - de_escalating: Tension is reducing
        - final_confrontation: Final decision point
        - resolution: Ending (success or failure)

        Achievement Guidelines:
        - You will receive a list of available achievements that can be unlocked
        - Each achievement has an id, name, description, and criteria
        - Carefully analyze the user's speech and emotions to determine if they've met any achievement criteria
        - Only award achievements that make sense based on the current context and user's behavior
        - Include the achievement IDs in your response when criteria are met
        - Do not award achievements that have already been earned (they won't be in the available list)

        Keep dialog realistic for a confrontation scenario. Never break character or acknowledge this is a game.

        The function must return a JSON with this exact structure:
        {
          "dialog": "The thug's next line of dialog text",
          "internal_state": {
            "threat_level": 5,  // A number from 0-10
            "stage": "initial_confrontation"  // One of the stages listed above
          },
          "game_status": {
            "continue": true,  // True if game should continue, false if it should end
            "ending_type": null  // "success", "failure", or null if game continues
          },
          "achievements": ["achievement_id1", "achievement_id2"]  // IDs of unlocked achievements, or empty array
        }
        """

    def _build_context(
        self,
        game_state: GameState,
        dialog_input: DialogInputDCL,
        achievement_contexts: Optional[List[AchievementContext]] = None,
    ) -> Dict[str, Any]:
        """Build the context object for the LLM API call"""

        dialog_history = []
        for emotion, sentence in zip(dialog_input.emotions, dialog_input.sentences):
            dialog_history.append(
                {
                    "content": sentence,
                    "emotions": emotion,
                }
            )

        context = {
            "current_state": {
                "threat_level": game_state.threat_level,
                "stage": game_state.stage.value,
                "dialog_history": dialog_history,
            },
            "user_input": {
                "emotions": dialog_input.emotions,
                "sentences": dialog_input.sentences,
            },
        }

        if achievement_contexts:
            context["available_achievements"] = [
                {
                    "id": ach.id,
                    "name": ach.name,
                    "description": ach.description,
                    "criteria": ach.criteria,
                }
                for ach in achievement_contexts
            ]

        return context
