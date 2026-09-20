"""Download the climatological daily files for Hidalgo stations."""

from utils import download_files

def main() -> None:
    """Download the available climatological files."""
    download_files()


if __name__ == "__main__":
    main()