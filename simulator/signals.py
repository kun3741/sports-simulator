from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Match, Tournament
from .services.tournament_manager import TournamentManager

@receiver(post_save, sender=Match)
def process_match_finish(sender, instance: Match, created, **kwargs):
    if instance.status == Match.STATUS_FINISHED and instance.score1 is not None and instance.score2 is not None:
        print(f"Сигнал post_save для Match: Матч {instance.id} завершено/оновлено.")

        if instance.tournament:
            tournament = instance.tournament
            print(f"Оновлення турнірної таблиці для турніру ID: {tournament.id}")
            try:
                manager = TournamentManager(tournament_id=tournament.id)
                manager.update_tournament_standings()

                if tournament.status == Tournament.STATUS_ONGOING:
                    tournament.check_and_finish()

            except ValueError as e:
                 print(f"Сигнал: Помилка обробки турніру {tournament.id}: {e}")
            except Exception as e:
                 print(f"Сигнал: Неочікувана помилка при обробці турніру: {e}")
        else:
            print(f"Сигнал: Матч {instance.id} не належить до жодного турніру.")