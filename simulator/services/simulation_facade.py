
from .tournament_manager import TournamentManager
from .schedule_generator import ScheduleGenerator, RoundRobinStrategy # Example
from .report_generator import TournamentResultsReport # Example
from ..models import Tournament, Event, Team, Player, Match # etc.

class SimulationFacade:
    def create_event(self, name, start_date, end_date, location=None):
        event = Event.objects.create(name=name, start_date=start_date, end_date=end_date, location=location)
        print(f"Створено подію: {event}")
        return event

    def add_team_to_event(self, event_id, team_id):
        try:
            event = Event.objects.get(pk=event_id)
            team = Team.objects.get(pk=team_id)
            event.add_team(team)
        except (Event.DoesNotExist, Team.DoesNotExist) as e:
             print(f"Помилка додавання команди до події: {e}")

    def create_tournament(self, name, event_id=None):
        params = {'name': name}
        if event_id:
            params['event_id'] = event_id
        tournament = Tournament.objects.create(**params)
        print(f"Створено турнір: {tournament}")
        return tournament

    def generate_tournament_schedule(self, tournament_id, start_date, strategy_class=RoundRobinStrategy):
        try:
            tournament = Tournament.objects.get(pk=tournament_id)
            generator = ScheduleGenerator(strategy=strategy_class())
            matches = generator.create_matches_for_tournament(tournament, start_date)
            return matches
        except Tournament.DoesNotExist as e:
             print(f"Помилка генерації розкладу: {e}")
             return []

    def record_match_result(self, match_id, score1, score2):
         try:
            match = Match.objects.get(pk=match_id)
            match.set_result(score1, score2)
            print(f"Результат матчу {match} записано.")
         except Match.DoesNotExist as e:
             print(f"Помилка запису результату: {e}")
         except (ValueError, TypeError) as e:
             print(f"Помилка даних результату: {e}")


    def get_tournament_report(self, tournament_id):
        reporter = TournamentResultsReport()
        report = reporter.generate(tournament_id=tournament_id)
        return report

