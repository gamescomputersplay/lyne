from pathlib import Path

import pandas as pd
from jinja2 import Environment, FileSystemLoader


DATA_FILE = "stats_SMART RESTART.xlsx"
TITLE = "SMART RESTART"

TEMPLATE_DIR = "."
TEMPLATE_FILE = "data_visualization.html"
OUTPUT_FILE = DATA_FILE.split(".")[0] + ".html"


MAX_TIME = 10.0


def time_to_color(time_seconds):
    """
    Convert solving time to a color.

    0 seconds  -> green
    10 seconds -> yellow-green
    """

    # Clamp to 0..MAX_TIME
    ratio = min(max(time_seconds / MAX_TIME, 0), 1)

    # Green -> yellow
    # Green: 120°
    # Yellow: 60°
    hue = 120 - (60 * ratio)

    return f"hsl({hue}, 80%, 50%)"


def prepare_data(df):
    """Convert dataframe into the structure used by the template."""

    letters = []

    for letter in "abcdefghijklmnopqrstuvwxyz":

        levels = []

        for number in range(1, 26):

            level_name = f"{letter}-{number:02d}"

            row = df[df["name"] == level_name]

            if row.empty:
                solved = False
                time_seconds = None

            else:
                row = row.iloc[0]

                solved = bool(row["solved"])

                if solved:
                    time_seconds = float(row["time_seconds"])
                else:
                    time_seconds = None

            if solved:
                color = time_to_color(time_seconds)
            else:
                color = "red"

            levels.append({
                "name": level_name,
                "solved": solved,
                "time_seconds": time_seconds,
                "color": color,
            })

        letters.append({
            "letter": letter.upper(),
            "levels": levels,
        })

    return letters


def main():

    df = pd.read_excel(DATA_FILE)

    letters = prepare_data(df)

    solved_count = int(df["solved"].sum())
    total_count = len(df)
    solved_percent = solved_count / total_count * 100

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR)
    )

    template = env.get_template(TEMPLATE_FILE)

    html = template.render(
        title=TITLE,
        letters=letters,
        solved_count=solved_count,
        total_count=total_count,
        solved_percent=solved_percent,
    )

    Path(OUTPUT_FILE).write_text(
        html,
        encoding="utf-8"
    )


if __name__ == "__main__":
    main()
