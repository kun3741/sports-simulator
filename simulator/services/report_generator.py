# simulator/services/report_generator.py
import abc
from django.utils import timezone
from ..models import Match, Player, Team, Tournament, PlayerStatistics

class BaseReportGenerator(abc.ABC):
    def generate(self, output_format='text', **kwargs):
        """Шаблонний метод генерації звіту."""
        print(f"--- Генерація звіту: {self.get_report_title()} ---")
        data = self.fetch_data(**kwargs)
        if not data:
             print("Немає даних для звіту.")
             return None
        formatted_data = self.format_data(data, output_format=output_format, **kwargs)
        print("--- Звіт згенеровано ---")
        return formatted_data

    @abc.abstractmethod
    def get_report_title(self):
        """Повертає заголовок звіту."""
        pass

    @abc.abstractmethod
    def fetch_data(self, **kwargs):
        """Отримує дані, необхідні для звіту."""
        pass

    @abc.abstractmethod
    def format_data(self, data, output_format='text', **kwargs):
        """Форматує отримані дані у вказаний формат."""
        pass


class TournamentResultsReport(BaseReportGenerator):
    def get_report_title(self):
        return "Звіт про результати матчів турніру"

    def fetch_data(self, tournament_id, **kwargs):
        try:
            tournament = Tournament.objects.get(pk=tournament_id)
            matches = Match.objects.filter(
                tournament=tournament,
                status=Match.STATUS_FINISHED
            ).select_related('team1', 'team2').order_by('match_datetime')
            return {'tournament': tournament, 'matches': list(matches)}
        except Tournament.DoesNotExist:
            print(f"Помилка: Турнір з ID {tournament_id} не знайдено.")
            return None

    def format_data(self, data, output_format='text', **kwargs):
        if output_format != 'text':
            return f"Формат {output_format} не підтримується для цього звіту."

        tournament = data['tournament']
        matches = data['matches']
        report_lines = [
            f"=== Звіт: Результати матчів турніру '{tournament.name}' ===",
            f"Дата генерації: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 30,
        ]
        if not matches:
            report_lines.append("Завершені матчі відсутні.")
        else:
            for match in matches:
                report_lines.append(
                    f"{match.match_datetime.strftime('%Y-%m-%d %H:%M')} | "
                    f"{match.team1.name} {match.score1} - {match.score2} {match.team2.name}"
                )
        return "\n".join(report_lines)


class PlayerStatisticsReport(BaseReportGenerator):
    def get_report_title(self):
        return "Звіт про статистику гравців"

    def fetch_data(self, top_n=10, team_id=None, **kwargs):
        stats = PlayerStatistics.objects.select_related('player__team').order_by('-goals')
        if team_id:
             try:
                 team = Team.objects.get(pk=team_id)
                 stats = stats.filter(player__team=team)
             except Team.DoesNotExist:
                 print(f"Попередження: Команда з ID {team_id} не знайдена, показуємо статистику всіх гравців.")

        return {'stats': list(stats[:top_n]), 'team_id': team_id}


    def format_data(self, data, output_format='text', **kwargs):
        if output_format != 'text':
             return f"Формат {output_format} не підтримується для цього звіту."

        stats_list = data['stats']
        team_info = f"команди ID {data['team_id']}" if data['team_id'] else "всіх команд"
        report_lines = [
            f"=== Звіт: Топ-{len(stats_list)} гравців за голами ({team_info}) ===",
            f"Дата генерації: {timezone.now().strftime('%Y-%m-%d %H:%M')}",
            "=" * 30,
            "Ім'я гравця\t\tКоманда\t\tГоли\tАсисти\tМатчі",
            "-" * 60
        ]
        if not stats_list:
            report_lines.append("Статистика гравців відсутня.")
        else:
            for stat in stats_list:
                player = stat.player
                team_name = player.team.name if player and player.team else "N/A"
                player_name = player.name if player else "Невідомий гравець"
                report_lines.append(
                    f"{player_name:<20}\t{team_name:<15}\t{stat.goals:<5}\t{stat.assists:<6}\t{stat.games_played}"
                )
        return "\n".join(report_lines)

