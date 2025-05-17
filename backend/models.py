from pydantic import BaseModel


# TODO: Add more fields for achievement, game state (game over or not)
class GameResponse(BaseModel):
    dialog: str
