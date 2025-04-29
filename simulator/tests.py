# simulator/tests.py
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import Team, Player, Tournament, Match, Event
from .services.tournament_manager import TournamentManager
from .services.schedule_generator import ScheduleGenerator, RoundRobinStrategy

class TeamModelTests(TestCase):

    def test_team_creation(self):
        """Тест створення команди."""
        team = Team.objects.create(name="Test Lions", coach="John Doe")
        self.assertEqual(team.name, "Test Lions")
        self.assertEqual(str(team), "Test Lions")

    def test_add_remove_player(self):
        """Тест додавання та видалення гравця."""
        team = Team.objects.create(name="Eagles")
        player = Player.objects.create(name="Bob", age=25)
        self.assertIsNone(player.team)

        team.add_player(player)
        self.assertEqual(player.team, team)
        self.assertEqual(team.players.count(), 1)

        team.remove_player(player)
        self.assertIsNone(player.team)
        self.assertEqual(team.players.count(), 0)


class TournamentManagerTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Створення даних один раз для всіх тестів класу."""
        cls.team1 = Team.objects.create(name="Team A")
        cls.team2 = Team.objects.create(name="Team B")
        cls.team3 = Team.objects.create(name="Team C")
        cls.tournament = Tournament.objects.create(name="Test Cup")
        cls.tournament.teams.add(cls.team1, cls.team2, cls.team3)

        now = timezone.now()
        # Матчі
        Match.objects.create(tournament=cls.tournament, team1=cls.team1, team2=cls.team2,
                             match_datetime=now - timedelta(days=2), status=Match.STATUS_FINISHED, score1=3, score2=1)
        Match.objects.create(tournament=cls.tournament, team1=cls.team1, team2=cls.team3,
                             match_datetime=now - timedelta(days=1), status=Match.STATUS_FINISHED, score1=2, score2=2)
        Match.objects.create(tournament=cls.tournament, team1=cls.team2, team2=cls.team3,
                             match_datetime=now, status=Match.STATUS_SCHEDULED) # Незавершений матч

    def test_calculate_standings(self):
        """Тест розрахунку турнірної таблиці."""
        manager = TournamentManager(tournament_id=self.tournament.id)
        standings = manager.calculate_standings()

        self.assertEqual(len(standings), 3) # Має бути 3 команди

        # Перевірка позицій та очок (Team A - 4, Team B - 0, Team C - 1)
        # Сортування: A, C, B
        self.assertEqual(standings[0]['team'], self.team1)
        self.assertEqual(standings[0]['points'], 4)
        self.assertEqual(standings[0]['played'], 2)
        self.assertEqual(standings[0]['won'], 1)
        self.assertEqual(standings[0]['drawn'], 1)
        self.assertEqual(standings[0]['lost'], 0)
        self.assertEqual(standings[0]['gf'], 5) # 3 + 2
        self.assertEqual(standings[0]['ga'], 3) # 1 + 2
        self.assertEqual(standings[0]['gd'], 2)

        self.assertEqual(standings[1]['team'], self.team3)
        self.assertEqual(standings[1]['points'], 1)
        self.assertEqual(standings[1]['played'], 1) # Тільки один завершений матч
        self.assertEqual(standings[1]['gf'], 2)
        self.assertEqual(standings[1]['ga'], 2)
        self.assertEqual(standings[1]['gd'], 0)


        self.assertEqual(standings[2]['team'], self.team2)
        self.assertEqual(standings[2]['points'], 0)
        self.assertEqual(standings[2]['played'], 1) # Тільки один завершений матч
        self.assertEqual(standings[2]['lost'], 1)
        self.assertEqual(standings[2]['gf'], 1)
        self.assertEqual(standings[2]['ga'], 3)
        self.assertEqual(standings[2]['gd'], -2)


    def test_update_tournament_standings_json(self):
        """Тест оновлення JSON поля турнірної таблиці."""
        manager = TournamentManager(tournament_id=self.tournament.id)
        json_standings = manager.update_tournament_standings()

        self.tournament.refresh_from_db() # Оновити об'єкт з бази даних
        self.assertIn('table', self.tournament.standings)
        self.assertEqual(len(self.tournament.standings['table']), 3)
        self.assertEqual(self.tournament.standings['table'][0]['team_name'], "Team A")
        self.assertEqual(self.tournament.standings['table'][0]['points'], 4)

class ScheduleGeneratorTests(TestCase):
     def test_round_robin_generation(self):
        """Тест генерації розкладу 'Round Robin'."""
        team1 = Team.objects.create(name="Raptors")
        team2 = Team.objects.create(name="Sharks")
        team3 = Team.objects.create(name="Wolves")
        teams = [team1, team2, team3]
        start_date = timezone.datetime(2025, 6, 1, 15, 0, tzinfo=timezone.utc)

        strategy = RoundRobinStrategy()
        generator = ScheduleGenerator(strategy=strategy)
        schedule_data = generator.generate_schedule(teams, start_date)

        # Для 3 команд має бути C(3,2) = 3 матчі
        self.assertEqual(len(schedule_data), 3)

        # Перевірка пар (порядок не важливий в combinations)
        pairs = {(d['team1'], d['team2']) for d in schedule_data}
        expected_pairs = {
            (team1, team2),
            (team1, team3),
            (team2, team3),
        }
        # Порівнюємо множини, щоб ігнорувати порядок пар
        self.assertEqual(len(pairs.intersection(expected_pairs)), 3)

        # Перевірка першої дати
        self.assertEqual(schedule_data[0]['match_datetime'], start_date)

# Запуск тестів: python manage.py test simulator