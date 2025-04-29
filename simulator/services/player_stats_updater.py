from ..models import Match, Player, PlayerStatistics
import uuid 

def _update_single_player_stat(player_id, stat_type):
    try:
        valid_uuid = uuid.UUID(player_id)
        player = Player.objects.select_related('statistics').get(pk=valid_uuid)
        if not hasattr(player, 'statistics'):
            stats = PlayerStatistics.objects.create(player=player)
            print(f"Створено запис статистики для гравця {player.name}")
        else:
            stats = player.statistics

        update_data = {'played': True} 
        if stat_type == 'goal':
             stats.goals += 1
        elif stat_type == 'assist':
             stats.assists += 1

        stats.games_played += 1 
        stats.save(update_fields=[stat_type + 's' if stat_type else None, 'games_played']) # Оновлюємо тільки потрібні поля
        print(f"Оновлено статистику ({stat_type or 'played'}) для {player.name}")

    except Player.DoesNotExist:
        print(f"Помилка оновлення статистики: Гравець з ID {player_id} не знайдений.")
    except PlayerStatistics.MultipleObjectsReturned:
         print(f"Помилка: Знайдено декілька записів статистики для гравця ID {player_id}.")
    except ValueError:
         print(f"Помилка: Некоректний UUID {player_id}")
    except Exception as e:
        print(f"Неочікувана помилка при оновленні статистики для {player_id}: {e}")


def update_player_stats_from_match_data(match: Match, scorers1_ids, assists1_ids, scorers2_ids, assists2_ids):
    print(f"[Статистика] Оновлення для матчу {match.id}...")

    processed_players = set() 

    for player_id in scorers1_ids + scorers2_ids:
         _update_single_player_stat(player_id, 'goal')
         processed_players.add(player_id)

    for player_id in assists1_ids + assists2_ids:
         _update_single_player_stat(player_id, 'assist')
         processed_players.add(player_id)

    all_involved_player_ids = set(str(p.id) for p in match.team1.players.all()) | \
                              set(str(p.id) for p in match.team2.players.all())

    for player_id in all_involved_player_ids:
        if player_id not in processed_players:
             _update_single_player_stat(player_id, None) # Оновлює тільки games_played

    print(f"[Статистика] Оновлення для матчу {match.id} завершено.")