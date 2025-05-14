import abc
import uuid
from datetime import datetime
from django.utils import timezone
from django.core.exceptions import ValidationError

from ..models import Match, Player, PlayerStatistics
from .player_stats_updater import update_player_stats_from_match_data, _update_single_player_stat
from .match_simulator import SimpleMatchSimulator
from .tournament_manager import TournamentManager

class Command(abc.ABC):
    def __init__(self):
        self._previous_match_state = {}

    @abc.abstractmethod
    def execute(self):
        pass

    @abc.abstractmethod
    def undo(self):
        pass

    def _get_match(self, match_id):
        try:
            return Match.objects.select_related('team1', 'team2', 'tournament').get(pk=match_id)
        except Match.DoesNotExist:
            raise ValueError(f"Матч з ID {match_id} не знайдено.")

    def _backup_match_state(self, match: Match):
        self._previous_match_state = {
            'score1': match.score1,
            'score2': match.score2,
            'status': match.status,
            'match_datetime': match.match_datetime
        }
        print(f"[Command Backup] Saved state for match {match.id}: {self._previous_match_state}")


    def _restore_match_state(self, match: Match):
        if not self._previous_match_state:
            print(f"[Command Restore] No previous state saved for match {match.id}.")
            return False

        try:
            match.score1 = self._previous_match_state.get('score1')
            match.score2 = self._previous_match_state.get('score2')
            match.status = self._previous_match_state.get('status', Match.STATUS_SCHEDULED)
            match.save(update_fields=['score1', 'score2', 'status'])
            print(f"[Command Restore] Restored state for match {match.id}: {self._previous_match_state}")

            if match.tournament:
                try:
                    manager = TournamentManager(tournament_id=match.tournament.id)
                    manager.update_tournament_standings()
                except Exception as e:
                    print(f"[Command Restore] Error updating standings after undo for tournament {match.tournament.id}: {e}")
            return True
        except Exception as e:
             print(f"[Command Restore] Error restoring state for match {match.id}: {e}")
             return False

    def _update_standings(self, match: Match):
         if match.tournament:
            try:
                manager = TournamentManager(tournament_id=match.tournament.id)
                manager.update_tournament_standings()
            except Exception as e:
                print(f"[Command Update Standings] Error updating standings for tournament {match.tournament.id}: {e}")


class RecordMatchResultCommand(Command):
    def __init__(self, match_id, score1: int, score2: int,
                 scorers1_ids: list = None, assists1_ids: list = None,
                 scorers2_ids: list = None, assists2_ids: list = None):
        super().__init__()
        self.match_id = match_id
        self.score1 = score1
        self.score2 = score2
        self.scorers1_ids = scorers1_ids or []
        self.assists1_ids = assists1_ids or []
        self.scorers2_ids = scorers2_ids or []
        self.assists2_ids = assists2_ids or []
        self._previous_player_stats = {}

    def execute(self):
        print(f"[RecordMatchResultCommand] Executing for match {self.match_id} with score {self.score1}-{self.score2}")
        match = self._get_match(self.match_id)

        if match.status == Match.STATUS_CANCELLED:
            raise ValidationError("Неможливо записати результат для скасованого матчу.")

        self._backup_match_state(match)

        try:
            match.set_result(self.score1, self.score2)

            update_player_stats_from_match_data(
                match=match,
                scorers1_ids=self.scorers1_ids, assists1_ids=self.assists1_ids,
                scorers2_ids=self.scorers2_ids, assists2_ids=self.assists2_ids
            )
            print(f"[RecordMatchResultCommand] Successfully executed for match {self.match_id}")
            return True
        except (ValidationError, ValueError) as e:
            print(f"[RecordMatchResultCommand] Validation Error for match {self.match_id}: {e}")
            raise
        except Exception as e:
            print(f"[RecordMatchResultCommand] Unexpected Error for match {self.match_id}: {e}")
            self._restore_match_state(match)
            raise

    def undo(self):
        print(f"[RecordMatchResultCommand] Undoing for match {self.match_id}")
        match = self._get_match(self.match_id)
        print("[RecordMatchResultCommand] Warning: Player stats undo is not fully implemented.")
        restored = self._restore_match_state(match)
        if restored:
             print(f"[RecordMatchResultCommand] Successfully undone for match {self.match_id}")
        else:
             print(f"[RecordMatchResultCommand] Failed to undo for match {self.match_id}")
        return restored


class SimulateMatchResultCommand(Command):
    def __init__(self, match_id):
        super().__init__()
        self.match_id = match_id
        self._previous_player_stats = {}
        self._simulated_result = None

    def execute(self):
        print(f"[SimulateMatchResultCommand] Executing for match {self.match_id}")
        match = self._get_match(self.match_id)

        if match.status != Match.STATUS_SCHEDULED:
             raise ValidationError("Можна симулювати тільки заплановані матчі.")

        self._backup_match_state(match)

        simulator = SimpleMatchSimulator(match)
        success = simulator.simulate_and_set_result()

        if success:
             match.refresh_from_db()
             self._simulated_result = (match.score1, match.score2)
             print(f"[SimulateMatchResultCommand] Successfully executed for match {self.match_id}. Result: {self._simulated_result}")
             return True
        else:
             print(f"[SimulateMatchResultCommand] Failed to simulate or set result for match {self.match_id}")
             return False

    def undo(self):
        print(f"[SimulateMatchResultCommand] Undoing for match {self.match_id}")
        match = self._get_match(self.match_id)
        print("[SimulateMatchResultCommand] Warning: Player stats undo is not fully implemented.")
        restored = self._restore_match_state(match)
        if restored:
             print(f"[SimulateMatchResultCommand] Successfully undone for match {self.match_id}")
        else:
             print(f"[SimulateMatchResultCommand] Failed to undo for match {self.match_id}")
        return restored