#!/bin/python
import sys
sys.path.append('..') #janky fix for package not properly installing on remote
from pz_battlesnake.env import duels_v0
import pettingzoo
import gymnasium as gym
import math
import random
import numpy as np
import matplotlib.pyplot as plt
from collections import namedtuple, deque
from itertools import count
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import time
import os
import snakebrain
env = duels_v0.env() # create a default duels environment

plt.ion()


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
Transition = namedtuple('Transition', 
                        ('state', 'action', 'next_state', 'reward', 'agent')) #saving the result of taking action a in state s, we progress to the next state and observe a reward

#our dqn agents network
class DQN(nn.Module):

    def __init__(self, n_observations, n_actions):
        super(DQN, self).__init__()
        self.network = nn.Sequential(
            nn.Flatten(),
            nn.Linear(n_observations, 1024),
            nn.ReLU(),
            nn.Linear(1024,1024),
            nn.ReLU(),
            nn.Linear(1024,1024),
            nn.ReLU(),
            nn.Linear(1024, n_actions),
        )
    # Called with either one element to determine next action, or a batch
    # during optimization. Returns tensor([[left0exp,right0exp]...]).
    def forward(self, x):
        return self.network(x)


class ReplayMemory(object):

    def __init__(self, capacity):
        self.memory = deque([],maxlen=capacity)

    def push(self, *args):
        """Save a transition"""
        self.memory.append(Transition(*args))

    def sample(self, batch_size):
        return random.sample(self.memory, batch_size)

    def __len__(self):
        return len(self.memory)
    #when an agent wins or loses we push a new transition to memory that associates winning / losing move with a reward
    def add_transition_for_agent(self, agent, new_value):
        for i in range(len(self.memory)-1, -1, -1):
            if self.memory[i].agent == agent:
                new_transition = Transition(self.memory[i].state, self.memory[i].action, self.memory[i].next_state, torch.tensor([new_value], device=device), self.memory[i].agent)
                self.push(*new_transition)
                break

# BATCH_SIZE is the number of transitions sampled from the replay buffer
# GAMMA is the discount factor as mentioned in the previous section
# EPS_START is the starting value of epsilon
# EPS_END is the final value of epsilon
# EPS_DECAY controls the rate of exponential decay of epsilon, higher means a slower decay
# TAU is the update rate of the target network
# LR is the learning rate of the AdamW optimizer
BATCH_SIZE = 500
GAMMA = 0.99
EPS_START = 0.99
EPS_END = 0.003 #in long games each action is really important, so we want to be greedy after lots of training
EPS_DECAY = 2000
TAU = 0.005
LR = 1e-4   

# 4 actions, left, right, up, down
n_actions = 4
# Get the number of state observations
env.reset()

observation, reward, termination, truncation, info = env.last()
#print(observation)
'''example observation:

{'game': {'id': 'cb7e7773-03e7-43e4-afad-9da19c0ede0c', 'ruleset': {'name': 'standard', 'version': 'cli', 
'settings': {'foodSpawnChance': 15, 'minimumFood': 1, 'hazardDamagePerTurn': 0, 'hazardMap': '', 'hazardMapAuthor': '', 
'royale': {'shrinkEveryNTurns': 0}, 'squad': {'allowBodyCollisions': False, 'sharedElimination': False, 'sharedHealth': False, 'sharedLength': False}}}, 
'map': 'standard', 'timeout': 0, 'source': ''}, 'turn': 0, 
'board': {'height': 11, 'width': 11,
 'snakes': [{'id': 'agent_1', 'name': 'agent_1', 'latency': '0', 'health': 100, 'body': [{'x': 1, 'y': 1}, {'x': 1, 'y': 1}, {'x': 1, 'y': 1}], 'head': {'x': 1, 'y': 1}, 'length': 3, 'shout': '', 'squad': '', 'customizations': {'color': '#0000FF', 'head': '', 'tail': ''}}, 
{'id': 'agent_0', 'name': 'agent_0', 'latency': '0', 'health': 100, 'body': [{'x': 9, 'y': 9}, {'x': 9, 'y': 9}, {'x': 9, 'y': 9}], 'head': {'x': 9, 'y': 9}, 'length': 3, 'shout': '', 'squad': '', 'customizations': {'color': '#00FF00', 'head': '', 'tail': ''}}], 
'food': [{'x': 0, 'y': 2}, {'x': 10, 'y': 8}, {'x': 5, 'y': 5}], 'hazards': []}, 
'you': {'id': 'agent_0', 'name': 'agent_0', 'latency': '0', 'health': 100, 'body': [{'x': 9, 'y': 9}, {'x': 9, 'y': 9}, {'x': 9, 'y': 9}], 'head': {'x': 9, 'y': 9}, 'length': 3, 'shout': '', 'squad': '', 'customizations': {'color': '#00FF00', 'head': '', 'tail': ''}}}

'''


'''turn the observation dictionary we get from the environment into a matrix of values
we get:
The snakes health
Where our snakes head is
Where its body segments are
Where the food is
'''
def observation_to_values(observation):
    try:
        board = observation['board']
    except:
        observation = observation['observation']
    #init
    board = observation['board']
    health = 100
    n_channels = 8
    state_matrix = np.zeros((n_channels, board["height"], board["width"]))
    #fill
    for _snake in board['snakes']:
        health = np.array(_snake['health'])
        #if us
        if _snake['id'] == observation['you']['id']:
            #place our head on channel 0
            state_matrix[0, _snake['head']['x'], _snake['head']['y']] = 1
            
            #place our tail on channel 1
            state_matrix[1, _snake['body'][-1]['x'], _snake['body'][-1]['y']] = 1
            #place body on channel 2
            for _body_segment in _snake['body']:
                state_matrix[2, _body_segment['x'], _body_segment['y']] = 1
        else:
            #place adversary head on channel 3
            state_matrix[3, _snake['head']['x'], _snake['head']['y']] = 1
            #place adversary tail on channel 4
            state_matrix[4, _snake['body'][-1]['x'], _snake['body'][-1]['y']] = 1
            #place adversary body on channel 5
            for _body_segment in _snake['body']:
                state_matrix[5, _body_segment['x'], _body_segment['y']] = 1
    #place food on channel 6
    for _food in board["food"]:
        state_matrix[6,_food['x'], _food['y']] = 1
    #create health channel
    state_matrix[7] = np.full((board["height"], board["width"]), health)
    #flatten
    return state_matrix.flatten()


#get the observation vector
state = observation_to_values(observation["observation"])
n_observations = len(state) #note the length of the vector

#print("size of obs vector: ", n_observations)

#initialize the networks
#initialize the networks
policy_net = DQN(n_observations, n_actions).to(device) 
target_net = DQN(n_observations, n_actions).to(device) 
target_net.load_state_dict(policy_net.state_dict()) 
#initialize the optimizer
optimizer = optim.AdamW(policy_net.parameters(), lr=LR, amsgrad=True)

#initialize the replay memory
memory = ReplayMemory(10000)


steps_done = 0

'''Select an action using the policy network, or a random action with probability epsilon'''
def select_action(state):
    global steps_done
    sample = random.random()
    eps_threshold = EPS_END + ( (EPS_START - EPS_END) * math.exp(-1. * steps_done / EPS_DECAY) )
    steps_done += 1
    if sample > eps_threshold:
        with torch.no_grad():
            # t.max(1) will return largest column value of each row.
            # second column on max result is index of where max element was
            # found, so we pick action with the larger expected reward.
            return policy_net(state).max(1)[1].view(1, 1)
    else:
        return torch.tensor([[env.action_space(env.agents[0]).sample()]], device=device, dtype=torch.long)


# number of turns the snake survives in each episode
episode_durations = []
def plot_dqn_wins(show_result=False):
    plt.figure(2)
    wins_t = torch.tensor(dqn_win_list, dtype=torch.float)
    if show_result:
        plt.title('Result')
    else:
        plt.clf()
        plt.title('Training...')
    plt.xlabel('Episode')
    plt.ylabel('Wins')
    plt.plot(wins_t.numpy())
    # Take 100 episode averages and plot them too
    #plt.pause(0.001)  # pause a bit so that plots are updated
'''interactive plotting'''
def plot_durations(show_result=False):
    plt.figure(1)
    durations_t = torch.tensor(episode_durations, dtype=torch.float)
    if show_result:
        plt.title('Result')
    else:
        plt.clf()
        plt.title('Training...')
    plt.xlabel('Episode')
    plt.ylabel('Duration')
    plt.plot(durations_t.numpy())
    # Take 100 episode averages and plot them too
    if len(durations_t) >= 100:
        means = durations_t.unfold(0, 100, 1).mean(1).view(-1)
        means = torch.cat((torch.zeros(99), means))
        plt.plot(means.numpy())

    #plt.pause(0.001)  # pause a bit so that plots are updated



'''Optimize our Q function approximator using the replay memory
Mostly pulled from the pytorch DQN tutorial
'''
def optimize_model():
    if len(memory) < BATCH_SIZE:
        return
    #print("memory", memory)
    transitions = memory.sample(BATCH_SIZE)
    # Transpose the batch (see https://stackoverflow.com/a/19343/3343043 for
    # detailed explanation). This converts batch-array of Transitions
    # to Transition of batch-arrays.
    batch = Transition(*zip(*transitions))

    # Compute a mask of non-final states and concatenate the batch elements
    # (a final state would've been the one after which simulation ended)
    non_final_mask = torch.tensor(tuple(map(lambda s: s is not None,
                                          batch.next_state)), device=device, dtype=torch.bool)

    non_final_next_states = torch.cat([s for s in batch.next_state
                                                if s is not None])
    state_batch = torch.cat(batch.state)
    action_batch = torch.cat(batch.action)
    reward_batch = torch.cat(batch.reward)

    # Compute Q(s_t, a) - the model computes Q(s_t), then we select the
    # columns of actions taken. These are the actions which would've been taken
    # for each batch state according to policy_net
    state_action_values = policy_net(state_batch).gather(1, action_batch)

    # Compute V(s_{t+1}) for all next states.
    # Expected values of actions for non_final_next_states are computed based
    # on the "older" target_net; selecting their best reward with max(1)[0].
    # This is merged based on the mask, such that we'll have either the expected
    # state value or 0 in case the state was final.
    next_state_values = torch.zeros(BATCH_SIZE, device=device)
    
    with torch.no_grad():
        next_state_values[non_final_mask] = target_net(non_final_next_states).max(1)[0]
    # Compute the expected Q values
    expected_state_action_values = (next_state_values * GAMMA) + reward_batch

    # Compute Huber loss
    criterion = nn.SmoothL1Loss()
    loss = criterion(state_action_values, expected_state_action_values.unsqueeze(1))

    # Optimize the model
    optimizer.zero_grad()
    loss.backward()
    # In-place gradient clipping
    torch.nn.utils.clip_grad_value_(policy_net.parameters(), 100)
    optimizer.step()

num_episodes = 50000

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
dqn_wins = 0
dqn_win_list = []
for i_episode in range(num_episodes):
    # Initialize the environment and get it's state
    t = 0
    if i_episode % 100 == 1:
        plot_durations(show_result=False)
        plt.show()
        plt.savefig("adversary_test_duration.png")
        plot_dqn_wins(show_result=False)
        plt.show()
        plt.savefig("adversary_test_wins.png")
    #print("Episode: ", i_episode)
    env.reset()
    observation, reward, termination, truncation, info = env.last()
    state = observation_to_values(observation["observation"])
    #print("state: ", state)
    state = torch.tensor(state, dtype=torch.float32, device=device).unsqueeze(0)
    done = False
    if i_episode % 10 == 0:
        target_net_state_dict = target_net.state_dict()
        policy_net_state_dict = policy_net.state_dict()
        for key in policy_net_state_dict:
            target_net_state_dict[key] = policy_net_state_dict[key]
        target_net.load_state_dict(target_net_state_dict)
    while not done:
        # if i_episode % 200 == 0:
        #     time.sleep(0.1)
        #     env.render()
        for agent in env.agents:
            if agent == "agent_1":
                action = select_action(state)
                env.step(action.item())
            else: 
                action = string_to_act[adversary_select_action(observation)]
                env.step(action)
            observation, reward, terminated, truncated, _ = env.last()
            done = terminated or truncated

            if terminated:
                #check which agent won, positive reward for winning, negative for losing
                #Go back into the memory and update the reward for the winning agent
                #gets reward of 1 for making the winning move
                if len(observation["board"]["snakes"]) == 1:
                    winner = observation["board"]["snakes"][0]["id"]
                    #print("WINNER: ", winner)
                    if winner == "agent_1":
                        reward = 10
                        dqn_wins += 1
                    else:
                        reward = -10
                else:
                    reward = 0
                next_state = None
            else:
                reward = 1
                next_state = torch.tensor(observation_to_values(observation), dtype=torch.float32, device=device).unsqueeze(0)
            reward = torch.tensor([reward], device=device)
            if agent == "agent_1":
                memory.push(state, action, next_state, reward, agent)
            t += 1
            # Store the transition in memory

            # Move to the next state
            state = next_state

            # Perform one step of the optimization (on the policy network)
            optimize_model()

            if done:
                dqn_win_list.append(dqn_wins)
                episode_durations.append(t + 1)
                # if i_episode % 100 == 0 and i_episode != 0: #only plotting every 100 eps to avoid the annoying popups
                #     # plot_durations()
                break

print('Complete')

#torch.save(policy_net.state_dict(), f"./saved_models/policy_weights_{num_episodes}.pt")