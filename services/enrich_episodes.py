import time

from database import get_connection
from services.tmdb_tv import (
    get_tv_episode,
    normalize_tv_episode,
)


SAO_SEASON_MAP = {
    "Sword Art Online": 1,
    "Sword Art Online II": 2,
    "Sword Art Online - Alicization": 3,
    "Sword Art Online - Alicization War Of Underworld": 4,
}


def get_episodes_to_enrich():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                e.id AS episode_id,
                e.season_number,
                e.episode_number,
                e.metadata_status,

                a.local_title,

                s.tmdb_id AS show_tmdb_id,
                s.title AS show_title

            FROM episodes e

            JOIN shows s
                ON s.id = e.show_id

            JOIN show_aliases a
                ON a.id = e.show_alias_id

            WHERE e.metadata_status = 'pending'

            ORDER BY
                a.local_title COLLATE NOCASE,
                e.season_number,
                e.episode_number
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def save_episode_metadata(
    episode_id,
    metadata,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE episodes
            SET
                tmdb_episode_id = ?,
                season_number = ?,
                episode_number = ?,
                title = ?,
                overview = ?,
                runtime = ?,
                still_url = ?,
                metadata_status = 'matched'
            WHERE id = ?
        """, (
            metadata["tmdb_episode_id"],
            metadata["season_number"],
            metadata["episode_number"],
            metadata["title"],
            metadata["overview"],
            metadata["runtime"],
            metadata["still_url"],
            episode_id,
        ))

        connection.commit()


def set_episode_status(
    episode_id,
    status,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE episodes
            SET metadata_status = ?
            WHERE id = ?
        """, (
            status,
            episode_id,
        ))

        connection.commit()


def get_tmdb_season(episode):
    local_title = episode["local_title"]
    local_season = episode["season_number"]

    # Special mapping for our SAO filenames.
    if local_title in SAO_SEASON_MAP:
        return SAO_SEASON_MAP[local_title]

    # Normal TV shows already have season numbers.
    return local_season


def enrich_episodes():
    episodes = get_episodes_to_enrich()

    matched = 0
    skipped = 0
    errors = 0

    print(
        f"Episodes waiting for metadata: "
        f"{len(episodes)}"
    )
    print()

    for episode in episodes:
        episode_id = episode["episode_id"]
        local_title = episode["local_title"]
        episode_number = episode["episode_number"]

        season_number = get_tmdb_season(
            episode
        )
        # Totally Spies! The Movie exists in the
        # library as a local Season 0 special.
        if (
            local_title == "Totally Spies!"
            and season_number == 0
            and episode_number == 1
        ):
            print(
                "LOCAL -> "
                "Totally Spies! The Movie"
            )

            set_episode_status(
                episode_id,
                "local",
            )

            skipped += 1
            continue
        
        # Alicization episode 00 does not map
        # directly to TMDB Season 3.
        if (
            local_title
            == "Sword Art Online - Alicization"
            and episode_number == 0
        ):
            print(
                "SKIPPED -> "
                "Sword Art Online - Alicization "
                "Episode 00"
            )

            set_episode_status(
                episode_id,
                "review",
            )

            skipped += 1
            continue

        if (
            season_number is None
            or episode_number is None
        ):
            print(
                f"SKIPPED -> "
                f"{local_title} "
                f"(missing season/episode)"
            )

            set_episode_status(
                episode_id,
                "review",
            )

            skipped += 1
            continue

        try:
            data = get_tv_episode(
                episode["show_tmdb_id"],
                season_number,
                episode_number,
            )

            metadata = normalize_tv_episode(
                data
            )

            save_episode_metadata(
                episode_id,
                metadata,
            )

            print(
                f"MATCHED -> "
                f"{local_title} "
                f"S{season_number:02d}"
                f"E{episode_number:02d} "
                f"- {metadata['title']}"
            )

            matched += 1

        except Exception as error:
            print(
                f"ERROR -> "
                f"{local_title} "
                f"S{season_number:02d}"
                f"E{episode_number:02d}: "
                f"{error}"
            )

            errors += 1

        time.sleep(0.1)

    print()
    print("Episode enrichment complete.")
    print(f"Matched: {matched}")
    print(f"Review:  {skipped}")
    print(f"Errors:  {errors}")


if __name__ == "__main__":
    enrich_episodes()