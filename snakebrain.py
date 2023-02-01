import random


def get_all_moves(head):

    return [{
        'x': head['x'],
        'y': head['y'] + 1
    }, {
        'x': head['x'],
        'y': head['y'] - 1
    }, {
        'x': head['x'] + 1,
        'y': head['y']
    }, {
        'x': head['x'] - 1,
        'y': head['y']
    }]


#move testing functions return true if safe, false if unsafe
def get_safe_moves(data, snake):
    moves = get_all_moves(snake["head"])
    safe_moves = []
    return_string_list = []
    head = snake["head"]
    for move in moves:
        # print("move", move)
        # print("avoids walls", avoid_walls(move, data["board"]["width"], data["board"]["height"]))
        # print("avoids snakes", avoid_snakes(data, move))
        if avoid_walls(move, data["board"]["width"],
                       data["board"]["height"]) and avoid_snakes(data, move):
            safe_moves.append(move)
    for move in safe_moves:
        return_string_list.append(move_to_string(move, head))
    return return_string_list


def avoid_walls(future_head, board_width, board_height):
    safe = True
    x = int(future_head["x"])
    y = int(future_head["y"])
    if x < 0 or y < 0 or x >= board_width or y >= board_height:
        safe = False
    return safe


def avoid_snakes(data, future_head):
    for snake in data["board"]["snakes"]:
        if future_head in snake["body"][:-1]:
            return False
    return True


def shouldEat(data, move):
    m = string_to_move(move, data["you"]["head"])
    board = data["board"]
    for snake in board["snakes"]:
        potential = get_safe_moves(data, snake)
        if snake["id"] == data["you"]["id"]:
            continue
        if m in potential:
            if data["you"]["length"] <= snake["length"]:
               # print("shouldnt eat", move)
                return -3
            else:
                #print("should eat", move)
                return 3
    #print("no eat decision", move)
    return 0


def prune_safe_moves(data, moves):
    body = data["you"]["body"]
    board = data["board"]
    food = board["food"]
    random.shuffle(moves)
    safest = 0
    temp = 0
    safest_move = moves[0]
    head = data["you"]["head"]
    for move in moves:
        temp = get_safe_squares(
            data, simulate_next_move(body, string_to_move(move, head)))
        if isCorner(data, move):
            temp -= 1
        temp += shouldEat(data, move)
        if string_to_move(move, head) in food and temp > 1:
            temp += 2
        try:
            if string_to_move(move, head) in board["hazards"]:
                temp -= 1
        except:
            pass
        if data["you"]["health"] < 30 and seekFood(
                data, string_to_move(move, data["you"]["head"])) and temp > 1:
            temp += 2
        if temp > safest:
            safest = temp
            safest_move = move
    return safest_move


def simulate_next_move(body, move):
    sim_body = body
    #print("SIM BODY:", sim_body)
    for i in range(len(sim_body) - 1, 1, -1):
        sim_body[i] = sim_body[i - 1]
    if len(sim_body) > 0:
        sim_body[0] = move
    return sim_body


def get_safe_squares(data, sim_body):
    fake_data = data
    fake_data["you"]["body"] = sim_body[1:]
    fake_data["you"]["head"] = sim_body[0]
    return len(get_safe_moves(fake_data, fake_data["you"]))


def move_to_string(move, coord):
    up = {'x': coord['x'], 'y': coord['y'] + 1}
    down = {'x': coord['x'], 'y': coord['y'] - 1}
    right = {'x': coord['x'] + 1, 'y': coord['y']}
    if move == up:
        return "up"
    elif move == down:
        return "down"
    elif move == right:
        return "right"
    else:
        return "left"


def string_to_move(move, coord):
    if move == "up":
        return {'x': coord['x'], 'y': coord['y'] + 1}
    elif move == "down":
        return {'x': coord['x'], 'y': coord['y'] - 1}
    elif move == "right":
        return {'x': coord['x'] + 1, 'y': coord['y']}
    else:
        return {'x': coord['x'] - 1, 'y': coord['y']}


def prune_food(data, moves, food):
    temp = {}
    rlist = []
    for move in moves:
        temp = string_to_move(move, data["you"]["head"])
        if temp not in food:
            rlist.append(move)
    if (len(rlist) == 0):
        return moves
    return rlist


def isCorner(data, move):
    m = string_to_move(move, data["you"]["head"])
    board = data["board"]
    return (m["x"] == 0 or m["x"] == board["width"]) and (m["y"] == 0 or m["y"]
                                                          == board["height"])


def seekFood(data, move):
    foodList = data["board"]["food"]
    head = data["you"]["head"]
    closestFoodDist = 99
    temp = 99
    closestFood = {}
    for food in foodList:
        temp = distFrom(food, head)
        if temp < closestFoodDist:
            closestFoodDist = temp
            closestFood = food
    if distFrom(closestFood, head) > distFrom(move, closestFood):
        return True
    else:
        return False


def distFrom(c1, c2):
    return abs(c1["x"] - c2["x"]) + abs(c1["y"] - c2["y"])
