import random
from environment import Agent, MainEnv
from planner import MapRoute
from simulator import Simulator

class LearningAgent(Agent):

    def __init__(self, envmnt):
        super(LearningAgent, self).__init__(envmnt) 
        self.color = 'red'  # override color
        self.planner = MapRoute(self.envmnt, self)  # simple route planner to get upcoming_bystop
        self.upcoming_bystop = None
        self.total_reward = 0

    def instance_reset(self, destination=None):
        self.planner.direction_towards(destination)
        self.current_state = None
        self.upcoming_bystop = None

    def state_update(self, t):
        self.upcoming_bystop = self.planner.upcoming_bystop()  
        inputs = self.envmnt.env_sense(self)
        deadline = self.envmnt.obtain_deadline(self)

        # TODO: Select action according to your policy
        action = random.choice(MainEnv.possible_valid_action)

        # TODO: Update current_state
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

        if not action_okay:
            action = None

        # Execute action and get reward
        reward = self.envmnt.determine_action(self, action)
        self.total_reward += reward

        # TODO: Learn policy based on current_state, action, reward

        print "LearningAgent.state_update(): deadline = {}, inputs = {}, action = {}, reward = {}".format(deadline, inputs, action, reward)  # [debug]


def run():
    """Run the agent for a finite number of trials."""

    # Set up environment and agent
    e = MainEnv()  # create environment (also adds some dummy traffic)
    a = e.create_agent(LearningAgent)  # create agent
    e.set_primary_agent(a, enforce_deadline=True)  # set agent to track

    # Now simulate it
    sim = Simulator(e, delay_of_update=1.2)  # reduce delay_of_update to speed up simulation
    sim.run(n_trials=100)  # press Esc or close pygame window to quit


if __name__ == '__main__':
    run()
