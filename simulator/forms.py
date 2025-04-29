from django import forms
from django.core.exceptions import ValidationError
from .models import Event, Team, Player, Match, PlayerStatistics, Tournament 

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'location', 'start_date', 'end_date', 'teams']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'teams': forms.SelectMultiple(attrs={'size': '10'}),
        }
        help_texts = {
            'teams': 'Утримуйте Ctrl (або Cmd на Mac) для вибору декількох команд.',
        }

    def clean_end_date(self):
        """Перевірка, чи дата кінця не раніше дати початку."""
        start_date = self.cleaned_data.get('start_date')
        end_date = self.cleaned_data.get('end_date')
        if start_date and end_date and end_date < start_date:
            raise ValidationError("Дата кінця не може бути раніше дати початку.")
        return end_date

class TeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name', 'coach']

class PlayerForm(forms.ModelForm):
    goals = forms.IntegerField(required=False, label="Голи (Статистика)", initial=0)
    assists = forms.IntegerField(required=False, label="Асисти (Статистика)", initial=0)
    games_played = forms.IntegerField(required=False, label="Зіграно матчів (Статистика)", initial=0)

    class Meta:
        model = Player
        fields = ['name', 'age', 'position', 'team']

    def __init__(self, *args, **kwargs):
        """Ініціалізація форми з поточними значеннями статистики."""
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
             try:
                 stats = self.instance.statistics
                 self.fields['goals'].initial = stats.goals
                 self.fields['assists'].initial = stats.assists
                 self.fields['games_played'].initial = stats.games_played
             except PlayerStatistics.DoesNotExist:
                 pass

    def save(self, commit=True):
        """Збереження гравця та його статистики."""
        player = super().save(commit=commit)
        if commit:
            goals_val = self.cleaned_data.get('goals')
            assists_val = self.cleaned_data.get('assists')
            games_played_val = self.cleaned_data.get('games_played')

            stats_defaults = {
                'goals': goals_val if goals_val is not None else 0,
                'assists': assists_val if assists_val is not None else 0,
                'games_played': games_played_val if games_played_val is not None else 0,
            }

            PlayerStatistics.objects.update_or_create(
                player=player,
                defaults=stats_defaults
            )
        return player


class MatchResultForm(forms.ModelForm):
    scorers_team1_ids = forms.CharField(
        required=False,
        label="ID гравців команди 1, що забили (через кому)",
        help_text="Введіть ID гравців через кому, напр.: uuid1,uuid2"
    )
    assists_team1_ids = forms.CharField(
        required=False,
        label="ID асистентів команди 1 (через кому)",
        help_text="Введіть ID гравців через кому"
    )
    scorers_team2_ids = forms.CharField(
        required=False,
        label="ID гравців команди 2, що забили (через кому)",
        help_text="Введіть ID гравців через кому"
    )
    assists_team2_ids = forms.CharField(
        required=False,
        label="ID асистентів команди 2 (через кому)",
        help_text="Введіть ID гравців через кому"
    )

    class Meta:
        model = Match
        fields = ['score1', 'score2']

    def clean(self):
        """Валідація рахунку."""
        cleaned_data = super().clean()
        score1 = cleaned_data.get('score1')
        score2 = cleaned_data.get('score2')

        if score1 is None or score2 is None:
            raise ValidationError("Необхідно вказати рахунок для обох команд.")
        if score1 < 0 or score2 < 0:
            raise ValidationError("Рахунок не може бути від'ємним.")
        return cleaned_data
    

class TournamentForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'event', 'teams', 'standings']
        widgets = {
            'event': forms.Select(attrs={'class': 'form-control'}),
            'teams': forms.SelectMultiple(attrs={'size': '10'}),
            'standings': forms.Textarea(attrs={'rows': 5, 'placeholder': 'JSON структура турнірної таблиці (зазвичай генерується автоматично)'}),
        }
        help_texts = {
            'teams': 'Утримуйте Ctrl (або Cmd на Mac) для вибору декількох команд.',
            'standings': 'Це поле зазвичай оновлюється автоматично після завершення матчів. Редагуйте обережно.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'event' in self.fields:
            self.fields['event'].required = not Tournament._meta.get_field('event').blank
        if 'standings' in self.fields:
            self.fields['standings'].required = False

