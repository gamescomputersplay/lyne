from pathlib import Path
from math import ceil
from PIL import Image


INPUT_DIR = Path("./solution_pics/")
OUTPUT_DIR = Path("./solution_pics_combined")
COLUMNS = 3

def combine_images(
    input_dir,
    output_dir,
    columns=5,
):
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    for letter in "abcdefghijklmnopqrstuvwxyz":

        images = []

        for i in range(1, 26):
            path = input_dir / f"{letter}-{i:02d}.png"

            if path.exists():
                images.append(Image.open(path).convert("RGB"))

        if not images:
            continue

        tile_width, tile_height = images[0].size

        rows = ceil(len(images) / columns)

        # Create the grid
        grid = Image.new(
            "RGB",
            (tile_width * columns, tile_height * rows),
            (229, 221, 237)
        )

        # Place images left-to-right, top-to-bottom
        for index, image in enumerate(images):
            row = index // columns
            col = index % columns

            x = col * tile_width
            y = row * tile_height

            grid.paste(image, (x, y))

        # Resize to Full HD width
        scale = 1920 / grid.width
        new_height = round(grid.height * scale)

        grid = grid.resize(
            (1920, new_height),
            Image.Resampling.LANCZOS
        )

        output_path = output_dir / f"{letter}-combined.png"
        grid.save(output_path)

        print(f"Created {output_path}")


combine_images(
    INPUT_DIR,
    OUTPUT_DIR,
    columns=COLUMNS,
)