import random

class MapRoute(object):
    """Silly route planner that is meant for a perpendicular grid network."""

    def __init__(self, env, agent):
        self.env = env
        self.agent = agent
        self.destination = None

    def direction_towards(self, destination=None):
        self.destination = destination if destination is not None else random.choice(self.env.intersections.keys())
        print "MapRoute.direction_towards(): destination = {}".format(destination)  # [debug]

    def upcoming_bystop(self):
        current_location = self.env.possible_agent_states[self.agent]['location']
        going_to = self.env.possible_agent_states[self.agent]['heading']
        delta = (self.destination[0] - current_location[0], self.destination[1] - current_location[1])
        if delta[0] == 0 and delta[1] == 0:
            return None
        elif delta[0] != 0:  # EW difference
            if delta[0] * going_to[0] > 0:  # facing correct EW direction
                return 'forward'
            elif delta[0] * going_to[0] < 0:  # facing opposite EW direction
                return 'right'  # long U-turn
            elif delta[0] * going_to[1] > 0:
                return 'right'
            else:
                return 'left'
        elif delta[1] != 0:  # NS difference
            if delta[1] * going_to[1] > 0:  # facing correct NS direction
                return 'forward'
            elif delta[1] * going_to[1] < 0:  # facing opposite NS direction
                return 'right'  # long U-turn
            elif delta[1] * going_to[0] > 0:
                return 'right'
            else:
                return 'left'
