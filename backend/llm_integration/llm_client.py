import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    """Client for interacting with LLM APIs (e.g., OpenAI)"""

    def __init__(self, api_key: str):
        """
        Initialize the LLM client

        Args:
            api_key: API key for the LLM service
        """
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key, base_url="https://proxy.merkulov.ai")
        self.model = "gpt-4o-mini"

        logger.info("LLM client initialized")

    def generate_response(
        self,
        game_state: Dict[str, Any],
        emotion_data: Optional[Dict[str, Any]] = None,
        speech_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generate a game response based on the current state and user inputs

        Args:
            game_state: Current game state including scenario and history
            emotion_data: Detected emotion data
            speech_data: Recognized speech data

        Returns:
            Response containing dialog and game state updates
        """
        try:
            # Create the context for the LLM
            context = self._build_context(game_state, emotion_data, speech_data)

            # Call the LLM API
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
                            },
                            "required": ["dialog", "internal_state", "game_status"],
                        },
                    }
                ],
                function_call={"name": "generate_response"},
                temperature=0.7,
            )

            # Extract the function call from the response
            function_call = response.choices[0].message.function_call

            if function_call and function_call.name == "generate_response":
                result = json.loads(function_call.arguments)
                logger.info(f"Generated response: {result['dialog'][:50]}...")
                return result
            else:
                # Fallback in case function calling fails
                logger.warning("Function calling failed, using fallback")
                return {
                    "dialog": "What do you want? Just give me your purse and nobody gets hurt.",
                    "internal_state": {"threat_level": 7, "stage": "initial_confrontation"},
                    "game_status": {"continue": True, "ending_type": None},
                }

        except Exception as e:
            logger.error(f"Error in LLM API call: {str(e)}")
            # Return a fallback response
            return {
                "dialog": "Hey, I'm talking to you! Hand over the purse now!",
                "internal_state": {"threat_level": 8, "stage": "escalating"},
                "game_status": {"continue": True, "ending_type": None},
            }

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """
        You are the AI controlling a thug character in an interactive scenario. The user is walking at night and you (the thug) want to steal their purse. The user needs to convince you not to do so by acting confidently and speaking appropriately.

        Your role:
        1. Generate realistic dialog for the thug character
        2. Update the threat level (0-10) based on the user's emotions and responses
        3. Decide when the scenario should end

        Guidelines:
        - If the user shows confidence, gradually reduce the threat level
        - If the user shows nervousness or fear, gradually increase the threat level
        - If the user says something calming or de-escalating, reduce the threat level
        - If the user says something provocative or threatening, increase the threat level sharply
        - End with SUCCESS if threat level goes below 3 (thug gives up and leaves)
        - End with FAILURE if threat level reaches 10 (thug takes the purse)
        - Keep dialog realistic for a confrontation scenario
        - Never break character or acknowledge this is a game

        The function you'll use returns:
        1. The thug's next line of dialog
        2. Updated internal_state (threat_level and stage)
        3. game_status (whether to continue or end with success/failure)
        """

    def _build_context(
        self,
        game_state: Dict[str, Any],
        emotion_data: Optional[Dict[str, Any]] = None,
        speech_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build the context object for the LLM API call"""

        context = {"scenario": "night_encounter", "current_state": game_state, "user_input": {}}

        if emotion_data:
            context["user_input"]["emotion"] = emotion_data

        if speech_data:
            context["user_input"]["speech"] = speech_data

        return context
