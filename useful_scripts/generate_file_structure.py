import os

def generate_file_structure(root_dir, ignore_folders=None, prefix=""):
    """
    Recursively generates the file structure of the given directory, ignoring specified folders.

    :param root_dir: Directory to scan.
    :param ignore_folders: List of folder names to ignore.
    :param prefix: Prefix used for tree-like indentation.
    """
    if ignore_folders is None:
        ignore_folders = []

    try:
        items = sorted(os.listdir(root_dir))
    except PermissionError:
        print(f"{prefix}[Permission Denied] {root_dir}")
        return

    for index, item in enumerate(items):
        item_path = os.path.join(root_dir, item)
        is_last = index == len(items) - 1
        connector = "└── " if is_last else "├── "
        next_prefix = "    " if is_last else "│   "

        if os.path.isdir(item_path):
            if item in ignore_folders:
                continue
            print(f"{prefix}{connector}{item}/")
            generate_file_structure(item_path, ignore_folders, prefix + next_prefix)
        else:
            print(f"{prefix}{connector}{item}")


if __name__ == "__main__":
    # Define the root directory and folders to ignore
    current_dir = os.getcwd()
    folders_to_ignore = ["__pycache__", "myenv", ".git", ".venv"]

    print(f"File structure of {current_dir} (ignoring {folders_to_ignore}):\n")
    generate_file_structure(current_dir, folders_to_ignore)
