import re

from pydantic import BaseModel
from database import session as db
from fastapi import HTTPException

from api.app import getApp
from misc.functions import generate_game_code

from models.game_model import Game

app = getApp()

#
#   Returns an array with all the stored games if there are no parameters given
#   or returns an array with all the games filtered by the arguments
#

@app.get("/games")
async def list_games(page: int = 1, page_size: int = 10):
    games = db.getSession().query(Game).offset((page - 1) * page_size).limit(page_size).all()
    return games

#
#   Creates a game and returns the created game ID and the join code
#   Requires a player name (3-16 characters)
#
class CreateGame(BaseModel):
    player1_name: str
    
@app.post("/game/create")
async def create_game(request: CreateGame):
    if len(request.player1_name) < 3 or len(request.player1_name) > 16:
        raise HTTPException(status_code=400, detail="Player name should be between 3 and 16 characters long.")
        
    pattern = r"^[a-zA-Z0-9_.]+$"
    if not re.match(pattern, request.player1_name):
        raise HTTPException(status_code=400, detail="Player name should contain only letters, number and special characters ('.' and '_')")

    session = db.getSession()

    code = generate_game_code()
    game = Game(
        code=code,
        player1_name=request.player1_name,
        player1_score=0,
        game_state="waiting",
        current_round=0
    )

    session.add(game)
    session.commit()
    session.refresh(game)

    return {"game_id": game.id, "code": game.code}

#
#   Gets data for a specific game by their ID
#

@app.get("/game/{game_id}")
async def get_game(game_id: str):
    game = db.getSession().query(Game).filter(Game.id == game_id).first()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found.")

    return game

#
#   The method that allows the second player to join a lobby
#   Requires the join code and a player name
#

class JoinGame(BaseModel):
    code: str
    player_name: str

@app.post("/game/join")
async def join_game(request: JoinGame):
    if len(request.player_name) < 3 or len(request.player_name) > 16:
        raise HTTPException(status_code=400, detail="Player name should be between 3 and 16 characters long.")
        
    pattern = r"^[a-zA-Z0-9_.]+$"
    if not re.match(pattern, request.player_name):
        raise HTTPException(status_code=400, detail="Player name should contain only letters, number and special characters ('.' and '_')")

    session = db.getSession()
    game = session.query(Game).filter(Game.code == request.code).first()

    if game.game_state != "waiting":
        raise HTTPException(status_code=403, detail="Game is already active!")

    # Updates the game with these values
    game.player2_name = request.player_name
    game.player2_score = 0
    game.game_state = "active"
    game.current_round = 1

    session.commit() # Commits the changes to the database
    session.refresh(game) # Updates the game
    
    return {
        "game_id": game.id,
        "player2_name": game.player2_name,
        "game_state": game.game_state,
    }