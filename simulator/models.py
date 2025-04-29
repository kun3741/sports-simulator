# simulator/models.py
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid # Для унікальних ID, якщо потрібно

# --- Базові класи / Допоміжні ---

class BaseUUIDModel(models.Model):
    """Абстрактна базова модель для використання UUID як первинного ключа."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True # Ця модель не створюватиме таблицю в базі даних

# --- Основні сутності ---

class PlayerStatistics(BaseUUIDModel):
    """Статистика гравця (розширений функціонал)."""
    # !!! ЗМІНА: OneToOneField перенесено сюди !!!
    player = models.OneToOneField(
        'Player',
        on_delete=models.CASCADE, # Якщо гравця видалено, видаляємо і його статистику
        related_name='statistics', # Дозволяє отримати статистику з об'єкту гравця: player.statistics
        verbose_name="Гравець"
        # primary_key=True # Можна зробити ID гравця первинним ключем для статистики, але UUID краще для гнучкості
    )
    games_played = models.PositiveIntegerField(default=0, verbose_name="Зіграно матчів")
    goals = models.PositiveIntegerField(default=0, verbose_name="Голи")
    assists = models.PositiveIntegerField(default=0, verbose_name="Асисти")

    # Агрегація з Player (зв'язок "один до одного", кожен гравець має свою статистику)
    # Зв'язок визначається в моделі Player через OneToOneField
    # Player має доступ до статистики через player.statistics

    class Meta:
        verbose_name = "Статистика гравця"
        verbose_name_plural = "Статистики гравців"
        # Важливо: Переконайтеся, що немає двох записів статистики для одного гравця
        constraints = [
            models.UniqueConstraint(fields=['player'], name='unique_player_stats')
        ]

    def __str__(self):
        # Тепер поле player існує напряму
        player_name = self.player.name if self.player else "Не призначено"
        return f"Статистика для {player_name}"

    def update_stats(self, goals=0, assists=0, played=False):
        """Оновлює статистику гравця."""
        if played:
            self.games_played += 1
        self.goals += goals
        self.assists += assists
        self.save()

class Player(BaseUUIDModel):
    """Клас Гравець."""
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

    # !!! ЗМІНА: Поле statistics видалено звідси. Доступ через related_name 'statistics' !!!
    # statistics = models.OneToOneField(...) # <--- ВИДАЛИТИ ЦЕЙ РЯДОК

    class Meta:
        verbose_name = "Гравець"
        verbose_name_plural = "Гравці"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.position or 'N/A'})"

    def get_info(self):
        """Повертає словник з інформацією про гравця."""
        # Доступ до статистики тепер через related_name
        stats_data = "Немає статистики"
        try:
             # Перевіряємо наявність статистики
             stats = self.statistics # Використовуємо related_name
             stats_data = {
                 'games': stats.games_played,
                 'goals': stats.goals,
                 'assists': stats.assists,
             }
        except PlayerStatistics.DoesNotExist:
             pass # Залишаємо "Немає статистики"

        return {
            'id': self.id,
            'name': self.name,
            'age': self.age,
            'position': self.position,
            'team': self.team.name if self.team else "Вільний агент",
            'stats': stats_data
        }

class Team(BaseUUIDModel):
    """Клас Команда."""
    name = models.CharField(max_length=200, unique=True, verbose_name="Назва команди")
    coach = models.CharField(max_length=200, blank=True, null=True, verbose_name="Тренер")
    # Список гравців реалізовано через ForeignKey в моделі Player (related_name='players')

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команди"
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_player(self, player):
        """Додає гравця до команди."""
        if not isinstance(player, Player):
            raise TypeError("Можна додати лише об'єкт Player")
        if player.team == self:
            print(f"Гравець {player.name} вже у команді {self.name}")
            return # Вже в команді
        if player.team is not None:
             raise ValueError(f"Гравець {player.name} вже належить команді {player.team.name}")

        player.team = self
        player.save()
        print(f"Гравець {player.name} доданий до команди {self.name}")


    def remove_player(self, player):
        """Видаляє гравця з команди."""
        if not isinstance(player, Player):
            raise TypeError("Можна видалити лише об'єкт Player")
        if player.team != self:
            print(f"Гравець {player.name} не належить до команди {self.name}")
            return

        player.team = None # Робимо гравця вільним агентом
        player.save()
        print(f"Гравець {player.name} видалений з команди {self.name}")

    def get_players(self):
        """Повертає QuerySet гравців цієї команди."""
        return self.players.all() # Використовуємо related_name

    def get_info(self):
        """Повертає словник з інформацією про команду."""
        return {
            'id': self.id,
            'name': self.name,
            'coach': self.coach,
            'player_count': self.players.count(),
        }


class Event(BaseUUIDModel):
    """Клас Змагання (Подія)."""
    name = models.CharField(max_length=255, verbose_name="Назва змагання")
    location = models.CharField(max_length=255, blank=True, null=True, verbose_name="Місце проведення")
    start_date = models.DateField(verbose_name="Дата початку")
    end_date = models.DateField(verbose_name="Дата кінця")

    # Зв'язок з командами (Агрегація: змагання *може* містити команди, команди можуть існувати окремо)
    teams = models.ManyToManyField(
        Team,
        blank=True, # Дозволяє створювати змагання без команд спочатку
        related_name='events',
        verbose_name="Команди-учасниці"
    )

    class Meta:
        verbose_name = "Змагання"
        verbose_name_plural = "Змагання"
        ordering = ['start_date', 'name']

    def __str__(self):
        return f"{self.name} ({self.start_date} - {self.end_date})"

    def clean(self):
        """Валідація даних моделі."""
        if self.end_date < self.start_date:
            raise ValidationError("Дата кінця не може бути раніше дати початку.")

    def add_team(self, team):
        """Додає команду до змагання."""
        if not isinstance(team, Team):
             raise TypeError("Можна додати лише об'єкт Team")
        self.teams.add(team)
        print(f"Команда {team.name} додана до змагання {self.name}")

    def remove_team(self, team):
        """Видаляє команду зі змагання."""
        if not isinstance(team, Team):
            raise TypeError("Можна видалити лише об'єкт Team")
        self.teams.remove(team)
        print(f"Команда {team.name} видалена зі змагання {self.name}")

    def get_teams(self):
        """Повертає QuerySet команд, що беруть участь у змаганні."""
        return self.teams.all()


class Match(BaseUUIDModel):
    """Клас Матч."""
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

    # Зв'язок з командами (Композиція/Агрегація: матч потребує 2 команди)
    team1 = models.ForeignKey(
        Team,
        on_delete=models.CASCADE, # Якщо команду видалено, матч не може відбутись (або SET_NULL?)
        related_name='home_matches',
        verbose_name="Команда 1 (Господарі)"
    )
    team2 = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='away_matches',
        verbose_name="Команда 2 (Гості)"
    )

    match_datetime = models.DateTimeField(verbose_name="Дата і час матчу")
    score1 = models.PositiveIntegerField(null=True, blank=True, verbose_name="Рахунок команди 1")
    score2 = models.PositiveIntegerField(null=True, blank=True, verbose_name="Рахунок команди 2")
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_SCHEDULED,
        verbose_name="Статус матчу"
    )

    # Зв'язок з турніром (Агрегація: матч може належати до турніру)
    tournament = models.ForeignKey(
        'Tournament',
        on_delete=models.SET_NULL, # Матч може існувати поза турніром (товариський)
        null=True,
        blank=True,
        related_name='matches',
        verbose_name="Турнір"
    )

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчі"
        ordering = ['match_datetime']

    def __str__(self):
        return f"{self.team1} vs {self.team2} ({self.match_datetime.strftime('%Y-%m-%d %H:%M')})"

    def clean(self):
        """Валідація: команди не можуть грати самі з собою."""
        if self.team1 == self.team2:
            raise ValidationError("Команда не може грати сама з собою.")
        if self.score1 is not None and self.score2 is not None and self.status != self.STATUS_FINISHED:
            # Логіка: якщо є рахунок, статус має бути "Завершено" (можна налаштувати)
            pass # Або автоматично встановити статус, або видати помилку
        if (self.score1 is None or self.score2 is None) and self.status == self.STATUS_FINISHED:
             raise ValidationError("Для завершеного матчу потрібен результат.")


    def set_result(self, score1, score2):
        """Встановлює результат матчу і змінює статус."""
        if self.status == self.STATUS_CANCELLED:
            raise ValueError("Неможливо встановити результат для скасованого матчу.")
        if score1 < 0 or score2 < 0:
             raise ValueError("Рахунок не може бути від'ємним.")

        self.score1 = score1
        self.score2 = score2
        self.status = self.STATUS_FINISHED
        self.save()
        # Тут можна викликати сигнал для оновлення статистики/турнірної таблиці
        # match_finished.send(sender=self.__class__, match=self)


class Tournament(BaseUUIDModel):
    """Клас Турнір."""
    name = models.CharField(max_length=255, verbose_name="Назва турніру")
    # Список матчів реалізовано через ForeignKey в моделі Match (related_name='matches')
    # Список команд-учасниць (Агрегація)
    teams = models.ManyToManyField(
        Team,
        blank=True,
        related_name='tournaments',
        verbose_name="Команди-учасниці"
    )
    # Турнірне положення може бути складним полем (JSON) або окремою моделлю Standing
    standings = models.JSONField(default=dict, blank=True, verbose_name="Турнірна таблиця")
    # Можна додати посилання на Event, якщо турнір є частиною більшого змагання
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='tournaments',
        verbose_name="Змагання"
    )

    class Meta:
        verbose_name = "Турнір"
        verbose_name_plural = "Турніри"
        ordering = ['name']

    def __str__(self):
        return self.name

    def add_match(self, match):
        """Додає існуючий матч до турніру."""
        if not isinstance(match, Match):
            raise TypeError("Можна додати лише об'єкт Match")
        # Перевірка, чи команди матчу є учасниками турніру
        if match.team1 not in self.teams.all() or match.team2 not in self.teams.all():
            raise ValueError("Команди матчу повинні бути учасниками турніру.")
        match.tournament = self
        match.save()
        print(f"Матч {match} доданий до турніру {self.name}")

    def remove_match(self, match):
        """Видаляє матч з турніру (не видаляє сам матч)."""
        if not isinstance(match, Match):
            raise TypeError("Можна видалити лише об'єкт Match")
        if match.tournament != self:
             print(f"Матч {match} не належить до турніру {self.name}")
             return
        match.tournament = None
        match.save()
        print(f"Матч {match} видалений з турніру {self.name}")

    def get_matches(self):
        """Повертає QuerySet матчів цього турніру."""
        return self.matches.all() # Використовуємо related_name

    # Метод оновлення турнірного положення буде в TournamentManager

# --- Додаткові класи з вимог ---

class Recommendation(BaseUUIDModel):
    """Клас для зберігання згенерованих рекомендацій (якщо потрібно їх зберігати)."""
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='recommendations')
    recommendation_text = models.TextField(verbose_name="Текст рекомендації")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Рекомендація"
        verbose_name_plural = "Рекомендації"
        ordering = ['-created_at']

    def __str__(self):
        return f"Рекомендація для {self.team.name} від {self.created_at.strftime('%Y-%m-%d')}"