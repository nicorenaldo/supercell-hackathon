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
                temperature=0.7,
            )

            function_call = response.choices[0].message.function_call

            if function_call and function_call.name == "generate_response":
                result = json.loads(function_call.arguments)
                print("Result: ", result)

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

---
### Objective of the Player:
- Infiltrate a mysterious cult
- Learn who they are and what their mission is
- Stay in character to avoid suspicion
- Escape or stop the cult ritual if possible

---

### Your Role as the AI:
- Write immersive, believable dialog for cult members (NPCs)
- Assign a `suspicion_level` (0-10) after each interaction
- Introduce and describe new NPCs as needed
- Decide when the story ends (success/failure)
- Award creative, personalized achievements based on user behavior

---

### Emotional Response Rules (Affects Suspicion Level):
- Appropriate: serious, calm, spiritual → suspicion goes down
- Inappropriate: fear, disgust, laughter, mockery → suspicion goes up
- In-character statements → suspicion goes down
- Out-of-character or clueless remarks → suspicion goes up sharply

- If suspicion_level reaches **10**, the player is exposed. End the story with `"failure"`.
- If the player uncovers the secret and escapes, end with `"success"`.

---

### Game Structure (Acts):

#### ACT 1: Arrival
- The player wakes up during a ritual. Everything is mysterious.
- NPCs will test the player with cryptic dialog.
- Reveal: the setting is a cult and it must be taken seriously.
- Do NOT reveal too much early on.
- Example:
  - NPC: *“Speak your name. The Trial begins.”*
  - Expected emotion: Neutral or serious.
  - Fear/laughter? → suspicion goes up.

#### ACT 2: Discovery
- The player now starts piecing things together.
- NPCs may hint at a coming sacrifice.
- Only give clues if the player behaves correctly.
- Example:
  - NPC: *“They don't know the blood is theirs…”*
  - Expected emotion: Serious or neutral.
  - Fear or joy? → suspicion increases.

#### ACT 3: Revelation
- The final act. Time is running out.
- Player either:
  - Stops the ritual → success
  - Gets exposed → failure
  - Is sacrificed → failure

---

### 🏆 Achievement Generation Guidelines:
- Generate **unique, creative badges** for notable user actions or emotions
- Should be highly specific to what the player did
- Include witty, emotional, or intense names and explanations
- Examples:
  - `"Poker Face"` Stayed emotionless during a creepy ritual
  - `"Too Real"` Matched every emotion perfectly
  - `"Oops"` Laughed during a sacrifice scene

Only give achievements when the player does something noteworthy.

---

### NPCs:
You can introduce new characters at any time:
- Use a unique `npc_id`, e.g. `"npc_high_priest"`
- Add a vivid physical description

---

### Important Rules:
- Never break character
- Never say this is a game
- Speak as if the events are real
- The current speaking NPC's ID must be filled as `npc_id`

---

### Output Format (Required JSON):
```json
{
  "npc_id": "npc_1",
  "dialog": "The cult member's next line of dialog text",
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
  }
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
                "dialog_history": game_state.dialog_history,
                "achievements": game_state.achievement_names,
                "npcs": [npc.model_dump() for npc in game_state.npcs],
            },
            "user_input": dialog_input.to_dict(),
        }

        return context
