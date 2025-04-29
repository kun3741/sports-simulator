
from ..models import Team, Player, PlayerStatistics, Recommendation, Match
from django.db.models import Avg, Q, Count
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

class RecommendationSystem:
    def __init__(self, team_id):
        try:
            
            self.team = Team.objects.prefetch_related(
                'players__statistics',
                'home_matches', 
                'away_matches'  
            ).get(pk=team_id)
        except Team.DoesNotExist:
            raise ValueError(f"Команда з ID {team_id} не знайдена.")

    def _get_recent_form(self, num_matches=5):
        
        recent_matches = sorted(
            list(self.team.home_matches.filter(status=Match.STATUS_FINISHED)) +
            list(self.team.away_matches.filter(status=Match.STATUS_FINISHED)),
            key=lambda m: m.match_datetime,
            reverse=True
        )[:num_matches]

        wins = 0
        draws = 0
        losses = 0
        for match in recent_matches:
            if match.team1 == self.team: 
                if match.score1 > match.score2: wins += 1
                elif match.score1 == match.score2: draws += 1
                else: losses += 1
            elif match.team2 == self.team: 
                if match.score2 > match.score1: wins += 1
                elif match.score1 == match.score2: draws += 1
                else: losses += 1
        return {'played': len(recent_matches), 'W': wins, 'D': draws, 'L': losses}


    def generate_recommendations(self, save_recommendation=True):
        recommendations = []
        players = self.team.players.all()
        player_count = players.count()

        
        min_players = 11 
        if player_count == 0:
             return "В команді немає гравців. Терміново потрібен набір!"
        elif player_count < min_players:
            recommendations.append(f"В команді лише {player_count} гравців. Потрібно щонайменше {min_players - player_count} нових гравців для повноцінного складу.")

        
        avg_age = players.aggregate(Avg('age'))['age__avg']
        if avg_age:
            if avg_age > 32:
                recommendations.append(f"Дуже високий середній вік гравців ({avg_age:.1f}). Терміново потрібне омолодження складу.")
            elif avg_age > 29:
                 recommendations.append(f"Високий середній вік гравців ({avg_age:.1f}). Розгляньте можливість залучення 1-2 молодих талантів.")

        
        team_stats = players.aggregate(
            avg_goals=Avg('statistics__goals'),
            avg_assists=Avg('statistics__assists'),
            total_goals=Sum('statistics__goals') 
        )
        team_avg_goals_per_player = team_stats['avg_goals'] or 0

        
        potential_strikers = Player.objects.filter(
            Q(team__isnull=True) | ~Q(team=self.team), 
            statistics__goals__gt=team_avg_goals_per_player + 1 
        ).select_related('statistics', 'team').order_by('-statistics__goals')[:3]

        if potential_strikers:
             player_names = ", ".join([f"{p.name} ({p.statistics.goals} голів, {p.team.name if p.team else 'вільний агент'})" for p in potential_strikers])
             recommendations.append(f"Для підсилення атаки розгляньте таких гравців: {player_names}.")

        
        positions = players.values('position').annotate(count=Count('position'))
        position_dict = {p['position']: p['count'] for p in positions if p['position']}
        
        required_positions = ['Goalkeeper', 'Defender', 'Midfielder', 'Forward'] 
        missing = [pos for pos in required_positions if position_dict.get(pos, 0) == 0]
        if missing:
            recommendations.append(f"Відсутні гравці на позиціях: {', '.join(missing)}. Необхідно знайти підсилення.")
        

        
        form = self._get_recent_form()
        if form['played'] >= 3: 
            win_rate = form['W'] / form['played'] if form['played'] > 0 else 0
            if win_rate < 0.3 and form['L'] > form['W']:
                 recommendations.append(f"Погана поточна форма ({form['W']}W-{form['D']}D-{form['L']}L в останніх {form['played']} матчах). Розгляньте зміни в тактиці або складі.")

        
        final_recommendation_text = "\n".join(f"- {rec}" for rec in recommendations) if recommendations else "На даний момент конкретних рекомендацій немає. Команда виглядає збалансовано."

        if save_recommendation and recommendations:
            try:
                
                Recommendation.objects.filter(team=self.team).delete()
                
                Recommendation.objects.create(
                    team=self.team,
                    recommendation_text=final_recommendation_text
                )
                print(f"Рекомендацію для команди '{self.team.name}' оновлено.")
            except Exception as e:
                print(f"Помилка збереження рекомендації: {e}")

        return final_recommendation_text

