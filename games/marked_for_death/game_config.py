"""Marked for Death game configuration (based on v0.5 Math Design Document)."""

from src.config.config import Config
from src.config.distributions import Distribution
from src.config.config import BetMode
import os


class GameConfig(Config):
    """Marked for Death configuration class."""

    def __init__(self):
        super().__init__()
        self.game_id = "marked_for_death"
        self.provider_number = 0
        self.working_name = "Marked for Death"
        self.wincap = 25000
        self.win_type = "ways"
        self.rtp = 0.9673
        self.construct_paths()

        # Force reels_path to always be next to this file.
        # The base class computes it based on where the *library* is installed,
        # which is wrong when developing the game separately or when the package
        # is in a venv/src layout.
        self.reels_path = os.path.join(os.path.dirname(__file__), "reels")

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels

        # Board and Symbol Properties
        self.paytable = {
            (5, "H1"): 500,
            (4, "H1"): 100,
            (3, "H1"): 20,
            (5, "H2"): 300,
            (4, "H2"): 80,
            (3, "H2"): 15,
            (5, "H3"): 200,
            (4, "H3"): 50,
            (3, "H3"): 12,
            (5, "H4"): 150,
            (4, "H4"): 40,
            (3, "H4"): 10,
            (5, "L1"): 80,
            (4, "L1"): 20,
            (3, "L1"): 5,
            (5, "L2"): 60,
            (4, "L2"): 15,
            (3, "L2"): 4,
            (5, "L3"): 50,
            (4, "L3"): 12,
            (3, "L3"): 3,
            (5, "L4"): 40,
            (4, "L4"): 10,
            (3, "L4"): 3,
            (5, "L5"): 30,
            (4, "L5"): 8,
            (3, "L5"): 2,
        }

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": [], "marked": []}

        self.freespin_triggers = {
            self.basegame_type: {3: 12, 4: 14, 5: 16},
            self.freegame_type: {3: 12, 4: 14, 5: 16},
        }
        self.anticipation_triggers = {self.basegame_type: 2, self.freegame_type: 1}

        # Reels (placeholders copied from example; replace with proper 4-row strips per v0.5)
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(os.path.join(self.reels_path, f))

        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(
                        criteria="wincap",
                        quota=0.001,
                        win_criteria=self.wincap,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 100, 4: 20, 5: 5},
                            "force_wincap": True,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="freegame",
                        quota=0.1,
                        conditions={
                            "reel_weights": {
                                self.basegame_type: {"BR0": 1},
                                self.freegame_type: {"FR0": 1},
                            },
                            "scatter_triggers": {3: 100, 4: 20, 5: 5},
                            "force_wincap": False,
                            "force_freegame": True,
                        },
                    ),
                    Distribution(
                        criteria="0",
                        quota=0.4,
                        win_criteria=0.0,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                        },
                    ),
                ],
            ),
        ]
