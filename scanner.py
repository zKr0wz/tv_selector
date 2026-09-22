from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from database import create_database, save_media
from config import VIDEO_EXTENSIONS, IGNORE_DIRECTORIES
from parser import parse_media


@dataclass
class MediaFile:
    name: str
    path: Path
    extension: str
    size_bytes: int

    media_type: str
    title: str

    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)


def should_ignore(path: Path) -> bool:
    return any(
        part in IGNORE_DIRECTORIES
        for part in path.parts
    )


def is_video_file(path: Path) -> bool:
    return (
        path.is_file()
        and path.suffix.lower() in VIDEO_EXTENSIONS
    )


def scan_drive(mountpoint: str) -> list[MediaFile]:

    root = Path(mountpoint)

    if not root.exists():
        print(f"Drive not found: {root}")
        return []

    media_files = []

    print(f"\nScanning: {root}")
    print("This may take a moment...\n")

    try:
        for path in root.rglob("*"):

            if should_ignore(path):
                continue

            try:
                if not is_video_file(path):
                    continue

                parsed = parse_media(path.name)

                media = MediaFile(
                    name=path.name,
                    path=path,
                    extension=path.suffix.lower(),
                    size_bytes=path.stat().st_size,

                    media_type=parsed.media_type,
                    title=parsed.title,
                    year=parsed.year,
                    season=parsed.season,
                    episode=parsed.episode,
                    episode_title=parsed.episode_title,
                )

                media_files.append(media)

            except (PermissionError, OSError) as error:
                print(f"Could not read: {path}")
                print(f"Reason: {error}")

    except (PermissionError, OSError) as error:
        print(f"Scan error: {error}")

    return media_files


def print_movie(media: MediaFile) -> None:

    year = f" ({media.year})" if media.year else ""

    print(
        f"[MOVIE] {media.title}{year}"
        f" - {media.size_gb:.2f} GB"
    )


def print_tv(media: MediaFile) -> None:

    if (
        media.season is not None
        and media.episode is not None
    ):
        episode_code = (
            f"S{media.season:02d}"
            f"E{media.episode:02d}"
        )

    elif media.episode is not None:
        episode_code = (
            f"E{media.episode:02d}"
        )

    else:
        episode_code = "Episode Unknown"

    episode_title = ""

    if media.episode_title:
        episode_title = (
            f" - {media.episode_title}"
        )

    print(
        f"[TV] {media.title} "
        f"{episode_code}"
        f"{episode_title}"
    )
    
def print_results(media_files: list[MediaFile]) -> None:

    movies = [
        media
        for media in media_files
        if media.media_type == "movie"
    ]

    tv_episodes = [
        media
        for media in media_files
        if media.media_type == "tv"
    ]

    print("\nMOVIES")
    print("=" * 70)

    for movie in movies:
        print_movie(movie)

    print("\nTV EPISODES")
    print("=" * 70)

    for episode in tv_episodes:
        print_tv(episode)

    total_size = sum(
        media.size_bytes
        for media in media_files
    )

    total_gb = total_size / (1024 ** 3)

    print("\nLIBRARY SUMMARY")
    print("=" * 70)

    print(f"Movies:       {len(movies)}")
    print(f"TV Episodes:  {len(tv_episodes)}")
    print(f"Total Files:  {len(media_files)}")
    print(f"Storage Used: {total_gb:.2f} GB")


def main():

    create_database()

    mountpoint = input(
        "Enter media drive mount point: "
    ).strip()

    media_files = scan_drive(mountpoint)

    print_results(media_files)

    if not media_files:
        return

    saved = save_media(media_files)

    print("\nDATABASE")
    print("=" * 70)
    print(f"Media records saved: {saved}")


if __name__ == "__main__":
    main()
