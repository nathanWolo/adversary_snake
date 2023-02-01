import os
import random
import json
import cherrypy
import snakebrain
"""
This is a simple Battlesnake server written in Python.
For instructions see https://github.com/BattlesnakeOfficial/starter-snake-python/README.md
"""


class Battlesnake(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def index(self):
        # This function is called when you register your Battlesnake on play.battlesnake.com
        # It controls your Battlesnake appearance and author permissions.
        # TIP: If you open your Battlesnake URL in browser you should see this data
        return {
            "apiversion": "1",
            "author": "nathanWolo",  # TODO: Your Battlesnake Username
            "color": "#005590",  # TODO: Personalize
            "head": "default",  # TODO: Personalize
            "tail": "default",  # TODO: Personalize
        }

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def start(self):
        # This function is called everytime your snake is entered into a game.
        # cherrypy.request.json contains information about the game that's about to be played.
        data = cherrypy.request.json
        self.turn = data["turn"]
        self.game_id = data["game"]["id"]
        print("START")
        return "ok"

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def move(self):
        # This function is called on every turn of a game. It's how your snake decides where to move.
        # Valid moves are "up", "down", "left", or "right".
        # TODO: Use the information in cherrypy.request.json to decide your next move.
        data = cherrypy.request.json
        dodge_food = False #set to false for competition play. set to true for survival challenges
        self.turn = data["turn"]
        self.game_id = data["game"]["id"]
        board = data["board"]
        turn = data["turn"]
        board = data['board']
        food = board["food"]
        health = int(data["you"]["health"])
        # Choose a random direction to move in
        possible_moves = ["up", "down", "left", "right"]
        move = random.choice(possible_moves)
        safe_moves = snakebrain.get_safe_moves(data, data["you"])
        print("safe moves", safe_moves)
        if dodge_food and len(safe_moves) > 1 and health > 10:
          safe_moves = snakebrain.prune_food(data, safe_moves, food)
        move = snakebrain.prune_safe_moves(data, safe_moves)
        print('------PRUNING--------')
        print(move)
        # except IndexError:
        #   print("forced random")
        #   random.shuffle(possible_moves)
        #   for m in possible_moves:
        #     if snakebrain.avoid_self(body, snakebrain.string_to_move(m, body[0])) and snakebrain.avoid_walls(snakebrain.string_to_move(m,body[0]), board["width"], board["height"]):
        #       move = m
        print(f"TURN: {turn}, MOVE: {move}")
        return {"move": move}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def end(self):
        # This function is called when a game your snake was in ends.
        # It's purely for informational purposes, you don't have to make any decisions here.
        data = cherrypy.request.json

        print("END")
        return "ok"


if __name__ == "__main__":
    server = Battlesnake()
    cherrypy.config.update({"server.socket_host": "0.0.0.0"})
    cherrypy.config.update(
        {"server.socket_port": int(os.environ.get("PORT", "8080")),}
    )
    print("Starting Battlesnake Server...")
    cherrypy.quickstart(server)
