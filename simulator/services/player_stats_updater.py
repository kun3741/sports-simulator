from ..models import Match, Player, PlayerStatistics
import uuid
import logging

logger = logging.getLogger(__name__)

def _update_single_player_stat(player_id, stat_type):
    try:
        valid_uuid = uuid.UUID(str(player_id))
        player = Player.objects.select_related('statistics').get(pk=valid_uuid)

        stats, created = PlayerStatistics.objects.get_or_create(player=player)
        if created:
            print(f"Створено запис статистики для гравця {player.name}")

        fields_to_update = ['games_played']
        stats.games_played += 1

        if stat_type == 'goal':
             stats.goals += 1
             fields_to_update.append('goals')
        elif stat_type == 'assist':
             stats.assists += 1
             fields_to_update.append('assists')

        stats.save(update_fields=fields_to_update)
        print(f"Оновлено статистику ({stat_type or 'played'}) для {player.name}: {fields_to_update}")

    except Player.DoesNotExist:
        print(f"Помилка оновлення статистики: Гравець з ID {player_id} не знайдений.")
    except PlayerStatistics.MultipleObjectsReturned:
         print(f"Помилка: Знайдено декілька записів статистики для гравця ID {player_id}.")
    except ValueError:
         print(f"Помилка: Некоректний UUID {player_id}")
    except Exception as e:
        logger.error(f"Неочікувана помилка при оновленні статистики для {player_id}: {e}", exc_info=True)
        print(f"Неочікувана помилка при оновленні статистики для {player_id}: {e}")


def update_player_stats_from_match_data(match: Match, scorers1_ids, assists1_ids, scorers2_ids, assists2_ids):
    print(f"[Статистика] Оновлення для матчу {match.id}...")

    processed_players = set()

    # Process scorers and assistants ensuring IDs are strings for set operations
    all_scorers = [str(pid) for pid in (scorers1_ids or []) + (scorers2_ids or [])]
    all_assistants = [str(pid) for pid in (assists1_ids or []) + (assists2_ids or [])]

    for player_id in all_scorers:
         _update_single_player_stat(player_id, 'goal')
         processed_players.add(player_id)

    for player_id in all_assistants:
         # Only update assist if player didn't score (to avoid double game count)
         if player_id not in processed_players:
            _update_single_player_stat(player_id, 'assist')
            processed_players.add(player_id)
         else: # If they scored, just update the assist count without game played again
            try:
                stats = PlayerStatistics.objects.get(player_id=player_id)
                stats.assists +=1
                stats.save(update_fields=['assists'])
                print(f"Оновлено статистику (assist only) для {stats.player.name}: ['assists']")
            except PlayerStatistics.DoesNotExist:
                 print(f"Помилка оновлення асисту: Статистика гравця {player_id} не знайдена.")
            except Exception as e:
                 logger.error(f"Помилка оновлення асисту для {player_id}: {e}", exc_info=True)


    # Get all players involved in the match
    all_involved_player_ids = set()
    try:
        if match.team1:
            all_involved_player_ids.update(str(p.id) for p in match.team1.players.all())
        if match.team2:
            all_involved_player_ids.update(str(p.id) for p in match.team2.players.all())
    except Exception as e:
         logger.error(f"Помилка отримання гравців для матчу {match.id}: {e}", exc_info=True)


    # Update games_played for players who participated but didn't score/assist
    for player_id in all_involved_player_ids:
        if player_id not in processed_players:
             _update_single_player_stat(player_id, None)

    print(f"[Статистика] Оновлення для матчу {match.id} завершено.")