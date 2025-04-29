from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Match
from .services.tournament_manager import TournamentManager

@receiver(post_save, sender=Match)
def update_standings_on_match_finish(sender, instance: Match, created, **kwargs):
    """
    Сигнал, що спрацьовує після збереження об'єкта Match.
    Якщо матч завершено (або його результат оновлено), оновлює турнірну таблицю.
    (!) Оновлення статистики гравців тепер відбувається у views, де є дані про голи/асисти.
    """
    if instance.status == Match.STATUS_FINISHED and instance.score1 is not None and instance.score2 is not None:
        print(f"Сигнал post_save для Match: Матч {instance.id} завершено/оновлено.")

        if instance.tournament:
            print(f"Оновлення турнірної таблиці для турніру ID: {instance.tournament.id}")
            try:
                manager = TournamentManager(tournament_id=instance.tournament.id)
                manager.update_tournament_standings()
            except ValueError as e:
                 print(f"Сигнал: Помилка оновлення таблиці для турніру {instance.tournament.id}: {e}")
            except Exception as e:
                 print(f"Сигнал: Неочікувана помилка при оновленні таблиці: {e}")
        else:
            print(f"Сигнал: Матч {instance.id} не належить до жодного турніру.")


