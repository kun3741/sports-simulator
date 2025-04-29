from django.urls import path
from . import views

app_name = 'simulator'

urlpatterns = [
    path('', views.index, name='index'),
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<uuid:event_id>/', views.event_detail, name='event_detail'),
    path('events/<uuid:event_id>/update/', views.event_update, name='event_update'),

    path('teams/', views.team_list, name='team_list'),
    path('teams/create/', views.team_create, name='team_create'),
    path('teams/<uuid:team_id>/', views.team_detail, name='team_detail'),
    path('teams/<uuid:team_id>/update/', views.team_update, name='team_update'),
    path('teams/<uuid:team_id>/recommendations/', views.team_recommendations, name='team_recommendations'),

    path('players/', views.player_list, name='player_list'),
    path('players/create/', views.player_create, name='player_create'),
    path('players/<uuid:player_id>/', views.player_detail, name='player_detail'),
    path('players/<uuid:player_id>/update/', views.player_update, name='player_update'),


    path('tournaments/', views.tournament_list, name='tournament_list'),
    path('tournaments/create/', views.tournament_create, name='tournament_create'),
    path('tournaments/<uuid:tournament_id>/update/', views.tournament_update, name='tournament_update'),
    path('tournaments/<uuid:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('tournaments/<uuid:tournament_id>/standings/', views.tournament_standings, name='tournament_standings'),
    path('tournaments/<uuid:tournament_id>/generate_schedule/', views.tournament_generate_schedule, name='tournament_generate_schedule'),

    path('matches/<uuid:match_id>/', views.match_detail, name='match_detail'),
    path('matches/<uuid:match_id>/record_result/', views.match_record_result, name='match_record_result'),

    path('matches/<uuid:match_id>/simulate/', views.match_simulate, name='match_simulate'),

    path('reports/tournament/<uuid:tournament_id>/results/', views.report_tournament_results, name='report_tournament_results'),
]