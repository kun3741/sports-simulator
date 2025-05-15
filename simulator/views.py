from django.shortcuts import render, get_object_or_404, redirect
from django.core.exceptions import ValidationError
from django.http import HttpResponse, Http404, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db import IntegrityError
from django.core.management import call_command

from .models import Event, Team, Player, Tournament, Match, PlayerStatistics
from .forms import EventForm, TeamForm, PlayerForm, MatchResultForm, TournamentForm, MatchForm
from .services.tournament_manager import TournamentManager
from .services.report_generator import TournamentResultsReport
from .services.schedule_generator import create_schedule_generator
from .services.recommendation_system import RecommendationSystem
from .services.commands import RecordMatchResultCommand, SimulateMatchResultCommand

def index(request):
    num_events = Event.objects.count()
    num_teams = Team.objects.count()
    num_players = Player.objects.count()
    context = {
        'num_events': num_events,
        'num_teams': num_teams,
        'num_players': num_players,
    }
    return render(request, 'simulator/index.html', context=context)

def populate_data_view(request):
    if request.method == 'POST':
        try:
            call_command('populate_data', '--generate')
            messages.success(request, "Тестові дані успішно згенеровано!")
        except Exception as e:
            messages.error(request, f"Помилка під час генерації даних: {e}")
        return HttpResponseRedirect(reverse('simulator:index'))
    return redirect('simulator:index')

def delete_data_view(request):
    if request.method == 'POST':
        try:
            call_command('populate_data', '--delete')
            messages.success(request, "Тестові дані успішно видалено!")
        except Exception as e:
            messages.error(request, f"Помилка під час видалення даних: {e}")
        return HttpResponseRedirect(reverse('simulator:index'))
    return redirect('simulator:index')

def event_list(request):
    events = Event.objects.order_by('-start_date')
    return render(request, 'simulator/event_list.html', {'events': events})

def team_list(request):
    teams = Team.objects.order_by('name').prefetch_related('players')
    return render(request, 'simulator/team_list.html', {'teams': teams})

def player_list(request):
    players = Player.objects.select_related('team', 'statistics').order_by('name')
    return render(request, 'simulator/player_list.html', {'players': players})

def tournament_create(request):
    if request.method == 'POST':
        form = TournamentForm(request.POST)
        if form.is_valid():
            tournament = form.save()
            messages.success(request, f'Турнір "{tournament.name}" успішно створено.')
            return redirect('simulator:tournament_detail', tournament_id=tournament.id)
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = TournamentForm()
    return render(request, 'simulator/tournament_form.html', {'form': form})

def tournament_update(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    if request.method == 'POST':
        form = TournamentForm(request.POST, instance=tournament)
        if form.is_valid():
            tournament = form.save()
            messages.success(request, f'Турнір "{tournament.name}" успішно оновлено.')
            return redirect('simulator:tournament_detail', tournament_id=tournament.id)
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = TournamentForm(instance=tournament)
    return render(request, 'simulator/tournament_form.html', {'form': form})

def tournament_list(request):
    tournaments = Tournament.objects.select_related('event').prefetch_related('teams', 'matches').order_by('name')
    return render(request, 'simulator/tournament_list.html', {'tournaments': tournaments})

def event_detail(request, event_id):
    event = get_object_or_404(Event.objects.prefetch_related('teams', 'tournaments'), pk=event_id)
    return render(request, 'simulator/event_detail.html', {'event': event})

def team_detail(request, team_id):
    team = get_object_or_404(Team.objects.prefetch_related('players__statistics', 'tournaments'), pk=team_id)
    return render(request, 'simulator/team_detail.html', {'team': team})

def player_detail(request, player_id):
    player = get_object_or_404(Player.objects.select_related('team', 'statistics'), pk=player_id)
    return render(request, 'simulator/player_detail.html', {'player': player})

def tournament_detail(request, tournament_id):
    tournament = get_object_or_404(
        Tournament.objects.select_related('event', 'winner').prefetch_related(
            'teams', 'matches__team1', 'matches__team2'
        ), pk=tournament_id
    )
    standings_table_list = tournament.final_standings.get('table') or tournament.standings.get('table')
    context = {
        'tournament': tournament,
        'standings_table_list': standings_table_list,
    }
    return render(request, 'simulator/tournament_detail.html', context)


def match_detail(request, match_id):
    match = get_object_or_404(Match.objects.select_related('team1', 'team2', 'tournament'), pk=match_id)
    return render(request, 'simulator/match_detail.html', {'match': match})


def tournament_standings(request, tournament_id):
    try:
        manager = TournamentManager(tournament_id)
        standings = manager.calculate_standings()
        tournament = manager.tournament
    except ValueError:
        raise Http404("Турнір не знайдено.")
    except Exception as e:
        print(f"Помилка при розрахунку таблиці: {e}")
        messages.error(request, "Помилка при отриманні турнірної таблиці.")
        return redirect('simulator:tournament_list')

    return render(request, 'simulator/tournament_standings.html', {
        'tournament': tournament,
        'standings': standings
    })

def report_tournament_results(request, tournament_id):
    reporter = TournamentResultsReport()
    try:
        report_text = reporter.generate(tournament_id=tournament_id, output_format='text')
        if report_text is None:
             raise Http404("Не вдалося згенерувати звіт (можливо, турнір не знайдено або немає даних).")
    except Http404:
         raise
    except Exception as e:
        print(f"Помилка генерації звіту: {e}")
        return HttpResponse("Помилка під час генерації звіту.", status=500)

    return HttpResponse(report_text, content_type='text/plain; charset=utf-8')

def event_create(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Подію "{event.name}" успішно створено.')
            return redirect('simulator:event_detail', event_id=event.id)
        else:
             messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = EventForm()
    return render(request, 'simulator/event_form.html', {'form': form})

def team_create(request):
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Команду "{team.name}" успішно створено.')
            return redirect('simulator:team_detail', team_id=team.id)
        else:
             messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = TeamForm()
    return render(request, 'simulator/team_form.html', {'form': form})

def player_create(request):
    if request.method == 'POST':
        form = PlayerForm(request.POST)
        if form.is_valid():
            player = form.save()
            messages.success(request, f'Гравця "{player.name}" успішно створено.')
            return redirect('simulator:player_detail', player_id=player.id)
        else:
             messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = PlayerForm()
    return render(request, 'simulator/player_form.html', {'form': form})


def event_update(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            event = form.save()
            messages.success(request, f'Подію "{event.name}" успішно оновлено.')
            return redirect('simulator:event_detail', event_id=event.id)
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = EventForm(instance=event)
    return render(request, 'simulator/event_form.html', {'form': form})

def team_update(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.method == 'POST':
        form = TeamForm(request.POST, instance=team)
        if form.is_valid():
            team = form.save()
            messages.success(request, f'Команду "{team.name}" успішно оновлено.')
            return redirect('simulator:team_detail', team_id=team.id)
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = TeamForm(instance=team)
    return render(request, 'simulator/team_form.html', {'form': form})

def player_update(request, player_id):
    player = get_object_or_404(Player, pk=player_id)
    if request.method == 'POST':
        form = PlayerForm(request.POST, instance=player)
        if form.is_valid():
            player = form.save()
            messages.success(request, f'Гравця "{player.name}" успішно оновлено.')
            return redirect('simulator:player_detail', player_id=player.id)
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        initial_data = {}
        try:
             stats = player.statistics
             initial_data = {
                 'goals': stats.goals,
                 'assists': stats.assists,
                 'games_played': stats.games_played,
             }
        except PlayerStatistics.DoesNotExist:
             pass
        form = PlayerForm(instance=player, initial=initial_data)
    return render(request, 'simulator/player_form.html', {'form': form})


def match_record_result(request, match_id):
    match = get_object_or_404(Match.objects.select_related('team1', 'team2', 'tournament'), pk=match_id)

    if match.status == Match.STATUS_CANCELLED:
        messages.error(request, "Неможливо редагувати результат для скасованого матчу.")
        return redirect('simulator:match_detail', match_id=match.id)

    if request.method == 'POST':
        form = MatchResultForm(request.POST)
        if form.is_valid():
            score1 = form.cleaned_data['score1']
            score2 = form.cleaned_data['score2']
            scorers1_ids = []
            assists1_ids = []
            scorers2_ids = []
            assists2_ids = []

            command = RecordMatchResultCommand(
                match_id=match.id,
                score1=score1, score2=score2,
                scorers1_ids=scorers1_ids, assists1_ids=assists1_ids,
                scorers2_ids=scorers2_ids, assists2_ids=assists2_ids
            )

            try:
                command.execute()
                messages.success(request, f"Результат матчу {match} успішно збережено.")

                if match.tournament:
                    return redirect('simulator:tournament_detail', tournament_id=match.tournament.id)
                else:
                    return redirect('simulator:match_detail', match_id=match.id)

            except (ValidationError, ValueError) as e:
                messages.error(request, f"Помилка збереження результату: {e}")
            except Exception as e:
                 messages.error(request, f"Неочікувана помилка: {e}")
        else:
             messages.error(request, "Будь ласка, виправте помилки у формі.")
    else:
        initial_data = {}
        if match.score1 is not None:
            initial_data['score1'] = match.score1
        if match.score2 is not None:
            initial_data['score2'] = match.score2
        form = MatchResultForm(initial=initial_data)

    return render(request, 'simulator/match_result_form.html', {
        'form': form,
        'match': match,
    })


def tournament_generate_schedule(request, tournament_id):
    tournament = get_object_or_404(Tournament.objects.prefetch_related('teams'), pk=tournament_id)

    if request.method == 'POST':
        strategy_type = request.POST.get('strategy', 'round_robin')
        start_date_str = request.POST.get('start_date')

        try:
            start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except (ValueError, TypeError):
            messages.error(request, "Некоректний формат дати початку.")
            return redirect('simulator:tournament_detail', tournament_id=tournament.id)

        try:
            generator = create_schedule_generator(strategy_type)
            created_matches = generator.create_matches_for_tournament(tournament, start_date)

            if created_matches:
                messages.success(request, f"Розклад ({strategy_type}) з {len(created_matches)} матчів успішно згенеровано.")
                if tournament.status == Tournament.STATUS_PLANNED:
                    tournament.status = Tournament.STATUS_ONGOING
                    tournament.save(update_fields=['status'])
            else:
                 messages.warning(request, "Не вдалося створити нові матчі (можливо, розклад вже існує або немає команд).")
        except ValueError as e:
             messages.error(request, f"Помилка вибору стратегії: {e}")
        except Exception as e:
            messages.error(request, f"Помилка під час генерації розкладу: {e}")

        return redirect('simulator:tournament_detail', tournament_id=tournament.id)
    else:
        messages.error(request, "Неприпустимий метод запиту для генерації розкладу.")
        return redirect('simulator:tournament_detail', tournament_id=tournament.id)


def team_recommendations(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    recommender = RecommendationSystem(team_id=team.id)
    recommendations_text = recommender.generate_recommendations(save_recommendation=False)

    return render(request, 'simulator/team_recommendations.html', {
        'team': team,
        'recommendations': recommendations_text.split('\n') if recommendations_text else []
    })


def match_simulate(request, match_id):
    if request.method != 'POST':
        messages.error(request, "Неприпустимий метод запиту.")
        try:
             match = Match.objects.get(pk=match_id)
             return redirect('simulator:match_detail', match_id=match.id)
        except Match.DoesNotExist:
             return redirect('simulator:index')

    command = SimulateMatchResultCommand(match_id=match_id)
    match = None
    try:
        success = command.execute()
        match = command._get_match(match_id)

        if success:
             messages.success(request, f"Матч {match} успішно симульовано та результат записано.")
        else:
             messages.error(request, f"Не вдалося симулювати або записати результат для матчу {match}.")

    except (ValidationError, ValueError) as e:
        messages.error(request, f"Помилка симуляції: {e}")
        try:
            match = command._get_match(match_id)
        except ValueError:
            match = None
    except Exception as e:
         messages.error(request, f"Неочікувана помилка симуляції: {e}")
         try:
            match = Match.objects.get(pk=match_id)
         except Match.DoesNotExist:
             match = None


    if match and match.tournament:
        return redirect('simulator:tournament_detail', tournament_id=match.tournament.id)
    elif match:
        return redirect('simulator:match_detail', match_id=match.id)
    else:
        return redirect('simulator:index')

def match_create(request, tournament_id):
    tournament = get_object_or_404(Tournament, pk=tournament_id)
    tournament_teams = tournament.teams.all()
    if not tournament_teams or tournament_teams.count() < 2:
         messages.error(request, "У турнірі недостатньо команд для створення матчу.")
         return redirect('simulator:tournament_detail', tournament_id=tournament.id)

    if request.method == 'POST':
        form = MatchForm(request.POST, tournament_teams=tournament_teams)
        if form.is_valid():
            match = form.save(commit=False)
            match.tournament = tournament
            match.status = Match.STATUS_SCHEDULED
            try:
                match.save()
                messages.success(request, f'Матч між {match.team1.name} та {match.team2.name} успішно додано до турніру "{tournament.name}".')
                if tournament.status == Tournament.STATUS_PLANNED:
                    tournament.status = Tournament.STATUS_ONGOING
                    tournament.save(update_fields=['status'])
                return redirect('simulator:tournament_detail', tournament_id=tournament.id)
            except IntegrityError:
                 messages.error(request, "Такий матч вже існує в цьому турнірі.")
            except Exception as e:
                 messages.error(request, f"Виникла помилка при збереженні матчу: {e}")
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        form = MatchForm(tournament_teams=tournament_teams)

    return render(request, 'simulator/match_form.html', {'form': form, 'tournament': tournament})