"""Main file for generating results for Marked for Death (v0.5 design)."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import create_stat_sheet
from utils.rgs_verification import execute_all_tests
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    # Memory-friendly settings for 8 vCPU / 32 GB RAM VM (ccx33)
    # - num_threads=4: ~half the cores to leave headroom for OS + main process + avoid OOM
    # - batching_size=1000: limits memory per worker process (each holds ~500 books in RAM for 2000 total sims)
    #   This prevents large in-memory book collections that can trigger OOM killer.
    # - Keep compression=False during sims (zstd can add peak memory).
    # Total peak for sim phase should stay well under 8-10 GB even with real reels + cascades.
    # If still OOM: drop to num_threads=2 and/or batching_size=500.
    # Monitor on VM with: htop or `watch -n1 'free -h; ps aux --sort=-%mem | head'`
    num_threads = 4
    rust_threads = 4
    batching_size = 1000
    compression = False
    profiling = False

    num_sim_args = {
        "base": 2000,
    }

    run_conditions = {
        "run_sims": True,
        "run_optimization": False,
        "run_analysis": False,
        "upload_data": False,
    }
    target_modes = ["base"]

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        OptimizationExecution().run_all_modes(config, target_modes, rust_threads)
        generate_configs(gamestate)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        run(config.game_id, custom_keys=custom_keys)

    if run_conditions["upload_data"]:
        upload_items = {
            "books": True,
            "lookup_tables": True,
            "force_files": True,
            "config_files": True,
        }
        upload_to_aws(
            gamestate,
            target_modes,
            upload_items,
        )
