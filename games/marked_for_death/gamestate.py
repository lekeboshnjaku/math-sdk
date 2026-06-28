"""Game logic and event emission for Marked for Death (5x4 1024 Ways + Cascading per v0.5 design)."""

from game_override import GameStateOverride
from src.events.events import reveal_event


class GameState(GameStateOverride):
    """Handle basegame and freegame logic."""

    def run_spin(self, sim: int, simulation_seed=None) -> None:
        self.repeat = True
        attempt = 0
        while self.repeat:
            # Use varying seed per repeat attempt so different boards are generated
            # (important for criteria like win_criteria=0 that require specific outcomes)
            self.reset_seed(sim + attempt * 1000003)
            self.reset_book()
            self.draw_board(emit_event=False)
            self.promote_marked_symbols()
            reveal_event(self)

            self.evaluate_ways_board()
            self.emit_tumble_win_events()
            self.convert_marked_to_wild()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.promote_marked_symbols()
                self.update_global_mult()  # after paid cascade, before next eval
                self.evaluate_ways_board()
                self.emit_tumble_win_events()
                self.convert_marked_to_wild()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            # Check Scatter condition and trigger freegame
            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()
            attempt += 1

        print(f"  Sim {sim} completed after {attempt} attempt(s)", flush=True)
        self.imprint_wins()

    def run_freespin(self) -> None:
        self.reset_fs_spin()
        self.global_multiplier = 1
        self.update_global_mult()  # start new FS round at x2 (and emit)
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board(emit_event=False)
            self.promote_marked_symbols()
            self.force_reel3_marked()
            reveal_event(self)

            self.evaluate_ways_board()
            self.emit_tumble_win_events()
            self.convert_marked_to_wild()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.promote_marked_symbols()
                self.update_global_mult()  # after paid cascade, before next eval
                self.evaluate_ways_board()
                self.emit_tumble_win_events()
                self.convert_marked_to_wild()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()
        self.end_freespin()
