''' Read a screenshot and generate a digital representation of a LYNE puzzle
'''
from PIL import Image
import numpy as np
from pathlib import Path
from scipy.ndimage import label

# -----------------------------
# Configuration
# -----------------------------

TARGET_COLORS = {
    'S': (84, 99, 109), 
    'T': (198, 162, 59), 
    'D': (135, 79, 41), 
    'N': (204, 185, 162)}
WHITE_COLOR = {    
    "W": (230, 221, 237)
    }
MIN_STRETCH = 5  # minimum number of consecutive pixels

def hex_to_rgb(hex_color):
    '''Convert hex color string to RGB tuple. 54636d" -> (84, 99, 109)
    '''
    hex_color = hex_color.lstrip("#")

    if len(hex_color) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")

    return tuple(
        int(hex_color[i:i+2], 16)
        for i in (0, 2, 4)
    )

def convert_colors(colors):
    '''Convert dictionary of named hex colors into RGB tuples.'''
    return {
        name: hex_to_rgb(value)
        for name, value in colors.items()
    }

# -----------------------------
# Load image
# -----------------------------

def load_image(path):
    img = Image.open(path).convert("RGB")
    return np.array(img)


# -----------------------------
# Find matching pixels
# -----------------------------

def color_mask(image, colors):
    """
    Returns True where pixel matches one of target colors exactly.

    colors can be:
        (r, g, b)
        [(r1,g1,b1), (r2,g2,b2)]
    """

    if isinstance(colors, tuple):
        colors = [colors]

    mask = np.zeros(image.shape[:2], dtype=bool)

    for color in colors:
        match = np.all(image == color, axis=2)
        mask |= match

    return mask

# -----------------------------
# Detect continuous ranges
# -----------------------------

def find_ranges(values, min_length):
    '''Given a list of booleans, return continuous True ranges.'''


    ranges = []
    start = None

    for i, value in enumerate(values):

        if value and start is None:
            start = i

        elif not value and start is not None:
            if i - start >= min_length:
                ranges.append((start, i - 1))

            start = None

    # Handle ending range
    if start is not None:
        if len(values) - start >= min_length:
            ranges.append((start, len(values)-1))

    return ranges


def find_axis_ranges(mask, axis=0, min_pixels=5):
    '''
    Find continuous ranges along one axis.

    axis=0 -> scan rows (horizontal projection)
    axis=1 -> scan columns (vertical projection)

    Returns list of (start, end) ranges
    '''

    hits = []

    if axis == 0:
        # scan rows
        for y in range(mask.shape[0]):
            count = np.sum(mask[y, :])
            hits.append(count >= min_pixels)

    elif axis == 1:
        # scan columns
        for x in range(mask.shape[1]):
            count = np.sum(mask[:, x])
            hits.append(count >= min_pixels)

    else:
        raise ValueError("axis must be 0 (rows) or 1 (columns)")

    return find_ranges(hits, 1)


def count_holes(mask):
    """
    Count enclosed empty regions inside a mask.
    """

    # invert:
    # True = empty space
    empty = ~mask

    # label connected empty areas
    labeled, count = label(empty)

    holes = 0

    height, width = mask.shape

    for i in range(1, count + 1):

        region = labeled == i

        # does this empty region touch image border?
        touches_border = (
            np.any(region[0, :]) or
            np.any(region[-1, :]) or
            np.any(region[:, 0]) or
            np.any(region[:, -1])
        )

        if not touches_border:
            holes += 1

    return holes

def classify_cell(image):

    image_np = np.array(image)

    detected = {}

    # detect all colors present in the cell
    for name, rgb in (TARGET_COLORS | WHITE_COLOR).items():

        mask = color_mask(image_np, rgb)

        detected[name] = np.any(mask)

    # -----------------------
    # S / T / D logic
    # -----------------------

    for name in ["S", "T", "D"]:

        if detected.get(name, False):

            if detected.get("W", False):
                return name   # uppercase

            else:
                return name.lower()  # lowercase


    # -----------------------
    # N logic
    # -----------------------

    if detected.get("N", False):
        N_COLOR_VALUES = TARGET_COLORS["N"]
        mask = color_mask(image_np, N_COLOR_VALUES)
        holes = 0
        holes = count_holes(mask)
        return holes


    # nothing detected
    return " "

def read_pic_into_puzzle(image, rows, cols):
    ''' Read the image and return a list of string that solver can use
    '''

    puzzle = []

    for r, (y1, y2) in enumerate(rows):
        puzzle.append("")

        for c, (x1, x2) in enumerate(cols):

            # PIL crop box:
            # (left, upper, right, lower)

            cell = image.crop((
                x1,
                y1,
                x2 + 1,
                y2 + 1
            ))

            value = classify_cell(cell)
            puzzle[-1] += str(value)

    return puzzle

if __name__ == "__main__":


    image = Image.open("lyne_example.png")
    image_np = load_image("lyne_example.png")

    mask = color_mask(image_np, list(TARGET_COLORS.values()))

    rows = find_axis_ranges(mask, axis=0)
    cols = find_axis_ranges(mask, axis=1)

    puzzle = read_pic_into_puzzle(image, rows, cols)
    for line in puzzle:
        print(f"'{line}'")