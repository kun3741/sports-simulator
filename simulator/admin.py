
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

    def player_count_display(self, obj):
        return obj.players.count()
    player_count_display.short_description = "Кількість гравців"

@admin.register(Player)
class PlayerAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'position', 'team', 'get_goals', 'get_assists')
    list_filter = ('team', 'position', 'age')
    search_fields = ('name', 'team__name')
    inlines = [PlayerStatisticsInline] 
    list_select_related = ('team', 'statistics') 

    def get_goals(self, obj):
        return obj.statistics.goals if obj.statistics else 0
    get_goals.short_description = 'Голи'
    get_goals.admin_order_field = 'statistics__goals' 

    def get_assists(self, obj):
        return obj.statistics.assists if obj.statistics else 0
    get_assists.short_description = 'Асисти'
    get_assists.admin_order_field = 'statistics__assists' 


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'start_date', 'end_date', 'teams_count_display')
    list_filter = ('start_date', 'end_date', 'location')
    search_fields = ('name', 'location')
    filter_horizontal = ('teams',) 

    def teams_count_display(self, obj):
        return obj.teams.count()
    teams_count_display.short_description = "Кількість команд"

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'tournament', 'match_datetime', 'status', 'score1', 'score2')
    list_filter = ('status', 'tournament', 'match_datetime')
    search_fields = ('team1__name', 'team2__name', 'tournament__name')
    list_editable = ('status', 'score1', 'score2') 
    list_select_related = ('team1', 'team2', 'tournament') 
    actions = ['mark_as_finished']

    def mark_as_finished(self, request, queryset):
        
        updated_count = 0
        for match in queryset:
            if match.score1 is not None and match.score2 is not None:
                 match.status = Match.STATUS_FINISHED
                 match.save()
                 updated_count += 1
            
        self.message_user(request, f"{updated_count} матчів позначено як завершені.")
    mark_as_finished.short_description = "Позначити вибрані матчі як Завершені (якщо є рахунок)"


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ('name', 'event', 'teams_count_display', 'matches_count_display')
    list_filter = ('event',)
    search_fields = ('name', 'event__name')
    filter_horizontal = ('teams',)

    def teams_count_display(self, obj):
        return obj.teams.count()
    teams_count_display.short_description = "Кількість команд"

    def matches_count_display(self, obj):
        return obj.matches.count()
    matches_count_display.short_description = "Кількість матчів"

@admin.register(PlayerStatistics)
class PlayerStatisticsAdmin(admin.ModelAdmin):
    list_display = ('player', 'games_played', 'goals', 'assists')
    search_fields = ('player__name',)
    

@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = ('team', 'created_at', 'recommendation_text_short')
    list_filter = ('team', 'created_at')
    search_fields = ('team__name', 'recommendation_text')

    def recommendation_text_short(self, obj):
        return obj.recommendation_text[:80] + '...' if len(obj.recommendation_text) > 80 else obj.recommendation_text
    recommendation_text_short.short_description = 'Рекомендація (коротко)'