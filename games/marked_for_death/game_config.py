"""Marked for Death game configuration (based on v0.5 Math Design Document)."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.config import BetMode


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
        self.construct_paths(self.game_id)

        # Force reels_path to always be next to this file.
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
            (5, "L4"): 10,
            (3, "L4"): 3,
            (5, "L5"): 30,
            (4, "L5"): 8,
            (3, "L5"): 2,
        }

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": [], "marked": []}

        self.freespin_triggers = {
            self.basegame_type: {},
            self.freegame_type: {},
        }
        for n in range(3, 21):
            val = 12 + (n - 3) * 2
            self.freespin_triggers[self.basegame_type][n] = val
            self.freespin_triggers[self.freegame_type][n] = val
        self.anticipation_triggers = {self.basegame_type: 2, self.freegame_type: 1}

        # Load reels manually with robust comma stripping
        reel_files = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for name, filename in reel_files.items():
            path = os.path.join(self.reels_path, filename)
            with open(path, "r", encoding="utf-8") as f:
                symbols = []
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    # Remove trailing comma if present (supports both formats)
                    if line.endswith(","):
                        line = line[:-1].strip()
                    if line:
                        symbols.append(line)
            self.reels[name] = symbols

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
                            "mult_values": {
                                self.basegame_type: [1],
                                self.freegame_type: [1],
                            },
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
                            "mult_values": {
                                self.basegame_type: [1],
                                self.freegame_type: [1],
                            },
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
                            "mult_values": {
                                self.basegame_type: [1],
                                self.freegame_type: [1],
                            },
                        },
                    ),
                    Distribution(
                        criteria="basegame",
                        quota=0.5,
                        conditions={
                            "reel_weights": {self.basegame_type: {"BR0": 1}},
                            "force_wincap": False,
                            "force_freegame": False,
                            "mult_values": {
                                self.basegame_type: [1],
                                self.freegame_type: [1],
                            },
                        },
                    ),
                ],
            ),
        ]
