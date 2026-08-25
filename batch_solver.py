''' Batch testing of the Lyne solver on all 650 puzzles
'''

import json
import time
from pathlib import Path

import pandas as pd

import solver


def run_solver_batch(
    puzzle_file,
    output_file,
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
        puzzle_text = item["puzzle"]

        if name in completed:
            print(f"Skipping {name} (already done)")
            continue


        print(f"Solving {name}...")

        start = time.time()

        puzzle = solver.Puzzle(
            puzzle_text,
            verbose=False
        )

        sol = solver.Solver(puzzle, time_limit=timeout)

        sol.solve()

        elapsed = time.time() - start


        result = {
            "name": name,
            "solved": 0 if sol.solution is None else 1,
            "timed_out": 1 if sol.timed_out else 0,
            "time_seconds": round(elapsed, 3),
            "states_explored": sol.states_explored
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

    # Print stats summary
    solved_count = sum(r["solved"] for r in results)
    print(f"Total puzzles solved: {solved_count} / {len(puzzles)}",
          f" ({solved_count / len(puzzles) * 100:.1f}%)")

    return pd.DataFrame(results)

if __name__ == "__main__":

    PUZZLE_FILE = "puzzles.json"

    for STRATEGY in ["BFS", "DFS", "RESTART", "SMART RESTART"]:
        solver.STRATEGY = STRATEGY
        run_solver_batch(PUZZLE_FILE,
            f"stats_{STRATEGY}.xlsx",
            timeout=10)
