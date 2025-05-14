from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta, date
import uuid
import re

from .models import Event, Team, Player, PlayerStatistics, Tournament, Match, Recommendation
from .forms import EventForm, TeamForm, PlayerForm, MatchResultForm, TournamentForm
from .services.tournament_manager import TournamentManager
from .services.schedule_generator import create_schedule_generator, RoundRobinStrategy, KnockoutStrategy
from .services.report_generator import TournamentResultsReport, PlayerStatisticsReport
from .services.recommendation_system import RecommendationSystem
from .services.match_simulator import SimpleMatchSimulator
from .services.commands import RecordMatchResultCommand, SimulateMatchResultCommand

def create_team(name="Test Team", coach="Coach"):
    return Team.objects.create(name=name, coach=coach)

def create_player(team, name="Test Player", age=25, position="Forward"):
    player = Player.objects.create(name=name, age=age, position=position, team=team)
    PlayerStatistics.objects.get_or_create(player=player)
    return player

def create_event(name="Test Event", days_offset=0):
    start = timezone.now().date() + timedelta(days=days_offset)
    end = start + timedelta(days=7)
    return Event.objects.create(name=name, start_date=start, end_date=end, location="Test Location")

def create_tournament(name="Test Tournament", event=None):
    return Tournament.objects.create(name=name, event=event)

def create_match(team1, team2, tournament=None, days_offset=1, status=Match.STATUS_SCHEDULED, score1=None, score2=None):
    match_dt = timezone.now() + timedelta(days=days_offset)
    match, created = Match.objects.get_or_create(
        tournament=tournament,
        team1=team1,
        team2=team2,
        defaults={
            'match_datetime': match_dt,
            'status': status,
            'score1': score1,
            'score2': score2
        }
    )
    if not created:
        print(f"Warning: Match between {team1} and {team2} in {tournament} already existed.")
        match.status = status
        match.score1 = score1
        match.score2 = score2
        match.match_datetime = match_dt
        match.save()
    return match

class ModelCreationTests(TestCase):

    def setUp(self):
        self.team1 = create_team(name="Lions")
        self.player1 = create_player(self.team1, name="Leo")
        self.event1 = create_event(name="Summer Cup")
        self.tournament1 = create_tournament(name="Group Stage", event=self.event1)
        self.team2 = create_team(name="Tigers")
        self.match1 = create_match(self.team1, self.team2, self.tournament1)

    def test_team_creation(self):
        self.assertEqual(self.team1.name, "Lions")
        self.assertEqual(str(self.team1), "Lions")

    def test_player_creation_and_stats(self):
        self.assertEqual(self.player1.name, "Leo")
        self.assertEqual(self.player1.team, self.team1)
        self.assertTrue(hasattr(self.player1, 'statistics'))
        self.assertEqual(self.player1.statistics.goals, 0)
        self.assertEqual(str(self.player1), "Leo (Forward)")

    def test_event_creation(self):
        self.assertEqual(self.event1.name, "Summer Cup")
        self.assertTrue(self.event1.start_date < self.event1.end_date)
        self.assertEqual(str(self.event1), f"Summer Cup ({self.event1.start_date} - {self.event1.end_date})")

    def test_tournament_creation(self):
        self.assertEqual(self.tournament1.name, "Group Stage")
        self.assertEqual(self.tournament1.event, self.event1)
        self.assertEqual(str(self.tournament1), "Group Stage")

    def test_match_creation(self):
        self.assertEqual(self.match1.team1, self.team1)
        self.assertEqual(self.match1.team2, self.team2)
        self.assertEqual(self.match1.tournament, self.tournament1)
        self.assertEqual(self.match1.status, Match.STATUS_SCHEDULED)
        self.assertIsNone(self.match1.score1)
        team1_name = getattr(self.match1.team1, 'name', 'N/A')
        team2_name = getattr(self.match1.team2, 'name', 'N/A')
        dt_str = self.match1.match_datetime.strftime('%Y-%m-%d %H:%M') if self.match1.match_datetime else 'N/A'
        self.assertEqual(str(self.match1), f"{team1_name} vs {team2_name} ({dt_str})")


    def test_match_set_result(self):
        self.match1.set_result(3, 1)
        self.assertEqual(self.match1.score1, 3)
        self.assertEqual(self.match1.score2, 1)
        self.assertEqual(self.match1.status, Match.STATUS_FINISHED)

    def test_match_clean_validation(self):
        team1_id = self.team1.id
        with self.assertRaises(ValidationError):
            match_invalid = Match(team1_id=team1_id, team2_id=team1_id, match_datetime=timezone.now())
            match_invalid.clean()

    def test_player_stats_update(self):
        stats = self.player1.statistics
        stats.update_stats(goals=1, assists=1, played=True)
        self.assertEqual(stats.goals, 1)
        self.assertEqual(stats.assists, 1)
        self.assertEqual(stats.games_played, 1)


class FormValidationTests(TestCase):

    def setUp(self):
        self.team1 = create_team(name="Form Team 1")
        self.team2 = create_team(name="Form Team 2")

    def test_event_form_valid(self):
        form_data = {
            'name': 'Valid Event',
            'location': 'Venue',
            'start_date': date(2025, 6, 1),
            'end_date': date(2025, 6, 8),
            'teams': [self.team1.id, self.team2.id]
        }
        form = EventForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)

    def test_event_form_invalid_dates(self):
        form_data = {
            'name': 'Invalid Event',
            'start_date': date(2025, 6, 8),
            'end_date': date(2025, 6, 1)
        }
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('end_date', form.errors)

    def test_team_form_valid(self):
        form_data = {'name': 'Valid Team', 'coach': 'Coach'}
        form = TeamForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_player_form_valid_with_stats(self):
        form_data = {
            'name': 'Valid Player',
            'age': 22,
            'position': 'Midfielder',
            'team': self.team1.id,
            'goals': 5,
            'assists': 3,
            'games_played': 10
        }
        form = PlayerForm(data=form_data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        player = form.save()
        self.assertEqual(Player.objects.count(), 1)
        self.assertEqual(PlayerStatistics.objects.count(), 1)
        self.assertEqual(player.statistics.goals, 5)

    def test_match_result_form_valid(self):
        form_data = {'score1': 2, 'score2': 2}
        form = MatchResultForm(data=form_data)
        self.assertTrue(form.is_valid())


    def test_match_result_form_invalid_score(self):
        form_data = {'score1': -1, 'score2': 2}
        form = MatchResultForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_tournament_form_valid(self):
         form_data = {
             'name': 'Valid Tournament',
             'teams': [self.team1.id]
         }
         form = TournamentForm(data=form_data)
         self.assertTrue(form.is_valid())


class ServiceLogicTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.team_a = create_team(name="Service Team A")
        cls.team_b = create_team(name="Service Team B")
        cls.team_c = create_team(name="Service Team C")
        cls.player_a1 = create_player(cls.team_a, name="Player A1")
        cls.player_b1 = create_player(cls.team_b, name="Player B1")
        cls.tournament = create_tournament(name="Service Cup")
        cls.tournament.teams.add(cls.team_a, cls.team_b, cls.team_c)

        cls.match_ab = create_match(cls.team_a, cls.team_b, cls.tournament, days_offset=-2, status=Match.STATUS_FINISHED, score1=3, score2=0)
        cls.match_ac = create_match(cls.team_a, cls.team_c, cls.tournament, days_offset=-1, status=Match.STATUS_FINISHED, score1=1, score2=1)

    def setUp(self):
         self.match_bc_scheduled = create_match(self.team_b, self.team_c, self.tournament, days_offset=1, status=Match.STATUS_SCHEDULED)


    def test_tournament_manager_standings(self):
        manager = TournamentManager(tournament_id=self.tournament.id)
        standings = manager.calculate_standings()

        self.assertEqual(len(standings), 3)
        self.assertEqual(standings[0]['team'], self.team_a)
        self.assertEqual(standings[0]['points'], 4)
        self.assertEqual(standings[0]['gd'], 3)

        self.assertEqual(standings[1]['team'], self.team_c)
        self.assertEqual(standings[1]['points'], 1)
        self.assertEqual(standings[1]['gd'], 0)

        self.assertEqual(standings[2]['team'], self.team_b)
        self.assertEqual(standings[2]['points'], 0)
        self.assertEqual(standings[2]['gd'], -3)

    def test_schedule_generator_factory_round_robin(self):
        generator = create_schedule_generator('round_robin')
        self.assertIsInstance(generator._strategy, RoundRobinStrategy)
        teams = [self.team_a, self.team_b, self.team_c]
        start_date = date(2025, 7, 1)
        schedule = generator.generate_schedule(teams, start_date)
        self.assertEqual(len(schedule), 3)

    def test_schedule_generator_factory_knockout(self):
        team_d = create_team(name="Service Team D")
        generator = create_schedule_generator('knockout')
        self.assertIsInstance(generator._strategy, KnockoutStrategy)
        teams = [self.team_a, self.team_b, self.team_c, team_d]
        start_date = date(2025, 7, 1)
        schedule = generator.generate_schedule(teams, start_date)
        self.assertEqual(len(schedule), 2)

    def test_create_matches_for_tournament(self):
        generator = create_schedule_generator('round_robin')
        start_date = date(2025, 7, 10)
        new_tournament = create_tournament(name="Match Gen Test")
        new_tournament.teams.add(self.team_a, self.team_b)
        Match.objects.filter(tournament=new_tournament).delete()
        created_matches = generator.create_matches_for_tournament(new_tournament, start_date)
        self.assertEqual(len(created_matches), 1)
        self.assertEqual(Match.objects.filter(tournament=new_tournament).count(), 1)
        self.assertEqual(created_matches[0].status, Match.STATUS_SCHEDULED)

    def test_report_generator_tournament_results(self):
        reporter = TournamentResultsReport()
        report = reporter.generate(tournament_id=self.tournament.id)
        self.assertIsNotNone(report)
        self.assertIn(self.tournament.name, report)
        self.assertIn(f"{self.team_a.name} 3 - 0 {self.team_b.name}", report)
        self.assertIn(f"{self.team_a.name} 1 - 1 {self.team_c.name}", report)
        self.assertNotIn(self.team_b.name + " vs " + self.team_c.name, report)

    def test_report_generator_player_stats(self):
        self.player_a1.statistics.goals = 5
        self.player_a1.statistics.assists = 2
        self.player_a1.statistics.games_played = 3
        self.player_a1.statistics.save()
        self.player_b1.statistics.goals = 1
        self.player_b1.statistics.assists = 0
        self.player_b1.statistics.games_played = 2
        self.player_b1.statistics.save()

        reporter = PlayerStatisticsReport()
        report = reporter.generate(top_n=5)
        self.assertIsNotNone(report)

        player_count_with_stats = PlayerStatistics.objects.filter(player__in=[self.player_a1, self.player_b1]).count()
        expected_title_line = f"=== Звіт: Топ-{player_count_with_stats} гравців за голами (всіх команд) ==="
        self.assertIn(expected_title_line, report)

        self.assertRegex(report, rf"{re.escape(self.player_a1.name)}\s+{re.escape(self.team_a.name)}\s+5\s+2\s+3")
        self.assertRegex(report, rf"{re.escape(self.player_b1.name)}\s+{re.escape(self.team_b.name)}\s+1\s+0\s+2")


    def test_recommendation_system(self):
        self.player_a1.age = 35
        self.player_a1.save()
        recommender = RecommendationSystem(team_id=self.team_a.id)
        recommendations = recommender.generate_recommendations(save_recommendation=False)
        self.assertIn("високий середній вік", recommendations.lower())

    def test_match_simulator(self):
        simulator = SimpleMatchSimulator(self.match_bc_scheduled)
        result = simulator.simulate()
        self.assertIsNotNone(result)
        self.assertIsInstance(result[0], int)
        self.assertIsInstance(result[1], int)

    def test_command_record_result_execute_and_undo(self):
        match_to_record = create_match(self.team_a, self.team_b, status=Match.STATUS_SCHEDULED, tournament=self.tournament, days_offset=5)
        initial_status = match_to_record.status
        initial_score1 = match_to_record.score1

        player_a_id = str(self.player_a1.id)
        command = RecordMatchResultCommand(
            match_id=match_to_record.id,
            score1=4, score2=2,
            scorers1_ids=[player_a_id]
        )

        execution_success = command.execute()
        self.assertTrue(execution_success)
        match_to_record.refresh_from_db()
        self.assertEqual(match_to_record.status, Match.STATUS_FINISHED)
        self.assertEqual(match_to_record.score1, 4)
        self.assertEqual(match_to_record.score2, 2)
        self.player_a1.statistics.refresh_from_db()

        undo_success = command.undo()
        self.assertTrue(undo_success)
        match_to_record.refresh_from_db()
        self.assertEqual(match_to_record.status, initial_status)
        self.assertEqual(match_to_record.score1, initial_score1)

    def test_command_simulate_result_execute_and_undo(self):
        match_to_sim = self.match_bc_scheduled
        initial_status = match_to_sim.status
        initial_score1 = match_to_sim.score1

        command = SimulateMatchResultCommand(match_id=match_to_sim.id)

        execution_success = command.execute()
        self.assertTrue(execution_success)
        match_to_sim.refresh_from_db()
        self.assertEqual(match_to_sim.status, Match.STATUS_FINISHED)
        self.assertIsNotNone(match_to_sim.score1)

        undo_success = command.undo()
        self.assertTrue(undo_success)
        match_to_sim.refresh_from_db()
        self.assertEqual(match_to_sim.status, initial_status)
        self.assertEqual(match_to_sim.score1, initial_score1)


class ViewAccessAndFormTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.team1 = create_team(name="View Team 1")
        cls.team2 = create_team(name="View Team 2")
        cls.player1 = create_player(cls.team1, name="View Player 1")
        cls.event1 = create_event(name="View Event 1")
        cls.tournament1 = create_tournament(name="View Tournament 1", event=cls.event1)
        cls.tournament1.teams.add(cls.team1, cls.team2)
        cls.match_finished_view = create_match(cls.team1, cls.team2, cls.tournament1, status=Match.STATUS_FINISHED, score1=1, score2=0, days_offset=-5)
        cls.match_scheduled_view = create_match(cls.team1, cls.team2, cls.tournament1, status=Match.STATUS_SCHEDULED, days_offset=2)



    def test_index_view(self):
        response = self.client.get(reverse('simulator:index'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/index.html')
        self.assertContains(response, "Вітаємо")

    def test_event_list_view(self):
        response = self.client.get(reverse('simulator:event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/event_list.html')
        self.assertContains(response, self.event1.name)

    def test_team_list_view(self):
        response = self.client.get(reverse('simulator:team_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/team_list.html')
        self.assertContains(response, self.team1.name)

    def test_player_list_view(self):
        response = self.client.get(reverse('simulator:player_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/player_list.html')
        self.assertContains(response, self.player1.name)

    def test_tournament_list_view(self):
        response = self.client.get(reverse('simulator:tournament_list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/tournament_list.html')
        self.assertContains(response, self.tournament1.name)

    def test_event_detail_view(self):
        response = self.client.get(reverse('simulator:event_detail', args=[self.event1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/event_detail.html')
        self.assertContains(response, self.event1.name)

    def test_team_detail_view(self):
        response = self.client.get(reverse('simulator:team_detail', args=[self.team1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/team_detail.html')
        self.assertContains(response, self.team1.name)
        self.assertContains(response, self.player1.name)

    def test_player_detail_view(self):
         response = self.client.get(reverse('simulator:player_detail', args=[self.player1.id]))
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'simulator/player_detail.html')
         self.assertContains(response, self.player1.name)

    def test_tournament_detail_view(self):
         response = self.client.get(reverse('simulator:tournament_detail', args=[self.tournament1.id]))
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'simulator/tournament_detail.html')
         self.assertContains(response, self.tournament1.name)
         self.assertContains(response, self.match_scheduled_view.team1.name)

    def test_match_detail_view(self):
         response = self.client.get(reverse('simulator:match_detail', args=[self.match_scheduled_view.id]))
         self.assertEqual(response.status_code, 200)
         self.assertTemplateUsed(response, 'simulator/match_detail.html')
         self.assertContains(response, self.match_scheduled_view.team1.name)
         self.assertContains(response, "Заплановано")

    def test_event_create_view_post_success(self):
        event_count_before = Event.objects.count()
        response = self.client.post(reverse('simulator:event_create'), {
            'name': 'New Event From Test',
            'location': 'Test Venue',
            'start_date': '2025-08-01',
            'end_date': '2025-08-08',
            'teams': [self.team1.id]
        })
        self.assertEqual(Event.objects.count(), event_count_before + 1)
        new_event = Event.objects.latest('start_date')
        self.assertRedirects(response, reverse('simulator:event_detail', args=[new_event.id]))

    def test_event_create_view_post_fail(self):
        response = self.client.post(reverse('simulator:event_create'), {
            'name': 'Fail Event',
            'start_date': '2025-08-08',
            'end_date': '2025-08-01'
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/event_form.html')

    def test_team_create_view_post_success(self):
         team_count_before = Team.objects.count()
         response = self.client.post(reverse('simulator:team_create'), {
             'name': 'New Team From Test',
             'coach': 'Test Coach'
         })
         self.assertEqual(Team.objects.count(), team_count_before + 1)
         new_team = Team.objects.get(name='New Team From Test')
         self.assertRedirects(response, reverse('simulator:team_detail', args=[new_team.id]))

    def test_tournament_generate_schedule_view(self):
         test_tournament = create_tournament(name="Gen Sched Test Tourn View")
         test_tournament.teams.add(self.team1, self.team2)
         match_count_before = Match.objects.filter(tournament=test_tournament).count()
         self.assertEqual(match_count_before, 0)

         response = self.client.post(reverse('simulator:tournament_generate_schedule', args=[test_tournament.id]), {
             'start_date': '2025-09-01',
             'strategy': 'round_robin'
         })
         self.assertEqual(response.status_code, 302)
         self.assertEqual(response.url, reverse('simulator:tournament_detail', args=[test_tournament.id]))
         self.assertEqual(Match.objects.filter(tournament=test_tournament).count(), 1)


    def test_match_record_result_view_post(self):
        match_sched = create_match(self.team1, self.team2, self.tournament1, status=Match.STATUS_SCHEDULED, days_offset=3)
        self.assertEqual(match_sched.status, Match.STATUS_SCHEDULED)
        response = self.client.post(reverse('simulator:match_record_result', args=[match_sched.id]), {
            'score1': 5,
            'score2': 1
        })
        redirect_url = reverse('simulator:tournament_detail', args=[self.tournament1.id])
        self.assertRedirects(response, redirect_url)
        match_sched.refresh_from_db()
        self.assertEqual(match_sched.status, Match.STATUS_FINISHED)
        self.assertEqual(match_sched.score1, 5)

    def test_match_simulate_view_post(self):
         match_to_sim = create_match(self.team1, self.team2, self.tournament1, status=Match.STATUS_SCHEDULED, days_offset=10)
         self.assertEqual(match_to_sim.status, Match.STATUS_SCHEDULED)
         response = self.client.post(reverse('simulator:match_simulate', args=[match_to_sim.id]))
         self.assertRedirects(response, reverse('simulator:tournament_detail', args=[self.tournament1.id]))
         match_to_sim.refresh_from_db()
         self.assertEqual(match_to_sim.status, Match.STATUS_FINISHED)
         self.assertIsNotNone(match_to_sim.score1)

    def test_team_recommendations_view(self):
        response = self.client.get(reverse('simulator:team_recommendations', args=[self.team1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/team_recommendations.html')
        self.assertContains(response, f"Рекомендації для команди: {self.team1.name}")

    def test_tournament_standings_view(self):
        response = self.client.get(reverse('simulator:tournament_standings', args=[self.tournament1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'simulator/tournament_standings.html')
        self.assertContains(response, f"Турнірна таблиця: {self.tournament1.name}")
        self.assertContains(response, self.team1.name)

    def test_detail_view_404(self):
        random_uuid = uuid.uuid4()
        response = self.client.get(reverse('simulator:team_detail', args=[random_uuid]))
        self.assertEqual(response.status_code, 404)


class SignalEffectTests(TestCase):

    def test_standings_update_on_match_finish(self):
        team1 = create_team("Signal Team 1")
        team2 = create_team("Signal Team 2")
        tournament = create_tournament("Signal Tourn")
        tournament.teams.add(team1, team2)
        match = create_match(team1, team2, tournament, status=Match.STATUS_SCHEDULED)

        self.assertEqual(tournament.standings, {})

        command = RecordMatchResultCommand(match_id=match.id, score1=2, score2=1)
        command.execute()

        tournament.refresh_from_db()
        self.assertNotEqual(tournament.standings, {})
        self.assertIn('table', tournament.standings)
        self.assertEqual(len(tournament.standings['table']), 2)
        team1_entry = next((t for t in tournament.standings['table'] if t['team_name'] == team1.name), None)
        team2_entry = next((t for t in tournament.standings['table'] if t['team_name'] == team2.name), None)
        self.assertIsNotNone(team1_entry)
        self.assertIsNotNone(team2_entry)
        self.assertEqual(team1_entry['points'], 3)
        self.assertEqual(team2_entry['points'], 0)