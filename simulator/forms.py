from django import forms
from django.core.exceptions import ValidationError
from .models import Event, Team, Player, Match, PlayerStatistics, Tournament

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'location', 'start_date', 'end_date', 'teams', 'status', 'results_summary']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'teams': forms.SelectMultiple(attrs={'size': '10'}),
            'results_summary': forms.Textarea(attrs={'rows': 4}),
        }
        help_texts = {
            'teams': 'Утримуйте Ctrl (або Cmd на Mac) для вибору декількох команд.',
        }

    def clean_end_date(self):
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
        player = super().save(commit=commit)
        if commit:
            stats, _ = PlayerStatistics.objects.update_or_create(
                player=player,
                defaults={
                    'goals': self.cleaned_data.get('goals', 0),
                    'assists': self.cleaned_data.get('assists', 0),
                    'games_played': self.cleaned_data.get('games_played', 0),
                }
            )
        return player


class MatchResultForm(forms.Form):
    score1 = forms.IntegerField(label="Рахунок команди 1", min_value=0)
    score2 = forms.IntegerField(label="Рахунок команди 2", min_value=0)
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

    def clean(self):
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
        fields = ['name', 'event', 'teams', 'status', 'winner', 'final_standings']
        widgets = {
            'event': forms.Select(attrs={'class': 'form-control'}),
            'teams': forms.SelectMultiple(attrs={'size': '10'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'winner': forms.Select(attrs={'class': 'form-control'}),
            'final_standings': forms.Textarea(attrs={'rows': 5, 'placeholder': 'JSON структура фінальної таблиці (можна редагувати або копіювати з автоматичної)'}),
        }
        help_texts = {
            'teams': 'Утримуйте Ctrl (або Cmd на Mac) для вибору декількох команд.',
            'final_standings': 'Це поле може бути оновлено автоматично або вручну. Редагуйте обережно, зберігаючи валідну JSON структуру.',
            'winner': 'Переможець може бути визначений автоматично після завершення всіх матчів або встановлений вручну.',
            'status': 'Встановіть статус турніру.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            team_ids = self.instance.teams.values_list('id', flat=True)
            self.fields['winner'].queryset = Team.objects.filter(id__in=team_ids)
            self.fields['winner'].empty_label = "--------- (Не визначено)"
        else:
             self.fields['winner'].queryset = Team.objects.none()
             self.fields['winner'].help_text = "Спочатку додайте команди та збережіть турнір."

        if 'event' in self.fields:
             self.fields['event'].required = not Tournament._meta.get_field('event').blank
        if 'winner' in self.fields:
             self.fields['winner'].required = not Tournament._meta.get_field('winner').blank
        if 'final_standings' in self.fields:
             self.fields['final_standings'].required = False

class MatchForm(forms.ModelForm):
    match_datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
        input_formats=['%Y-%m-%dT%H:%M'],
        label="Дата і час матчу"
    )

    class Meta:
        model = Match
        fields = ['team1', 'team2', 'match_datetime']

    def __init__(self, *args, **kwargs):
        tournament_teams_queryset = kwargs.pop('tournament_teams', None)
        super().__init__(*args, **kwargs)
        if tournament_teams_queryset is not None:
            self.fields['team1'].queryset = tournament_teams_queryset
            self.fields['team2'].queryset = tournament_teams_queryset
        else:
            self.fields['team1'].queryset = Team.objects.all()
            self.fields['team2'].queryset = Team.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        team1 = cleaned_data.get("team1")
        team2 = cleaned_data.get("team2")

        if team1 and team2 and team1 == team2:
            raise ValidationError("Команда не може грати сама з собою.")

        return cleaned_data