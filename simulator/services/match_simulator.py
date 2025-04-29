import random
from ..models import Match, Team
from django.core.exceptions import ValidationError
from .player_stats_updater import update_player_stats_from_match_data

class SimpleMatchSimulator:

    def __init__(self, match: Match):
        if not isinstance(match, Match):
            raise TypeError("Необхідно передати об'єкт Match.")
        self.match = match

    def _get_team_strength(self, team: Team):
        base_strength = team.players.count() * 10
        random_factor = random.uniform(0.8, 1.2)
        name_bonus = len(team.name) % 5
        return base_strength * random_factor + name_bonus

    def simulate(self):

        if self.match.status != Match.STATUS_SCHEDULED:
             print(f"Матч {self.match.id} не запланований, симуляція неможлива.")
             return None

        print(f"Симуляція матчу: {self.match.team1} vs {self.match.team2}")

        strength1 = self._get_team_strength(self.match.team1)
        strength2 = self._get_team_strength(self.match.team2)

        max_goals = 5
        score1 = 0
        score2 = 0

        simulation_steps = 10
        for _ in range(simulation_steps):
            if random.random() < (strength1 / (strength1 + strength2 + 1)) * 0.5:
                if score1 < max_goals:
                     score1 += 1
            if random.random() < (strength2 / (strength1 + strength2 + 1)) * 0.5:
                 if score2 < max_goals:
                     score2 += 1

        print(f"Результат симуляції: {score1} - {score2}")
        return score1, score2

    def simulate_and_set_result(self):
        result = self.simulate()
        if result is not None:
            score1, score2 = result
            try:
                self.match.set_result(score1, score2)
                print(f"Результат {score1}-{score2} для матчу {self.match.id} записано.")
                self._assign_random_scorers(score1, score2)
                return True
            except (ValueError, ValidationError) as e:
                print(f"Помилка запису результату симуляції: {e}")
                return False
        return False

    def _assign_random_scorers(self, score1, score2):
        scorers1_ids = []
        assists1_ids = []
        scorers2_ids = []
        assists2_ids = []

        players1 = list(self.match.team1.players.all())
        players2 = list(self.match.team2.players.all())

        if players1:
            for _ in range(score1):
                 scorer = random.choice(players1)
                 scorers1_ids.append(str(scorer.id))
                 potential_assistants = [p for p in players1 if p != scorer]
                 if potential_assistants and random.random() > 0.3:
                     assists1_ids.append(str(random.choice(potential_assistants).id))

        if players2:
            for _ in range(score2):
                 scorer = random.choice(players2)
                 scorers2_ids.append(str(scorer.id))
                 potential_assistants = [p for p in players2 if p != scorer]
                 if potential_assistants and random.random() > 0.3:
                     assists2_ids.append(str(random.choice(potential_assistants).id))

        update_player_stats_from_match_data(
             match=self.match,
             scorers1_ids=scorers1_ids, assists1_ids=assists1_ids,
             scorers2_ids=scorers2_ids, assists2_ids=assists2_ids
        )