from pathlib import Path


def build_ascii_directory_tree(directory: str, exclude_patterns: list = None, max_depth: int = None) -> str:
    """
    Create a tree view of the directory structure.

    Args:
        directory (str): Root directory to start from
        exclude_patterns (list): List of patterns to exclude (e.g. ['.git', '__pycache__'])
        max_depth (int): Maximum depth to traverse

    Returns:
        str: String representation of the directory tree
    """
    if exclude_patterns is None:
        exclude_patterns = []

    directory = Path(directory)

    def should_exclude(path):
        return any(pattern in str(path) for pattern in exclude_patterns)

    def generate_tree(path: Path, prefix: str = "", depth: int = 0) -> str:
        if max_depth is not None and depth > max_depth:
            return ""

        output = []

        # Add the current directory/file
        if depth == 0:
            output.append(f"{path.name}/")

        # Get all items in the directory
        try:
            items = sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return f"{prefix}[Permission Denied]\n"

        # Process each item
        for index, item in enumerate(items):
            if should_exclude(item):
                continue

            is_last = index == len(items) - 1

            # Create the prefix for the current item
            current_prefix = "└── " if is_last else "├── "
            next_prefix = "    " if is_last else "│   "

            # Add the item to the output
            output.append(f"{prefix}{current_prefix}{item.name}")

            # If it's a directory, recurse into it
            if item.is_dir():
                output.append(generate_tree(item, prefix + next_prefix, depth + 1))

        return "\n".join(filter(None, output))

    return generate_tree(directory)