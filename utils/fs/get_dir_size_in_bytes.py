from pathlib import Path


def get_dir_size_in_bytes(dir_path: str) -> float:
    """Return the size of a directory and its subdirectories in bytes


    **Keyword arguments:**
     - dir_path (str) -- The path of the directory

    **Returns:**
     Size of the directory
    """
    root_directory = Path(dir_path)

    return sum(f.stat().st_size for f in root_directory.glob('**/*') if f.is_file())