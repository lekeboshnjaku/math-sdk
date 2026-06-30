from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """
    This class is is used to override or extend universal state.py functions.
    e.g: A specific game may have custom book properties to reset
    """

    def reset_book(self):
        """Reset game specific properties"""
        super().reset_book()

    def assign_special_sym_function(self):
        # This game uses a *global* persistent multiplier (x1 base / starts at x2 in FS,
        # +1 after each paid cascade, carries across FS spins). See gamestate.py run_freespin
        # and update_global_mult().
        #
        # There are no per-symbol multipliers (no "M" symbols, and wild "W" should not
        # receive random multipliers). The old template registration for "M"/"W" caused:
        #   KeyError: 'mult_values'   (because no Distribution.conditions had it)
        # when create_symbol("W") was called from reel strips during draw_board.
        self.special_symbol_functions = {}

    def check_game_repeat(self):
        if self.repeat == False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
