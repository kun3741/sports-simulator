from django.contrib import admin
from .models import (
    Event, Team, Player, PlayerStatistics, Match, Tournament, Recommendation
)

class PlayerInline(admin.TabularInline):
    model = Player
    extra = 1
    fields = ('name', 'age', 'position')
    show_change_link = True

class PlayerStatisticsInline(admin.StackedInline):
    model = PlayerStatistics
    can_delete = False
    verbose_name_plural = 'Статистика'

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'coach', 'player_count_display')
    search_fields = ('name', 'coach')
    inlines = [PlayerInline]

    @admin.display(description="Кількість гравців")
    def player_count_display(self, obj):
        return obj.players.count()

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'position', 'team', 'get_goals', 'get_assists')
    list_filter = ('team', 'position', 'age')
    search_fields = ('name', 'team__name')
    inlines = [PlayerStatisticsInline]
    list_select_related = ('team', 'statistics')

    @admin.display(description="Голи", ordering='statistics__goals')
    def get_goals(self, obj):
        try:
            return obj.statistics.goals
        except PlayerStatistics.DoesNotExist:
            return 0

    @admin.display(description="Асисти", ordering='statistics__assists')
    def get_assists(self, obj):
        try:
            return obj.statistics.assists
        except PlayerStatistics.DoesNotExist:
            return 0

class MatchInline(admin.TabularInline):
    model = Match
    extra = 0
    fields = ('team1', 'team2', 'match_datetime', 'status', 'score1', 'score2')
    readonly_fields = ('team1', 'team2', 'match_datetime')
    show_change_link = True
    fk_name = 'tournament'

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'start_date', 'end_date', 'status', 'teams_count_display')
    list_filter = ('status', 'start_date', 'end_date', 'location')
    search_fields = ('name', 'location')
    filter_horizontal = ('teams',)
    list_editable = ('status',)
    fieldsets = (
        (None, {'fields': ('name', 'location', 'status', 'results_summary')}),
        ('Dates', {'fields': ('start_date', 'end_date')}),
        ('Participants', {'fields': ('teams',)}),
    )

    @admin.display(description="Кількість команд")
    def teams_count_display(self, obj):
        return obj.teams.count()

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tournament', 'match_datetime', 'status', 'get_score')
    list_filter = ('status', 'tournament', 'match_datetime')
    search_fields = ('team1__name', 'team2__name', 'tournament__name')
    list_editable = ('status',)
    list_select_related = ('team1', 'team2', 'tournament')
    actions = ['mark_as_finished', 'mark_as_scheduled', 'mark_as_cancelled']
    fields = ('tournament', 'team1', 'team2', 'match_datetime', 'status', 'score1', 'score2')
    readonly_fields = ('team1', 'team2', 'tournament')

    @admin.display(description="Рахунок")
    def get_score(self, obj):
        if obj.status == Match.STATUS_FINISHED and obj.score1 is not None and obj.score2 is not None:
            return f"{obj.score1} - {obj.score2}"
        return "-"

    @admin.action(description="Позначити вибрані матчі як Завершені")
    def mark_as_finished(self, request, queryset):
        updated_count = 0
        for match in queryset:
            if match.score1 is not None and match.score2 is not None:
                 match.status = Match.STATUS_FINISHED
                 match.save(update_fields=['status'])
                 updated_count += 1
        self.message_user(request, f"{updated_count} матчів позначено як завершені.")

    @admin.action(description="Позначити вибрані матчі як Заплановані")
    def mark_as_scheduled(self, request, queryset):
        updated_count = queryset.update(status=Match.STATUS_SCHEDULED, score1=None, score2=None)
        self.message_user(request, f"{updated_count} матчів позначено як заплановані (рахунок скинуто).")

    @admin.action(description="Позначити вибрані матчі як Скасовані")
    def mark_as_cancelled(self, request, queryset):
        updated_count = queryset.update(status=Match.STATUS_CANCELLED)
        self.message_user(request, f"{updated_count} матчів позначено як скасовані.")


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'status', 'winner', 'teams_count_display', 'matches_count_display')
    list_filter = ('status', 'event',)
    search_fields = ('name', 'event__name', 'winner__name')
    filter_horizontal = ('teams',)
    list_editable = ('status',)
    readonly_fields = ('standings',)
    fieldsets = (
        (None, {'fields': ('name', 'event', 'status', 'winner')}),
        ('Participants', {'fields': ('teams',)}),
        ('Standings', {'fields': ('standings', 'final_standings')}),
    )

    @admin.display(description="Кількість команд")
    def teams_count_display(self, obj):
        return obj.teams.count()

    @admin.display(description="Кількість матчів")
    def matches_count_display(self, obj):
        return obj.matches.count()

@admin.register(PlayerStatistics)
class PlayerStatisticsAdmin(admin.ModelAdmin):
    list_display = ('player', 'games_played', 'goals', 'assists')
    search_fields = ('player__name',)
    readonly_fields = ('player',)


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('team', 'created_at', 'recommendation_text_short')
    list_filter = ('team', 'created_at')
    search_fields = ('team__name', 'recommendation_text')

    @admin.display(description="Рекомендація (коротко)")
    def recommendation_text_short(self, obj):
        return obj.recommendation_text[:80] + '...' if len(obj.recommendation_text) > 80 else obj.recommendation_text