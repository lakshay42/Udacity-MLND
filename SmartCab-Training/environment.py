import time
import random
import os
from collections import OrderedDict

from simulator import Simulator

script_dir = os.path.dirname(__file__)
path = os.path.join(script_dir, '../report/output_qlearning.txt')

class ThreeLights(object):

    possible_states = [True, False]  # True = NS open, False = EW open

    def __init__(self, current_state=None, current_period=None):
        self.current_state = current_state if current_state is not None else random.choice(self.possible_states)
        self.current_period = current_period if current_period is not None else random.choice([3, 4, 5])
        self.last_updated = 0

    def instance_reset(self):
        self.last_updated = 0

    def state_update(self, t):
        if t - self.last_updated >= self.current_period:
            self.current_state = not self.current_state  # assuming current_state is boolean
            self.last_updated = t


class MainEnv(object):
    """MainEnv within which all agents operate."""

    possible_valid_action = [None, 'forward', 'left', 'right']
    possible_valid_input = {'light': ThreeLights.possible_states, 'oncoming': possible_valid_action, 'left': possible_valid_action, 'right': possible_valid_action}
    possible_valid_headings = [(1, 0), (0, -1), (-1, 0), (0, 1)]  # ENWS

    def __init__(self):
        self.done = False
        self.t = 0
        self.possible_agent_states = OrderedDict()
        self.text_of_status = ""

        # Road network
        self.map_size = (8, 6)  # (cols, rows)
        self.bounds = (1, 1, self.map_size[0], self.map_size[1])
        self.square_size = 100
        self.map_intersection = OrderedDict()
        self.streets = []
        for x in xrange(self.bounds[0], self.bounds[2] + 1):
            for y in xrange(self.bounds[1], self.bounds[3] + 1):
                self.map_intersection[(x, y)] = ThreeLights()  # a traffic light at each intersection

        for a in self.map_intersection:
            for b in self.map_intersection:
                if a == b:
                    continue
                if (abs(a[0] - b[0]) + abs(a[1] - b[1])) == 1:  # L1 distance = 1
                    self.streets.append((a, b))

        # Dummy agents
        self.num_dummies = 3  # no. of dummy agents
        for i in xrange(self.num_dummies):
            self.create_agent(false_dummy_agents)

        # Primary agent
        self.primary_agent = None  # to be set explicitly
        self.enforce_deadline = False

    def create_agent(self, agent_class, *args, **kwargs):
        agent = agent_class(self, *args, **kwargs)
        self.possible_agent_states[agent] = {'location': random.choice(self.map_intersection.keys()), 'heading': (0, 1)}
        return agent

    def set_primary_agent(self, agent, enforce_deadline=False):
        self.primary_agent = agent
        self.enforce_deadline = enforce_deadline

    def instance_reset(self):
        self.done = False
        self.t = 0

        # Reset traffic lights
        for lights in self.map_intersection.itervalues():
            lights.instance_reset()

        # Pick a start and a destination
        start = random.choice(self.map_intersection.keys())
        destination = random.choice(self.map_intersection.keys())

        # Ensure starting location and destination are not too close
        while self.L1_distance_computation(start, destination) < 4:
            start = random.choice(self.map_intersection.keys())
            destination = random.choice(self.map_intersection.keys())

        start_heading = random.choice(self.possible_valid_headings)
        deadline = self.L1_distance_computation(start, destination) * 5
        print "MainEnv.instance_reset(): Trial set up with start = {}, destination = {}, deadline = {}".format(start, destination, deadline)

        # Initialize agent(s)
        for agent in self.possible_agent_states.iterkeys():
            self.possible_agent_states[agent] = {
                'location': start if agent is self.primary_agent else random.choice(self.map_intersection.keys()),
                'heading': start_heading if agent is self.primary_agent else random.choice(self.possible_valid_headings),
                'destination': destination if agent is self.primary_agent else None,
                'deadline': deadline if agent is self.primary_agent else None}
            agent.instance_reset(destination=(destination if agent is self.primary_agent else None))

    def all_steps(self):
        #print "MainEnv.all_steps(): t = {}".format(self.t)  # [debug]

        # Update traffic lights
        for intersection, lights in self.map_intersection.iteritems():
            lights.state_update(self.t)

        # Update agents
        for agent in self.possible_agent_states.iterkeys():
            agent.state_update(self.t)

        self.t += 1
        if self.primary_agent is not None:
            if self.enforce_deadline and self.possible_agent_states[self.primary_agent]['deadline'] <= 0:
                self.done = True
                print "MainEnv.instance_reset(): Primary agent could not reach destination within deadline!"
                with open(path, 'a') as file:
                    file.write("- Agent hasn't reached the destination on time\n")
            self.possible_agent_states[self.primary_agent]['deadline'] -= 1

    def env_sense(self, agent):
        assert agent in self.possible_agent_states, "Unknown agent!"

        current_state = self.possible_agent_states[agent]
        location = current_state['location']
        heading = current_state['heading']
        light = 'green' if (self.map_intersection[location].current_state and heading[1] != 0) or ((not self.map_intersection[location].current_state) and heading[0] != 0) else 'red'

        # Populate oncoming, left, right
        oncoming = None
        left = None
        right = None
        for other_agent, other_state in self.possible_agent_states.iteritems():
            if agent == other_agent or location != other_state['location'] or (heading[0] == other_state['heading'][0] and heading[1] == other_state['heading'][1]):
                continue
            other_heading = other_agent.get_next_waypoint()
            if (heading[0] * other_state['heading'][0] + heading[1] * other_state['heading'][1]) == -1:
                if oncoming != 'left':  # we don't want to override oncoming == 'left'
                    oncoming = other_heading
            elif (heading[1] == other_state['heading'][0] and -heading[0] == other_state['heading'][1]):
                if right != 'forward' and right != 'left':  # we don't want to override right == 'forward or 'left'
                    right = other_heading
            else:
                if left != 'forward':  # we don't want to override left == 'forward'
                    left = other_heading

        return {'light': light, 'oncoming': oncoming, 'left': left, 'right': right}  # TODO: make this a namedtuple

    def obtain_deadline(self, agent):
        return self.possible_agent_states[agent]['deadline'] if agent is self.primary_agent else None

    def determine_action(self, agent, action):
        assert agent in self.possible_agent_states, "Unknown agent!"
        assert action in self.possible_valid_action, "Invalid action!"

        current_state = self.possible_agent_states[agent]
        location = current_state['location']
        heading = current_state['heading']
        light = 'green' if (self.map_intersection[location].current_state and heading[1] != 0) or ((not self.map_intersection[location].current_state) and heading[0] != 0) else 'red'

        # Move agent if within bounds and obeys traffic rules
        reward = 0  # reward/penalty
        move_okay = True
        if action == 'forward':
            if light != 'green':
                move_okay = False
        elif action == 'left':
            if light == 'green':
                heading = (heading[1], -heading[0])
            else:
                move_okay = False
        elif action == 'right':
            heading = (-heading[1], heading[0])

        if action is not None:
            if move_okay:
                location = ((location[0] + heading[0] - self.bounds[0]) % (self.bounds[2] - self.bounds[0] + 1) + self.bounds[0],
                            (location[1] + heading[1] - self.bounds[1]) % (self.bounds[3] - self.bounds[1] + 1) + self.bounds[1])  # wrap-around
                #if self.bounds[0] <= location[0] <= self.bounds[2] and self.bounds[1] <= location[1] <= self.bounds[3]:  # bounded
                current_state['location'] = location
                current_state['heading'] = heading
                reward = 2 if action == agent.get_next_waypoint() else 0.5
            else:
                reward = -1
        else:
            reward = 1

        if agent is self.primary_agent:
            if current_state['location'] == current_state['destination']:
                if current_state['deadline'] >= 0:
                    reward += 10  # bonus
                self.done = True
                print "MainEnv.determine_action(): Primary agent has reached destination!"  # [debug]
                with open(path, 'a') as file:
                    file.write("+ Agent reached the destination on time\n")
            self.text_of_status = "current_state: {}\naction: {}\nreward: {}".format(agent.get_state(), action, reward)
            #print "MainEnv.determine_action() [POST]: location: {}, heading: {}, action: {}, reward: {}".format(location, heading, action, reward)  # [debug]

        return reward

    def L1_distance_computation(self, a, b):
        """L1 distance between two points."""
        return abs(b[0] - a[0]) + abs(b[1] - a[1])


class Agent(object):
    """Base class for all agents."""

    def __init__(self, envmnt):
        self.envmnt = envmnt
        self.current_state = None
        self.upcoming_bystop = None
        self.color = 'cyan'

    def instance_reset(self, destination=None):
        pass

    def state_update(self, t):
        pass

    def get_state(self):
        return self.current_state

    def get_next_waypoint(self):
        return self.upcoming_bystop


class false_dummy_agents(Agent):
    color_choices = ['blue', 'cyan', 'magenta', 'orange']

    def __init__(self, envmnt):
        super(false_dummy_agents, self).__init__(envmnt)  # sets self.envmnt = envmnt, current_state = None, upcoming_bystop = None, and a default color
        self.upcoming_bystop = random.choice(MainEnv.possible_valid_action[1:])
        self.color = random.choice(self.color_choices)

    def state_update(self, t):
        inputs = self.envmnt.env_sense(self)

        action_okay = True
        if self.upcoming_bystop == 'right':
            if inputs['light'] == 'red' and inputs['left'] == 'forward':
                action_okay = False
        elif self.upcoming_bystop == 'straight':
            if inputs['light'] == 'red':
                action_okay = False
        elif self.upcoming_bystop == 'left':
            if inputs['light'] == 'red' or (inputs['oncoming'] == 'forward' or inputs['oncoming'] == 'right'):
                action_okay = False

        action = None
        if action_okay:
            action = self.upcoming_bystop
            self.upcoming_bystop = random.choice(MainEnv.possible_valid_action[1:])
        reward = self.envmnt.determine_action(self, action)
        #print "false_dummy_agents.state_update(): t = {}, inputs = {}, action = {}, reward = {}".format(t, inputs, action, reward)  # [debug]
        #print "false_dummy_agents.state_update(): upcoming_bystop = {}".format(self.upcoming_bystop)  # [debug]
