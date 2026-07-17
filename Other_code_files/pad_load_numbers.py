import os
import re
from tkinter import Tk, filedialog


def pad_load_numbers():

    Tk().withdraw()

    folder = filedialog.askdirectory(
        title="Select Folder"
    )

    if not folder:
        print("No folder selected.")
        return

    # Pattern:
    # optional prefix (e.g. crop1_)
    # experiment name
    # _LOAD_
    # phase
    pattern = re.compile(
        r"^(.*?_)?(.+?)_(\d+)_(\d{3})(\.[^.]+)$"
    )

    rename_count = 0

    for filename in os.listdir(folder):

        match = pattern.match(filename)

        if match is None:
            continue

        prefix = match.group(1) or ""
        experiment = match.group(2)
        load = match.group(3)
        phase = match.group(4)
        extension = match.group(5)

        new_load = f"{int(load):04d}"

        if load == new_load:
            continue

        new_filename = (
            f"{prefix}"
            f"{experiment}_"
            f"{new_load}_"
            f"{phase}"
            f"{extension}"
        )

        old_path = os.path.join(folder, filename)
        new_path = os.path.join(folder, new_filename)

        os.rename(old_path, new_path)

        rename_count += 1

        print(f"{filename}")
        print(f"  -> {new_filename}")

    print(f"\nRenamed {rename_count} files.")


if __name__ == "__main__":
    pad_load_numbers()