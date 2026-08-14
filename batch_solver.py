import json
import time
from pathlib import Path

import pandas as pd

from solver import Solver, Puzzle

def run_solver_batch(
    puzzle_file,
    output_file,
    solver_method,
    timeout=None
):
    """
    Run solver over all puzzles with restart support.
    """

    puzzle_file = Path(puzzle_file)
    output_file = Path(output_file)

    # --------------------------
    # Load puzzles
    # --------------------------

    with open(puzzle_file, "r", encoding="utf-8") as f:
        puzzles = json.load(f)


    # --------------------------
    # Load previous results
    # --------------------------

    if output_file.exists():
        stats_df = pd.read_excel(output_file)

        completed = set(stats_df["name"])

        results = stats_df.to_dict("records")

    else:
        completed = set()
        results = []


    # --------------------------
    # Process puzzles
    # --------------------------

    for item in puzzles:

        name = item["name"]

        if name in completed:
            print(f"Skipping {name} (already done)")
            continue


        print(f"Solving {name}...")

        start = time.time()

        try:

            puzzle = Puzzle(
                item["puzzle"],
                verbose=False
            )

            solver = Solver(puzzle)

            solver_method(solver)

            elapsed = time.time() - start


            result = {
                "name": name,
                "solved": solver.solution is not None,
                "timed_out": solver.timed_out,
                "time_seconds": round(elapsed, 3),
                "states_explored": solver.states_explored
            }


        except Exception as e:

            # Keep going if one puzzle breaks
            result = {
                "name": name,
                "solved": False,
                "timed_out": False,
                "time_seconds": None,
                "states_explored": None,
                "error": str(e)
            }


        results.append(result)


        # --------------------------
        # Checkpoint save
        # --------------------------

        pd.DataFrame(results).to_excel(
            output_file,
            index=False
        )

        print(result)


    return pd.DataFrame(results)

puzzles_file = "puzzles.json"


run_solver_batch(puzzles_file,
    "solve_dfs_lcv.xlsx",
    Solver.solve_dfs_lcv)

run_solver_batch(puzzles_file,
    "stats_bfs.xlsx",
    Solver.solve_bfs)

run_solver_batch(puzzles_file,
    "stats_bfs_cache.xlsx",
    Solver.solve_bfs_cache)

run_solver_batch(puzzles_file,
    "stats_dfs.xlsx",
    Solver.solve_dfs)

run_solver_batch(puzzles_file,
    "stats_dfs_cache.xlsx",
    Solver.solve_dfs_cache)

run_solver_batch(puzzles_file,
    "stats_dfs_mrv.xlsx",
    Solver.solve_dfs_mrv)

run_solver_batch(puzzles_file,
    "solve_dfs_diverse.xlsx",
    Solver.solve_dfs_diverse)