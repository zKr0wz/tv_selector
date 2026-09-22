from database import (
    get_connection,
    get_tv_media,
    get_show_for_local_title,
)


def get_or_create_episode(
    show_id,
    show_alias_id,
    season_number,
    episode_number,
    episode_title=None,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT id
            FROM episodes
            WHERE show_alias_id = ?
              AND season_number IS ?
              AND episode_number = ?
        """, (
            show_alias_id,
            season_number,
            episode_number,
        ))

        row = cursor.fetchone()

        if row:
            return row["id"]

        cursor.execute("""
            INSERT INTO episodes (
                show_id,
                show_alias_id,
                season_number,
                episode_number,
                title,
                metadata_status
            )
            VALUES (?, ?, ?, ?, ?, 'pending')
        """, (
            show_id,
            show_alias_id,
            season_number,
            episode_number,
            episode_title,
        ))

        connection.commit()

        return cursor.lastrowid

def link_episode_file(
    episode_id,
    media_id,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO episode_files (
                episode_id,
                media_id
            )
            VALUES (?, ?)
        """, (
            episode_id,
            media_id,
        ))

        connection.commit()


def link_episodes():
    media_items = get_tv_media()

    linked = 0
    skipped_show = 0
    skipped_episode = 0

    for media in media_items:

        show = get_show_for_local_title(
            media["title"]
        )

        if show is None:
            print(
                f"NO SHOW -> {media['title']}"
            )
            skipped_show += 1
            continue

        show_id = show["show_id"]
        show_alias_id = show["show_alias_id"]

        if show_id is None:
            print(
                f"NO SHOW -> {media['title']}"
            )
            skipped_show += 1
            continue

        if media["episode"] is None:
            print(
                f"NO EPISODE -> {media['filename']}"
            )
            skipped_episode += 1
            continue

        episode_id = get_or_create_episode(
            show_id=show_id,
            show_alias_id=show_alias_id,
            season_number=media["season"],
            episode_number=media["episode"],
            episode_title=media["episode_title"],
        )

        link_episode_file(
            episode_id=episode_id,
            media_id=media["id"],
        )

        linked += 1

    print()
    print("Episode linking complete.")
    print(f"Linked files:     {linked}")
    print(f"No matched show:  {skipped_show}")
    print(f"No episode #:     {skipped_episode}")


if __name__ == "__main__":
    link_episodes()