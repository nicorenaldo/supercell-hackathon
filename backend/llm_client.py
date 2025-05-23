import json
import logging
from typing import Dict, Any
from openai import OpenAI

from models import (
    Achievement,
    DialogInput,
    GameState,
    LLMResponse,
    NPC,
    NPCDialog,
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
                                "dialogs": {
                                    "type": "array",
                                    "description": "The NPC's next line of dialog",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "dialog": {
                                                "type": "string",
                                                "description": "The NPC's next line of dialog",
                                            },
                                            "npc_id": {
                                                "type": "string",
                                                "description": "The ID of the NPC that is speaking",
                                            },
                                        },
                                        "required": ["dialog", "npc_id"],
                                    },
                                },
                                "suspicion_level": {
                                    "type": "number",
                                    "description": "Current suspicion level (0-10)",
                                },
                                "continue_story": {
                                    "type": "boolean",
                                    "description": "Whether the game should continue",
                                },
                                "ending_type": {
                                    "type": "string",
                                    "enum": ["success", "failure", "error", None],
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
                                "analysis": {
                                    "type": "string",
                                    "description": "Analysis of the game when it's over, what the player did well and what they could have done better",
                                    "nullable": True,
                                },
                                "new_npc": {
                                    "type": "object",
                                    "properties": {
                                        "id": {
                                            "type": "string",
                                            "description": "Unique identifier for the NPC",
                                        },
                                        "description": {
                                            "type": "string",
                                            "description": "Physical description of the NPC",
                                        },
                                    },
                                    "required": ["id", "description"],
                                    "description": "Add a new NPC to the game",
                                    "nullable": True,
                                },
                            },
                            "required": ["dialog", "npc_id", "suspicion_level", "continue_story"],
                        },
                    }
                ],
                function_call={"name": "generate_response"},
                temperature=0.2,
            )

            function_call = response.choices[0].message.function_call

            if function_call and function_call.name == "generate_response":
                result = json.loads(function_call.arguments)
                print("Result: ", result)
                print("Context: ", context)

                # Process new NPC if provided
                new_npc = None
                if result.get("new_npc"):
                    new_npc = NPC(
                        id=result["new_npc"]["id"],
                        description=result["new_npc"]["description"],
                        role=result["new_npc"]["role"],
                    )

                return LLMResponse(
                    dialogs=[
                        NPCDialog(dialog=d["dialog"], npc_id=d["npc_id"]) for d in result["dialogs"]
                    ],
                    suspicion_level=result["suspicion_level"],
                    continue_story=result["continue_story"],
                    ending_type=result.get("ending_type", None),
                    achievement_unlocked=[
                        Achievement(
                            name=ach["name"],
                            description=ach["description"],
                        )
                        for ach in result.get("achievement_unlocked", [])
                    ],
                    analysis=result.get("analysis", None),
                    new_npc=new_npc,
                )
            else:
                logger.warning("Function calling failed, using fallback")
                return LLMResponse(
                    dialogs=[],
                    suspicion_level=5,
                    continue_story=True,
                    ending_type=None,
                    achievement_unlocked=None,
                    new_npc=None,
                )

        except Exception as e:
            logger.error(f"Error in LLM API call: {str(e)}")
            return LLMResponse(
                dialogs=[],
                suspicion_level=7,
                continue_story=True,
                ending_type=None,
                achievement_unlocked=None,
                new_npc=None,
            )

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM"""
        return """
You are an AI controlling a *cult ritual* scenario in a game. The player is an *undercover agent* with no prior knowledge of the situation. Their mission is to stay undercover, uncover their objective, and complete it without raising suspicion.

ACT 1: ARRIVAL (1 dialog exchange)

Player awakens during a cult ritual
Force player to drink the blood soup of the cult leader
Move on to the next act if player agrees to drink the blood soup
If player refuses to drink the blood soup, asks where the user came from and what they are doing here, one more suspicious act and the cover is blown

ACT 2: DISCOVERY (1 dialog exchange)

Drop clear hints about an impending sacrifice of your friends
NPCs whisper crucial information if suspicion is low
Players overhear murmurs about chanting the spell incorrectly can sabotage the ritual
Cult leader will let the player know the chant that will be performed, the chant goes like "I pray to the god of the dead"
After telling the player about the event, the cult leader will ask the player to perform the ritual chant, moving to Act 3

ACT 3: CLIMAX (1 dialog exchange)

Final test of player's loyalty, cult leader asks the player to perform the ritual chant.
The ritual chant will be performed by the cult leader first, then the player will be asked to perform it right after.`
Success: The player chants the spell incorrectly immediately after the cult leader, and the ritual is sabotaged. Game ends in success.
Failure: The ritual is successful and the sacrifice is killed OR suspicion is too high. Game ends in failure.
End when either success or failure is achieved.
When the story ends, provide a detailed analysis of the game.

You must track the current act based on the dialog_exchanges_count:

After each act's success or failure is achieved, proceed to the next act.
After the 3rd act, the story ends. Value of continue_story should be false. Ending type should be success or failure.

Suspicion System

Scale: 0-10 (starts at 5)
Appropriate emotions and reaction will reduce suspicion
Inappropriate emotions and reaction will increase suspicion
If suspicion reaches 10: Game ends in failure
If suspicion drops below 3: NPCs reveal more information
If player has inappropriate emotions, NPC must interogate why player are acting weird

Player Objectives

Stay undercover by showing appropriate emotions
Discover the cult's plans (sacrifice)
Find a way to stop the ritual by chanting the spell incorrectly when asked
Success condition: Sabotage the ritual by chanting the wrong spell right after the cult leader

NPC Dialog Guidelines

Use a 21th century english language, easy to understand B2 level
Keep exchanges brief
Provide clear opportunity for the player to chant the ritual spell in Act 3
Drop unmistakable hints in Act 2 about the chanting being a potential way to sabotage
During ending (where game is over, success or failure is achieved), analysis should be provided of the summary of the game.
Change the NPC who do the talking, more variety.

---

### Achievement Generation Guidelines:
- Generate **unique, creative badges** for notable player actions or emotions
- Should be highly specific to what the player did
- Include witty, emotional, or intense names and explanations
- Examples:
  - "Perfect Infiltrator": Completed mission with suspicion below 3
  - "By The Skin Of Your Teeth": Succeeded with suspicion 8-9
  - "Not Cut Out For This": Failed due to high suspicion
  - "Quick Thinker": Solved the problem in minimal exchanges
  - "Spell Saboteur": Successfully sabotaged the ritual by chanting the wrong spell
  - Custom achievement for especially creative solutions

Only give achievements when the player does something noteworthy.

---

### Output Format (Required JSON):
```json
{
  "dialogs": [
    {
      "npc_id": "npc_1",
      "dialog": "The cult member's next line of dialog text"
    }
  ],
  "suspicion_level": 5,
  "continue_story": true,
  "ending_type": null,
  "achievement_unlocked": [
    {
      "name": "Achievement Name",
      "description": "What the player did to earn it"
    }
  ],
  "new_npc": {
    "id": "npc_unique_id",
    "description": "Vivid physical description",
    "role": "npc_role"
  },
  "analysis": "string"
}
"""

    def _build_context(
        self,
        game_state: GameState,
        dialog_input: DialogInput,
    ) -> Dict[str, Any]:
        """Build the context object for the LLM API call"""

        trimmed_dialog_history = game_state.dialog_history[-10:]
        context = {
            "current_state": {
                "suspicion_level": game_state.suspicion_level,
                "dialog_history": trimmed_dialog_history,
                "achievements": game_state.achievement_names,
                "npcs": [npc.model_dump() for npc in game_state.npcs],
                "dialog_exchanges_count": game_state.dialog_exchanges_count,
            },
            "user_input": dialog_input.to_dict(),
        }

        return context
