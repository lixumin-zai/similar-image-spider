import json
import random
import os

current_dir = os.path.dirname(os.path.abspath(__file__))

class UserAgent:
    def __init__(self):
        with open(f"{current_dir}/../static/user_agents.json", "r") as f:
            self.user_agents = json.load(f)

        base_probabilities = [float(item['weights'].strip('%')) for item in self.user_agents]
        self.weights = [p / sum(base_probabilities) for p in base_probabilities]


    def __call__(self):
        return random.choices(self.user_agents, weights=self.weights, k=1)[0]['user_agent']


if __name__ == "__main__":
    user_agent = UserAgent()
    print(user_agent())

