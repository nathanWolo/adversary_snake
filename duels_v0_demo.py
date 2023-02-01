from pz_battlesnake.env import duels_v0
import time
import snakebrain
def adversary_select_action(observation):
    try:
        safe_moves = snakebrain.get_safe_moves(observation, observation["you"])
    except:
        observation = observation["observation"]
        safe_moves = snakebrain.get_safe_moves(observation, observation["you"])
    if len(safe_moves) == 0:
        return env.action_space(env.agents[0]).sample()
    best = snakebrain.prune_safe_moves(observation, safe_moves)
    return best
string_to_act = {"up":0, "down":1, "left": 2, "right": 3 }
env = duels_v0.env()
dead_agents = []
# Run for 10 games
for _ in range(10):
    # Reset enviorment, before each game
    env.reset()
    dead_agents = []
    done = False
    while not done:
        for agent in env.agents:
            #print("Agent: ", env.agents)
            # Get Last Observation, Reward, Done, Info
            if agent not in dead_agents:
                observation, reward, termination, truncation, info = env.last()
            else:
                continue
            # try:
            #     #print("observation board: ", observation["board"])
            # except:
            #     pass
            # Pick an action, if agenmt is done, pick None
            #print("termination: ", termination)
            if termination:
                action = None
                #dead_agents.append(agent)
            else:
                if agent == "agent_0":
                    action = env.action_space(agent).sample()
                else:
                    action = adversary_select_action(observation)
                    print(action)
                    print(string_to_act[action])
                    action = string_to_act[action]
            # Step through the environment
            env.step(action)
            obs, _, dead, _, _ = env.last()
            if dead:
                #print("START OBS:", obs)
                dead_agents.append(agent)
                if len(obs["board"]["snakes"]) == 1:
                    done = True
                    print("WINNER:", obs["board"]["snakes"][0]["id"])
                #else:
                    #print("TIE")
       # print("dead agents", dead_agents)
        # Code below runs, when all agents has taken an action
        # Render the enviorment
        time.sleep(1)
        env.render() # uncomment this to render
        #since this is a duels env, we need to check if any agents are dead
        done = (len(dead_agents) > 0)