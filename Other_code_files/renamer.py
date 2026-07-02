import os
import re
from tkinter import Tk, filedialog

def remove_suffix_from_files():
    # Hide the main Tk window
    root = Tk()
    root.withdraw()

    # Ask user to choose a folder
    folder = filedialog.askdirectory(title="Select Folder")
    if not folder:
        print("No folder selected.")
        return

    # Regex: match the last underscore and up to 15 letters/numbers before the extension
    pattern = re.compile(r"_[A-Za-z0-9]{1,15}(?=\.[^.]+$)")

    renamed_count = 0
    for filename in os.listdir(folder):
        old_path = os.path.join(folder, filename)
        if not os.path.isfile(old_path):
            continue

        new_name = re.sub(pattern, "", filename)
        new_path = os.path.join(folder, new_name)

        if new_name != filename:
            os.rename(old_path, new_path)
            renamed_count += 1
            print(f"Renamed: {filename} -> {new_name}")

    print(f"Done. {renamed_count} files renamed in {folder}.")

# Example use
if __name__ == "__main__":
    remove_suffix_from_files()
