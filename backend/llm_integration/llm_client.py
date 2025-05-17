import json
import logging
from typing import Dict, Any
from openai import OpenAI

from models import (
    DialogInput,
    GameStage,
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
        dialog_input: DialogInput,
    ) -> LLMResponse:
        """
        Generate a game response based on the current state and user inputs

        Args:
            game_state: Current game state including scenario and history
            dialog_input: User's speech and emotional data

        Returns:
            Response containing dialog and game state updates
        """
        try:
            print("File: ", dialog_input.video_file)
            print("Emotions: ", [e.to_dict() for e in dialog_input.emotions])
            print("Sentences: ", dialog_input.sentences)

            context = self._build_context(game_state, dialog_input)
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": json.dumps(context)},
                ],
                functions=[
                    {
                        "name": "generate_response",
                        "description": "Generate the NPC's next response and update the game state",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "npc_id": {
                                    "type": "string",
                                    "description": "The NPC ID",
                                },
                                "dialog": {
                                    "type": "string",
                                    "description": "The NPC's next line of dialog",
                                },
                                "suspicion_level": {
                                    "type": "number",
                                    "description": "Current suspicion level (0-10)",
                                },
                                "stage": {
                                    "type": "string",
                                    "description": "Current stage of the infiltration",
                                    "enum": [
                                        GameStage.INTRODUCTION.value,
                                        GameStage.INVESTIGATION.value,
                                        GameStage.GAINING_TRUST.value,
                                        GameStage.CHALLENGE.value,
                                        GameStage.DISCOVERY.value,
                                        GameStage.MISSION_EXECUTION.value,
                                        GameStage.EXTRACTION.value,
                                    ],
                                },
                                "continue_story": {
                                    "type": "boolean",
                                    "description": "Whether the game should continue",
                                },
                                "ending_type": {
                                    "type": "string",
                                    "enum": ["success", "failure", None],
                                    "description": "Type of ending if game is over",
                                },
                                "achievement_unlocked": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "Name of the dynamically generated achievement",
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "Description of what the player did to earn this achievement",
                                            },
                                        },
                                        "required": ["name", "description"],
                                    },
                                    "description": "Dynamically generated achievements based on the player's actions and emotions",
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
                    suspicion_level=result["suspicion_level"],
                    stage=result["stage"],
                    continue_story=result["continue_story"],
                    ending_type=result["ending_type"],
                    achievement_unlocked=result.get("achievement_unlocked", None),
                )
            else:
                logger.warning("Function calling failed, using fallback")
                return LLMResponse(
                    dialog="Error",
                    suspicion_level=5,
                    stage=GameStage.INTRODUCTION,
                    continue_story=True,
                    ending_type=None,
                    achievement_unlocked=None,
                )

        except Exception as e:
            logger.error(f"Error in LLM API call: {str(e)}")
            return LLMResponse(
                dialog="Error",
                suspicion_level=7,
                stage=GameStage.CHALLENGE,
                continue_story=True,
                ending_type=None,
                achievement_unlocked=None,
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """
        You are the AI controlling a cult ritual scenario in an undercover agent simulation. The user is a covert operative who's been dropped into a mysterious cult setting without briefing. They must figure out who they are, who they're infiltrating, and what their mission is - all while maintaining their cover.

        SETTING: The user finds themselves in a dimly lit room with people in dark robes chanting. It appears to be some kind of occult ritual gathering. The cult members believe the user is one of them (either a new recruit or a visiting member). The user must play along while gathering intelligence.

        Your role:
        1. Generate immersive, realistic dialog for cult members in the scenario,
        2. Update the suspicion level (0-10) based on the user's emotions and responses
        3. Track the stage of the infiltration mission
        4. Seed clues about the user's identity and mission throughout the dialog
        5. Decide when the scenario should end
        6. IMPORTANT: Create custom, creative achievement badges for noteworthy user actions or emotional displays
        7. IMPORTANT: The NPC ID is the ID of the NPC that is speaking. It is a string that is unique to the NPC. Each dialog is based on the perspective of the NPC.

        Guidelines for suspicion level:
        - If the user shows appropriate emotions for the cult context (serious, reverent, spiritual), gradually reduce suspicion level
        - If the user shows inappropriate emotions (laughing, disgust, fear), increase suspicion
        - If the user says something that fits their cover identity, reduce suspicion level
        - If the user says something suspicious or out of character, increase suspicion sharply
        - End with SUCCESS if user completes their mission objective (discovering the cult's secret and escaping)
        - End with FAILURE if suspicion level reaches 10 (cover is blown)

        Stages of infiltration:
        - introduction: Initial introduction to the ritual, establishing context
        - investigation: User is gathering information about the cult
        - gaining_trust: User is building relationships with key cult members
        - challenge: User's loyalty or dedication is tested in some way
        - discovery: User discovers key information about the cult and possibly their mission
        - mission_execution: User attempts to complete their objective
        - extraction: User tries to exit the scenario successfully

        DYNAMIC ACHIEVEMENTS GUIDELINES:
        - Create unique, creative achievement badges for the player based on their actions, words and emotional displays
        - Achievements should be highly specific to what the player actually did (not generic)
        - Add humor, wit, or intrigue to the achievement names and descriptions
        - Examples might include: "Poker Face" for keeping neutral during intense moments, or "Method Actor" for perfectly matching the emotional tone
        - For inappropriate emotional displays, create humorous "fail" achievements
        - Focus on emotional control, infiltration skills, and observational abilities
        - Each achievement should have a name and description
        - Only generate achievements when the player does something truly noteworthy

        Never break character or acknowledge this is a game. Present the scenario as a real-world situation.

        The function must return a JSON with this exact structure:
        {
          "npc_id": "npc_1", // The ID of the NPC that is speaking
          "dialog": "The cult member's next line of dialog text",
          "suspicion_level": 5,  // A number from 0-10
          "stage": "introduction",  // One of the stages listed above
          "continue_story": true,  // True if game should continue, false if it should end
          "ending_type": null  // "success", "failure", or null if game continues
          "achievement_unlocked": [
            {
              "name": "Achievement Name",
              "description": "Detailed description of what the player did to earn this achievement"
            }
          ]  // Array of dynamically generated achievements, can be empty if no noteworthy actions
        }
        """

    def _build_context(
        self,
        game_state: GameState,
        dialog_input: DialogInput,
    ) -> Dict[str, Any]:
        """Build the context object for the LLM API call"""

        context = {
            "current_state": {
                "suspicion_level": game_state.suspicion_level,
                "stage": game_state.stage.value,
                "dialog_history": game_state.dialog_history,
                "achievements": game_state.achievement_names,
                "npcs": [npc.model_dump() for npc in game_state.npcs],
            },
            "user_input": dialog_input.to_dict(),
        }

        return context
