import os

root_dir = r"."

# Directories to ignore (you can modify this list based on your needs)
ignore_dirs = {"venvcpp", "__pycache__", ".git", ".vscode", "site-packages"}

def print_tree(startpath, prefix=""):
    try:
        items = os.listdir(startpath)
    except PermissionError:
        return

    # Print directories first (excluding ignored ones)
    dirs = [d for d in items if os.path.isdir(os.path.join(startpath, d)) and d not in ignore_dirs]

    # Include all files (no filtering by extension)
    files = [f for f in items if os.path.isfile(os.path.join(startpath, f))]

    # Combine directories and files, then sort them
    items_sorted = sorted(dirs) + sorted(files)

    # Print each item
    for index, item in enumerate(items_sorted):
        path = os.path.join(startpath, item)
        connector = "└── " if index == len(items_sorted) - 1 else "├── "

        # Print the current directory or file
        print(prefix + connector + item)

        # Recursively print directories
        if os.path.isdir(path):
            extension = "    " if index == len(items_sorted) - 1 else "│   "
            print_tree(path, prefix + extension)

# Call the function to start printing the directory tree
print_tree(root_dir)

