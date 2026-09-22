import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ParsedMedia:
    title: str
    media_type: str
    year: Optional[int] = None
    season: Optional[int] = None
    episode: Optional[int] = None
    episode_title: Optional[str] = None


# Common release information that should not be part of a title.
RELEASE_TAGS = {
    "480p", "720p", "1080p", "2160p", "4k",
    "bluray", "brrip", "bdrip", "webrip", "web-dl",
    "webdl", "hdtv", "dvdrip", "hdrip",
    "x264", "x265", "h264", "h265", "hevc",
    "10bit", "aac", "ac3", "ddp5", "ddp5.1",
    "yify", "yts", "yts.mx", "yts.ag", "yts.bz",
}


TV_PATTERN = re.compile(
    r"^(?P<show>.*?)"
    r"[.\s_-]+"
    r"S(?P<season>\d{1,2})E(?P<episode>\d{1,3})"
    r"(?:[.\s_-]+(?P<rest>.*))?$",
    re.IGNORECASE,
)

ANIME_EPISODE_PATTERN = re.compile(
    r"^(?:\[[^\]]+\]\s*)?"
    r"(?P<show>.+?)"
    r"\s*-\s*"
    r"(?P<episode>\d{1,3})"
    r"$",
    re.IGNORECASE,
)


YEAR_PATTERN = re.compile(
    r"(?<!\d)[\(\[\s._-]*"
    r"(?P<year>19\d{2}|20\d{2})"
    r"[\)\]\s._-]*"
)


def normalize_spaces(text: str) -> str:
    text = text.replace(".", " ")
    text = text.replace("_", " ")

    text = re.sub(r"\s+", " ", text)

    return text.strip(" -._[]()")


def extract_year(text: str):
    match = YEAR_PATTERN.search(text)

    if not match:
        return None, text

    year = int(match.group("year"))

    # Everything before the year is usually the movie title.
    title_part = text[:match.start()]

    return year, title_part


def clean_release_tags(text: str) -> str:
    words = text.split()
    cleaned = []

    for word in words:
        normalized = word.lower().strip("[]()")

        if normalized in RELEASE_TAGS:
            break

        # Stop when encountering common technical release tags.
        if re.fullmatch(r"x26[45]", normalized):
            break

        if re.fullmatch(r"\d{3,4}p", normalized):
            break

        cleaned.append(word)

    return " ".join(cleaned)


def parse_tv(filename: str) -> Optional[ParsedMedia]:

    stem = Path(filename).stem
    match = TV_PATTERN.match(stem)

    if not match:
        return None

    show = normalize_spaces(
        match.group("show")
    )

    # Extract a year from the show portion.
    year, show_without_year = extract_year(
        show
    )

    if year:
        show = normalize_spaces(
            show_without_year
        )

    season = int(
        match.group("season")
    )

    episode = int(
        match.group("episode")
    )

    rest = match.group("rest")
    episode_title = None

    if rest:
        rest = normalize_spaces(rest)
        rest = clean_release_tags(rest)

        if rest:
            episode_title = rest

    return ParsedMedia(
        title=show,
        media_type="tv",
        year=year,
        season=season,
        episode=episode,
        episode_title=episode_title,
    )

def parse_movie(filename: str) -> ParsedMedia:

    stem = Path(filename).stem

    year, title_part = extract_year(stem)

    title = normalize_spaces(title_part)

    if year is None:
        title = clean_release_tags(title)

    return ParsedMedia(
        title=title,
        media_type="movie",
        year=year,
    )

def parse_anime_episode(
    filename: str,
) -> Optional[ParsedMedia]:

    stem = Path(filename).stem

    match = ANIME_EPISODE_PATTERN.match(
        stem
    )

    if not match:
        return None

    show = normalize_spaces(
        match.group("show")
    )

    episode = int(
        match.group("episode")
    )

    return ParsedMedia(
        title=show,
        media_type="tv",
        season=None,
        episode=episode,
        episode_title=None,
    )

def parse_media(filename: str) -> ParsedMedia:

    # Standard S01E01 format
    tv_result = parse_tv(filename)

    if tv_result:
        return tv_result

    # Anime/release-group format:
    # [Anime Time] Show Name - 13
    anime_result = parse_anime_episode(
        filename
    )

    if anime_result:
        return anime_result

    # Anything else falls back to movie parsing.
    return parse_movie(filename)

def main():

    test_files = [
        "Saw.VII.The.Final.Chapter.UNRATED.2010.1080p.BRrip.x264.YIFY.mp4",
        "The Lord of the Rings The Fellowship of the Ring.mp4",
        "The.Matrix.1999.1080p.BrRip.x264.YIFY.mp4",
        "Blade (1998) (1080p BluRay x265 10bit Tigole).mkv",
        "Shrek.2.2004.1080p.BluRay.x264.YIFY.mp4",
        "Princess.Mononoke.1997.1080p.BluRay.ENG.LATINO.mkv",
        "Howl's Moving Castle[2004]DvDrip Tri Audio.avi",
        "Avatar.The.Last.Airbender.S01E01.Aang.1080p.NF.WEB-DL.DDP5.1.x264-LiTTLEBLUEMAN.mkv",
        "Avatar.The.Last.Airbender.S01E05.Spirited.Away.1080p.NF.WEB-DL.DDP5.1.x264-LiTTLEBLUEMAN.mkv",
    ]

    for filename in test_files:

        result = parse_media(filename)

        print(f"\nFILE: {filename}")
        print(f"TYPE: {result.media_type}")
        print(f"TITLE: {result.title}")

        if result.year:
            print(f"YEAR: {result.year}")

        if result.media_type == "tv":
            print(f"SEASON: {result.season}")
            print(f"EPISODE: {result.episode}")
            print(f"EPISODE TITLE: {result.episode_title}")


if __name__ == "__main__":
    main()