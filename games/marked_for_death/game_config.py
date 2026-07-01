"""Template game configuration file, detailing required user-specified inputs."""

from src.config.config import Config
from src.config.distributions import Distribution
from src.config.config import BetMode


class GameConfig(Config):
    """Template configuration class."""

    def __init__(self):
        super().__init__()
        # Priority 1 foundational settings per IMPLEMENTATION_MAPPING_v1.2.md
        # (sections 2, 5.1, 7): metadata, grid, paytable, special_symbols (incl. "marked"),
        # FS triggers. These are the minimal basics before building cascade logic.
        self.game_id = "marked_for_death"
        self.provider_number = 0
        self.working_name = "Marked for Death"
        self.wincap = 25000
        self.win_type = "ways"
        self.rtp = 0.9673
        self.construct_paths(self.game_id)

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels  # 5 reels × 4 rows per MDD / mapping section 2
        # Board and Symbol Properties
        self.paytable = {
            (5, "H1"): 500, (4, "H1"): 100, (3, "H1"): 20,
            (5, "H2"): 300, (4, "H2"): 80, (3, "H2"): 15,
            (5, "H3"): 200, (4, "H3"): 50, (3, "H3"): 12,
            (5, "H4"): 150, (4, "H4"): 40, (3, "H4"): 10,
            (5, "L1"): 80, (4, "L1"): 20, (3, "L1"): 5,
            (5, "L2"): 60, (4, "L2"): 15, (3, "L2"): 4,
            (5, "L3"): 50, (4, "L3"): 12, (3, "L3"): 3,
            (5, "L4"): 40, (4, "L4"): 10, (3, "L4"): 3,
            (5, "L5"): 30, (4, "L5"): 8, (3, "L5"): 2,
        }  # Exact from mapping section 2 (MDD paytable)

        self.include_padding = True
        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": [], "marked": []}  # Added "marked" per mapping 5.1/5.4 for event emission and attribute tracking

        # Phase 2 - Option B (2026-07-01): Accept higher base hit rate (~55-60%)
        # and rebalance overall RTP/volatility targets instead of forcing ~28% base hit.
        # Core marked fantasy preserved (spawn on 2-3-4, convert to Wild, persistent mult carry + full reel-3 in FS).
        # Current marked_prob locked for this path. Reels tuned aggressively.
        # New targets: Base hit ~55-60%, overall RTP 96.73%, adjust base/FS RTP split and volatility as needed.
        #
        # base: applied to reels 2-4 on initial landing and after each tumble (drops).
        # fs:   higher chance on 2/4; reel 3 fully Marked at every FS spin start.
        self.marked_prob = {
            "base": {"initial": 0.15, "drop": 0.045},
            "fs":   {"initial": 0.13, "drop": 0.035}
        }

        self.fs_reel3_marked_count = 4  # Full vertical Marked stack on reel 3 every FS spin (MDD v0.7 spec)

        self.freespin_triggers = {
            self.basegame_type: {3: 12, 4: 14, 5: 16, 6: 18, 7: 20, 8: 22, 9: 24, 10: 26},
            self.freegame_type: {3: 8, 4: 10, 5: 12, 6: 14, 7: 16, 8: 18, 9: 20, 10: 22}
        }
        # Extend for high scatter counts (possible in long cascades / many S landing, since S usually don't get removed).
        # Use +2 per additional scatter. Prevents KeyError on retrigger with 11+ scatters.
        for gtype in (self.basegame_type, self.freegame_type):
            trig = self.freespin_triggers[gtype]
            max_s = max(trig.keys())
            base = trig[max_s]
            for s in range(max_s + 1, 21):
                trig[s] = base + (s - max_s) * 2
        self.anticipation_triggers = {
            self.basegame_type: 2,
            self.freegame_type: 1
        }  # Priority 1 foundational per IMPLEMENTATION_MAPPING_v1.2.md section 5.1

        # Reels (IMPROVED TESTING REELS - see Option 1 / generate script)
        # ----------------------------------------------------------------
        # Updated 2026-06-30 as first step for realistic testing.
        # - Length: 300 stops/reel (up from 150-stub)
        # - S frequency tuned: BR ~2.5-3% , FR ~4.5% (natural low FS rate, controlled retriggers)
        # - Varied per reel (not clones). Good L/H density for marked_prob to matter.
        # - FRWCAP.csv exists in reels/ but is NOT integrated here yet (has H5 + needs review).
        #   When ready: add "FRWCAP": "FRWCAP.csv" + use in wincap/free dists like 0_0_ways example.
        # These are explicitly **for testing** (not production final reels).
        # Production reels will come from optimization after full cascade+marked+mult impl.
        # Per Option B: base hit rate accepted ~55-60%; reels tuned for distribution/volatility rather than forcing low hit.
        # Generator: reels/generate_improved_reels.py (re-runnable, seeded)
        # See also README.md in this folder for full reel summary + symbol counts.
        reels = {"BR0": "BR0.csv", "FR0": "FR0.csv"}
        self.reels = {}
        for r, f in reels.items():
            self.reels[r] = self.read_reels_csv(str.join("/", [self.reels_path, f]))

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
                            "scatter_triggers": {},
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
                            "scatter_triggers": {},
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
