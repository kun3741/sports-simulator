from ..models import Tournament, Match, Team
from collections import defaultdict

class TournamentManager:
    def __init__(self, tournament_id):
        try:
            self.tournament = Tournament.objects.prefetch_related('teams', 'matches__team1', 'matches__team2').get(pk=tournament_id)
        except Tournament.DoesNotExist:
            raise ValueError(f"Турнір з ID {tournament_id} не знайдено.")

    def calculate_standings(self):
        standings = defaultdict(lambda: {'played': 0, 'won': 0, 'drawn': 0, 'lost': 0, 'gf': 0, 'ga': 0, 'gd': 0, 'points': 0})
        
        for team in self.tournament.teams.all():
            standings[team.id] 

        finished_matches = self.tournament.matches.filter(status=Match.STATUS_FINISHED).select_related('team1', 'team2')

        for match in finished_matches:
            t1_id, t2_id = match.team1.id, match.team2.id
            s1, s2 = match.score1, match.score2

            if s1 is None or s2 is None: continue 


            standings[t1_id]['played'] += 1
            standings[t2_id]['played'] += 1
            standings[t1_id]['gf'] += s1
            standings[t1_id]['ga'] += s2
            standings[t2_id]['gf'] += s2
            standings[t2_id]['ga'] += s1
            standings[t1_id]['gd'] = standings[t1_id]['gf'] - standings[t1_id]['ga']
            standings[t2_id]['gd'] = standings[t2_id]['gf'] - standings[t2_id]['ga']

            if s1 > s2: 
                standings[t1_id]['won'] += 1
                standings[t1_id]['points'] += 3
                standings[t2_id]['lost'] += 1
            elif s2 > s1: 
                standings[t2_id]['won'] += 1
                standings[t2_id]['points'] += 3
                standings[t1_id]['lost'] += 1
            else: 
                standings[t1_id]['drawn'] += 1
                standings[t1_id]['points'] += 1
                standings[t2_id]['drawn'] += 1
                standings[t2_id]['points'] += 1

        teams_map = {team.id: team for team in self.tournament.teams.all()}
        result_list = []
        for team_id, stats in standings.items():
             if team_id in teams_map: 
                stats['team'] = teams_map[team_id]
                result_list.append(stats)


        result_list.sort(key=lambda x: (-x['points'], -x['gd'], -x['gf'], x['team'].name))

        return result_list

    def update_tournament_standings(self):
        standings_data = self.calculate_standings()
        json_standings = [
            {
                'team_id': str(entry['team'].id),
                'team_name': entry['team'].name,
                **{k: v for k, v in entry.items() if k != 'team'} 
            }
            for entry in standings_data
        ]
        self.tournament.standings = {"table": json_standings}
        self.tournament.save(update_fields=['standings'])
        print(f"Турнірна таблиця для '{self.tournament.name}' оновлена.")
        return json_standings

