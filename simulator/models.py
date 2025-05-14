from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid

class BaseUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True

class PlayerStatistics(BaseUUIDModel):
    player = models.OneToOneField(
        'Player',
        on_delete=models.CASCADE,
        related_name='statistics',
        verbose_name="Гравець"
    )
    games_played = models.PositiveIntegerField(default=0, verbose_name="Зіграно матчів")
    goals = models.PositiveIntegerField(default=0, verbose_name="Голи")
    assists = models.PositiveIntegerField(default=0, verbose_name="Асисти")

    class Meta:
        verbose_name = "Статистика гравця"
        verbose_name_plural = "Статистики гравців"
        constraints = [
            models.UniqueConstraint(fields=['player'], name='unique_player_stats')
        ]

    def __str__(self):
        player_name = self.player.name if self.player else "Не призначено"
        return f"Статистика для {player_name}"

    def update_stats(self, goals=0, assists=0, played=False):
        if played:
            self.games_played += 1
        self.goals += goals
        self.assists += assists
        self.save()

class Player(BaseUUIDModel):
    name = models.CharField(max_length=200, verbose_name="Ім'я")
    age = models.PositiveIntegerField(verbose_name="Вік")
    position = models.CharField(max_length=100, blank=True, null=True, verbose_name="Позиція")
    team = models.ForeignKey(
        'Team',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='players',
        verbose_name="Команда"
    )

    class Meta:
        verbose_name = "Гравець"
        verbose_name_plural = "Гравці"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.position or 'N/A'})"

    def get_info(self):
        stats_data = "Немає статистики"
        try:
             stats = self.statistics
             stats_data = {
                 'games': stats.games_played,
                 'goals': stats.goals,
                 'assists': stats.assists,
             }
        except PlayerStatistics.DoesNotExist:
             pass
        return {
            'id': self.id, 'name': self.name, 'age': self.age,
            'position': self.position,
            'team': self.team.name if self.team else "Вільний агент",
            'stats': stats_data
        }

class Team(BaseUUIDModel):
    name = models.CharField(max_length=200, unique=True, verbose_name="Назва команди")
    coach = models.CharField(max_length=200, blank=True, null=True, verbose_name="Тренер")

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команди"
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_player(self, player):
        if not isinstance(player, Player): raise TypeError("Можна додати лише об'єкт Player")
        if player.team == self: return
        if player.team is not None: raise ValueError(f"Гравець {player.name} вже належить команді {player.team.name}")
        player.team = self
        player.save()

    def remove_player(self, player):
        if not isinstance(player, Player): raise TypeError("Можна видалити лише об'єкт Player")
        if player.team != self: return
        player.team = None
        player.save()

    def get_players(self):
        return self.players.all()

    def get_info(self):
        return {'id': self.id, 'name': self.name, 'coach': self.coach, 'player_count': self.players.count()}

class Event(BaseUUIDModel):
    STATUS_PLANNED = 'planned'
    STATUS_ONGOING = 'ongoing'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Заплановано'),
        (STATUS_ONGOING, 'Триває'),
        (STATUS_FINISHED, 'Завершено'),
        (STATUS_CANCELLED, 'Скасовано'),
    ]

    name = models.CharField(max_length=255, verbose_name="Назва події")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Місце проведення")
    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата кінця")
    teams = models.ManyToManyField('Team', blank=True, related_name='events', verbose_name="Команди-учасниці")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
        verbose_name="Статус події"
    )
    results_summary = models.TextField(
        blank=True, null=True, verbose_name="Опис результатів події"
    )

    class Meta:
        verbose_name = "Подія"
        verbose_name_plural = "Події"
        ordering = ['start_date', 'name']

    def __str__(self):
        start_str = self.start_date.strftime('%Y-%m-%d') if self.start_date else 'N/A'
        end_str = self.end_date.strftime('%Y-%m-%d') if self.end_date else 'N/A'
        return f"{self.name} ({start_str} - {end_str})"

    def clean(self):
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError("Дата кінця не може бути раніше дати початку.")

    def add_team(self, team):
        if not isinstance(team, Team): raise TypeError("Можна додати лише об'єкт Team")
        self.teams.add(team)

    def remove_team(self, team):
        if not isinstance(team, Team): raise TypeError("Можна видалити лише об'єкт Team")
        self.teams.remove(team)

    def get_teams(self):
        return self.teams.all()

class Match(BaseUUIDModel):
    STATUS_SCHEDULED = 'scheduled'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, 'Заплановано'),
        (STATUS_IN_PROGRESS, 'Триває'),
        (STATUS_FINISHED, 'Завершено'),
        (STATUS_CANCELLED, 'Скасовано'),
    ]

    team1 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='home_matches', verbose_name="Команда 1 (Господарі)")
    team2 = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='away_matches', verbose_name="Команда 2 (Гості)")
    match_datetime = models.DateTimeField(verbose_name="Дата і час матчу")
    score1 = models.PositiveIntegerField(null=True, blank=True, verbose_name="Рахунок команди 1")
    score2 = models.PositiveIntegerField(null=True, blank=True, verbose_name="Рахунок команди 2")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED, verbose_name="Статус матчу")
    tournament = models.ForeignKey('Tournament', on_delete=models.SET_NULL, null=True, blank=True, related_name='matches', verbose_name="Турнір")

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчі"
        ordering = ['match_datetime']
        unique_together = [['tournament', 'team1', 'team2']]

    def __str__(self):
        team1_name = getattr(self.team1, 'name', 'N/A')
        team2_name = getattr(self.team2, 'name', 'N/A')
        dt_str = self.match_datetime.strftime('%Y-%m-%d %H:%M') if self.match_datetime else 'N/A'
        return f"{team1_name} vs {team2_name} ({dt_str})"

    def clean(self):
        if hasattr(self, 'team1_id') and hasattr(self, 'team2_id') and self.team1_id and self.team2_id:
            if self.team1_id == self.team2_id:
                raise ValidationError("Команда не може грати сама з собою.")

    def set_result(self, score1, score2):
        if self.status == self.STATUS_CANCELLED: raise ValueError("Неможливо встановити результат для скасованого матчу.")
        if not isinstance(score1, int) or not isinstance(score2, int) or score1 < 0 or score2 < 0: raise ValueError("Рахунок має бути невід'ємним цілим числом.")
        self.score1 = score1
        self.score2 = score2
        self.status = self.STATUS_FINISHED
        self.save(update_fields=['score1', 'score2', 'status'])

class Tournament(BaseUUIDModel):
    STATUS_PLANNED = 'planned'
    STATUS_ONGOING = 'ongoing'
    STATUS_FINISHED = 'finished'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Заплановано'),
        (STATUS_ONGOING, 'Триває'),
        (STATUS_FINISHED, 'Завершено'),
        (STATUS_CANCELLED, 'Скасовано'),
    ]

    name = models.CharField(max_length=255, verbose_name="Назва турніру")
    teams = models.ManyToManyField('Team', blank=True, related_name='tournaments', verbose_name="Команди-учасниці")
    standings = models.JSONField(
        default=dict, blank=True, verbose_name="Турнірна таблиця (авто)",
        help_text="Розраховується автоматично. Не редагуйте вручну."
    )
    event = models.ForeignKey(Event, on_delete=models.CASCADE, null=True, blank=True, related_name='tournaments', verbose_name="Подія")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
        verbose_name="Статус турніру"
    )
    winner = models.ForeignKey(
        'Team',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='won_tournaments',
        verbose_name="Переможець турніру"
    )
    final_standings = models.JSONField(
        default=dict, blank=True, verbose_name="Фінальна таблиця (офіційна)",
        help_text="Ви можете скопіювати дані з автоматичної таблиці сюди і відредагувати вручну. Зберігайте валідну JSON структуру."
    )

    class Meta:
        verbose_name = "Турнір"
        verbose_name_plural = "Турніри"
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_match(self, match):
        if not isinstance(match, Match): raise TypeError("Можна додати лише об'єкт Match")
        if match.team1 not in self.teams.all() or match.team2 not in self.teams.all(): raise ValueError("Команди матчу повинні бути учасниками турніру.")
        match.tournament = self
        match.save()

    def remove_match(self, match):
        if not isinstance(match, Match): raise TypeError("Можна видалити лише об'єкт Match")
        if match.tournament != self: return
        match.tournament = None
        match.save()

    def get_matches(self):
        return self.matches.all()

    def update_official_standings(self):
        if self.standings and 'table' in self.standings:
            self.final_standings = self.standings
            self.save(update_fields=['final_standings'])
            return True
        return False

    def maybe_determine_winner(self):
        standings_data = self.final_standings.get('table', []) or self.standings.get('table', [])
        if standings_data:
            winner_data = standings_data[0]
            try:
                winner_team = Team.objects.get(id=winner_data.get('team_id'))
                self.winner = winner_team
                self.save(update_fields=['winner'])
                return winner_team
            except Team.DoesNotExist:
                pass
            except Exception:
                pass
        return None

    def check_and_finish(self):
        if self.status == self.STATUS_ONGOING:
            all_matches = self.matches.all()
            if all_matches and all(m.status == Match.STATUS_FINISHED for m in all_matches):
                self.status = self.STATUS_FINISHED
                self.update_official_standings()
                self.maybe_determine_winner()
                self.save(update_fields=['status'])
                print(f"Tournament {self.name} finished automatically.")
                return True
        return False

class Recommendation(BaseUUIDModel):
    team = models.ForeignKey('Team', on_delete=models.CASCADE, related_name='recommendations')
    recommendation_text = models.TextField(verbose_name="Текст рекомендації")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Рекомендація"
        verbose_name_plural = "Рекомендації"
        ordering = ['-created_at']

    def __str__(self):
        team_name = getattr(self.team, 'name', 'N/A')
        created_str = self.created_at.strftime('%Y-%m-%d') if self.created_at else 'N/A'
        return f"Рекомендація для {team_name} від {created_str}"