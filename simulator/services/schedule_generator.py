import abc
import itertools
import random
import math
from datetime import timedelta
from django.utils import timezone
from ..models import Team, Match, Tournament

class ScheduleStrategy(abc.ABC):
    @abc.abstractmethod
    def generate(self, teams, start_date, **kwargs):
        """Генерує список потенційних матчів."""
        pass

class RoundRobinStrategy(ScheduleStrategy):
    def generate(self, teams, start_date, time_per_match=timedelta(days=1), matches_per_day=1):
        if len(teams) < 2: return []
        schedule = []
        if isinstance(start_date, timezone.datetime):
            match_datetime = start_date
        else:
             match_datetime = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time())) + timedelta(hours=12)

        match_count_today = 0
        for team1, team2 in itertools.combinations(teams, 2):
            schedule.append({'team1': team1, 'team2': team2,'match_datetime': match_datetime,'status': Match.STATUS_SCHEDULED})
            match_count_today += 1
            if match_count_today >= matches_per_day:
                match_datetime += time_per_match
                match_count_today = 0
        return schedule

class KnockoutStrategy(ScheduleStrategy):
    def generate(self, teams, start_date, time_per_match=timedelta(days=1), matches_per_day=1):
        num_teams = len(teams)
        if num_teams < 2: return []
        if num_teams % 2 != 0:
            print("Попередження: Непарна кількість команд для Knockout.")
            random.shuffle(teams)
            teams = teams[:-1]
            num_teams -=1
            if num_teams < 2: return []

        random.shuffle(teams)
        schedule = []
        match_datetime = timezone.make_aware(timezone.datetime.combine(start_date, timezone.datetime.min.time())) + timedelta(hours=12)
        match_count_today = 0
        for i in range(0, num_teams, 2):
            if i + 1 < num_teams:
                team1 = teams[i]; team2 = teams[i+1]
                schedule.append({'team1': team1,'team2': team2,'match_datetime': match_datetime,'status': Match.STATUS_SCHEDULED})
                match_count_today += 1
                if match_count_today >= matches_per_day:
                    match_datetime += time_per_match
                    match_count_today = 0
        print(f"Knockout: Згенеровано {len(schedule)} матчів першого раунду.")
        return schedule

class ScheduleGenerator:

    def __init__(self, strategy: ScheduleStrategy):
        if not isinstance(strategy, ScheduleStrategy):
             raise TypeError("Стратегія має бути екземпляром ScheduleStrategy")
        self._strategy = strategy

    def generate_schedule(self, teams, start_date, **kwargs):
        if not isinstance(teams, list) and not hasattr(teams, 'all'):
             raise TypeError("teams має бути списком або QuerySet")
        team_list = list(teams)
        if not team_list:
            return []

        print(f"Генерація розкладу за стратегією: {self._strategy.__class__.__name__}")
        return self._strategy.generate(team_list, start_date, **kwargs)

    def create_matches_for_tournament(self, tournament: Tournament, start_date, **kwargs):
        teams = list(tournament.teams.all())
        if not teams:
            print(f"У турнірі '{tournament.name}' немає команд для генерації розкладу.")
            return []

        potential_matches_data = self.generate_schedule(teams, start_date, **kwargs)
        created_matches = []
        for match_data in potential_matches_data:
            try:
                defaults={
                    'match_datetime': match_data['match_datetime'],
                    'status': match_data['status']
                }
                match, created = Match.objects.get_or_create(
                    tournament=tournament,
                    team1=match_data['team1'],
                    team2=match_data['team2'],
                    defaults=defaults
                )
                if created:
                    created_matches.append(match)
                    print(f"Створено матч: {match} для турніру {tournament.name}")
            except Exception as e:
                 print(f"Помилка створення матчу для {match_data}: {e}")
        return created_matches
