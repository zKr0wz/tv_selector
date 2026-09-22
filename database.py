import sqlite3
from pathlib import Path

DATABASE_PATH = Path("data/media.db")


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def create_database():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS media (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                path TEXT NOT NULL UNIQUE,
                filename TEXT NOT NULL,
                extension TEXT,
                size_bytes INTEGER,

                media_type TEXT NOT NULL,
                title TEXT NOT NULL,

                year INTEGER,
                season INTEGER,
                episode INTEGER,
                episode_title TEXT,

                favorite INTEGER NOT NULL DEFAULT 0,
                personal_rating INTEGER,

                play_count INTEGER NOT NULL DEFAULT 0,
                last_played TEXT,

                date_added TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_scanned TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        connection.commit()

    upgrade_database()
    create_tv_tables()

def save_media(media_files):
    with get_connection() as connection:
        cursor = connection.cursor()

        for media in media_files:

            cursor.execute("""
                INSERT INTO media (
                    path,
                    filename,
                    extension,
                    size_bytes,
                    media_type,
                    title,
                    year,
                    season,
                    episode,
                    episode_title
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

                ON CONFLICT(path)
                DO UPDATE SET
                    filename = excluded.filename,
                    extension = excluded.extension,
                    size_bytes = excluded.size_bytes,
                    media_type = excluded.media_type,
                    title = excluded.title,
                    year = excluded.year,
                    season = excluded.season,
                    episode = excluded.episode,
                    episode_title = excluded.episode_title,
                    last_scanned = CURRENT_TIMESTAMP
            """, (
                str(media.path),
                media.name,
                media.extension,
                media.size_bytes,
                media.media_type,
                media.title,
                media.year,
                media.season,
                media.episode,
                media.episode_title,
            ))

        connection.commit()

    return len(media_files)

def get_all_media():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM media
            ORDER BY title COLLATE NOCASE
        """)

        return [dict(row) for row in cursor.fetchall()]

def get_library_stats():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN media_type = 'movie' THEN 1 ELSE 0 END) AS movies,
                SUM(CASE WHEN media_type = 'tv' THEN 1 ELSE 0 END) AS episodes,
                COALESCE(SUM(size_bytes), 0) AS size_bytes
            FROM media
        """)

        return dict(cursor.fetchone())
    
def upgrade_database():
    columns = {
        "tmdb_id": "INTEGER",
        "poster_url": "TEXT",
        "overview": "TEXT",
        "runtime": "INTEGER",
        "genres": "TEXT",
        "tmdb_rating": "REAL",
        "metadata_status": "TEXT DEFAULT 'pending'",
        "metadata_confidence": "REAL",
    }

    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("PRAGMA table_info(media)")

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        for name, definition in columns.items():

            if name not in existing_columns:
                cursor.execute(
                    f"ALTER TABLE media "
                    f"ADD COLUMN {name} {definition}"
                )

        connection.commit()

def get_movies_needing_metadata():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM media
            WHERE media_type = 'movie'
              AND (
                    metadata_status IS NULL
                    OR metadata_status = 'pending'
                  )
            ORDER BY id
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def save_movie_metadata(
    media_id,
    metadata,
    confidence,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE media
            SET
                tmdb_id = ?,
                poster_url = ?,
                overview = ?,
                runtime = ?,
                genres = ?,
                tmdb_rating = ?,
                metadata_status = 'matched',
                metadata_confidence = ?
            WHERE id = ?
        """, (
            metadata["tmdb_id"],
            metadata["poster_url"],
            metadata["overview"],
            metadata["runtime"],
            ", ".join(metadata["genres"]),
            metadata["vote_average"],
            confidence,
            media_id,
        ))

        connection.commit()


def set_metadata_status(
    media_id,
    status,
    confidence=None,
):
    with get_connection() as connection:
        connection.execute("""
            UPDATE media
            SET
                metadata_status = ?,
                metadata_confidence = ?
            WHERE id = ?
        """, (
            status,
            confidence,
            media_id,
        ))

        connection.commit()

def get_movies_with_metadata():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                title,
                year,
                poster_url,
                overview,
                runtime,
                genres,
                tmdb_rating,
                favorite,
                play_count
            FROM media
            WHERE media_type = 'movie'
              AND metadata_status = 'matched'
            ORDER BY title COLLATE NOCASE
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def get_media_by_id(media_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM media
            WHERE id = ?
        """, (media_id,))

        row = cursor.fetchone()

        if row:
            return dict(row)

        return None

def toggle_favorite(media_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE media
            SET favorite =
                CASE
                    WHEN favorite = 1 THEN 0
                    ELSE 1
                END
            WHERE id = ?
        """, (media_id,))

        connection.commit()

        cursor.execute("""
            SELECT favorite
            FROM media
            WHERE id = ?
        """, (media_id,))

        row = cursor.fetchone()

        if row:
            return bool(row["favorite"])

        return False


def get_favorite_status(media_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT favorite
            FROM media
            WHERE id = ?
        """, (media_id,))

        row = cursor.fetchone()

        if row:
            return bool(row["favorite"])

        return False

def record_play(media_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE media
            SET
                play_count = play_count + 1,
                last_played = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (media_id,))

        connection.commit()


def get_most_watched(limit=12):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM media
            WHERE media_type = 'movie'
              AND metadata_status = 'matched'
              AND play_count > 0
            ORDER BY
                play_count DESC,
                last_played DESC
            LIMIT ?
        """, (limit,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]


def get_recently_watched(limit=12):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT *
            FROM media
            WHERE media_type = 'movie'
              AND metadata_status = 'matched'
              AND last_played IS NOT NULL
            ORDER BY last_played DESC
            LIMIT ?
        """, (limit,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def create_tv_tables():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                tmdb_id INTEGER UNIQUE,

                local_title TEXT NOT NULL UNIQUE,
                title TEXT,
                original_title TEXT,

                year INTEGER,

                overview TEXT,
                poster_url TEXT,
                backdrop_url TEXT,

                genres TEXT,
                tmdb_rating REAL,

                metadata_status TEXT
                    NOT NULL DEFAULT 'pending',

                metadata_confidence REAL,

                date_added TEXT
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                show_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL UNIQUE,

                tmdb_episode_id INTEGER,

                season_number INTEGER,
                episode_number INTEGER,

                title TEXT,
                overview TEXT,
                runtime INTEGER,
                still_url TEXT,

                metadata_status TEXT
                    NOT NULL DEFAULT 'pending',

                FOREIGN KEY (show_id)
                    REFERENCES shows(id),

                FOREIGN KEY (media_id)
                    REFERENCES media(id)
            )
        """)

        connection.commit()

def get_unique_tv_shows():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                title,
                year,
                COUNT(*) AS file_count
            FROM media
            WHERE media_type = 'tv'
            GROUP BY title, year
            ORDER BY title COLLATE NOCASE
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def save_show(
    local_title,
    metadata,
    confidence,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO shows (
                tmdb_id,
                title,
                original_title,
                year,
                overview,
                poster_url,
                backdrop_url,
                genres,
                tmdb_rating,
                metadata_status,
                metadata_confidence
            )
            VALUES (
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, 'matched', ?
            )
            ON CONFLICT(tmdb_id)
            DO UPDATE SET
                title = excluded.title,
                original_title =
                    excluded.original_title,
                year = excluded.year,
                overview = excluded.overview,
                poster_url =
                    excluded.poster_url,
                backdrop_url =
                    excluded.backdrop_url,
                genres = excluded.genres,
                tmdb_rating =
                    excluded.tmdb_rating,
                metadata_status = 'matched',
                metadata_confidence =
                    MAX(
                        shows.metadata_confidence,
                        excluded.metadata_confidence
                    )
        """, (
            metadata["tmdb_id"],
            metadata["title"],
            metadata["original_title"],
            metadata["year"],
            metadata["overview"],
            metadata["poster_url"],
            metadata["backdrop_url"],
            ", ".join(
                metadata["genres"]
            ),
            metadata["tmdb_rating"],
            confidence,
        ))

        cursor.execute("""
            SELECT id
            FROM shows
            WHERE tmdb_id = ?
        """, (
            metadata["tmdb_id"],
        ))

        show_id = cursor.fetchone()["id"]

        cursor.execute("""
            INSERT INTO show_aliases (
                show_id,
                local_title
            )
            VALUES (?, ?)
            ON CONFLICT(local_title)
            DO UPDATE SET
                show_id = excluded.show_id
        """, (
            show_id,
            local_title,
        ))

        connection.commit()

        return show_id

def create_tv_tables():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS shows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                tmdb_id INTEGER NOT NULL UNIQUE,

                title TEXT NOT NULL,
                original_title TEXT,

                year INTEGER,

                overview TEXT,
                poster_url TEXT,
                backdrop_url TEXT,

                genres TEXT,
                tmdb_rating REAL,

                metadata_status TEXT
                    NOT NULL DEFAULT 'pending',

                metadata_confidence REAL,

                date_added TEXT
                    NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS show_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                show_id INTEGER NOT NULL,
                local_title TEXT NOT NULL UNIQUE,

                FOREIGN KEY (show_id)
                    REFERENCES shows(id)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                show_id INTEGER NOT NULL,
                show_alias_id INTEGER NOT NULL,

                tmdb_episode_id INTEGER,

                season_number INTEGER,
                episode_number INTEGER,

                title TEXT,
                overview TEXT,
                runtime INTEGER,
                still_url TEXT,

                metadata_status TEXT
                    NOT NULL DEFAULT 'pending',

                FOREIGN KEY (show_id)
                    REFERENCES shows(id),

                UNIQUE (
                    show_id,
                    season_number,
                    episode_number
                )
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episode_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                episode_id INTEGER NOT NULL,
                media_id INTEGER NOT NULL,

                FOREIGN KEY (episode_id)
                    REFERENCES episodes(id),

                FOREIGN KEY (media_id)
                    REFERENCES media(id),

                UNIQUE (
                    episode_id,
                    media_id
                )  
            )
        """)

        connection.commit()

def get_tv_media():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                path,
                filename,
                title,
                year,
                season,
                episode,
                episode_title
            FROM media
            WHERE media_type = 'tv'
            ORDER BY
                title COLLATE NOCASE,
                season,
                episode
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def get_show_for_local_title(
    local_title,
):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id AS show_alias_id,
                show_id
            FROM show_aliases
            WHERE local_title = ?
        """, (local_title,))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

def get_shows_with_metadata():
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                s.id,
                s.tmdb_id,
                s.title,
                s.original_title,
                s.year,
                s.overview,
                s.poster_url,
                s.backdrop_url,
                s.genres,
                s.tmdb_rating,
                s.metadata_status,
                s.metadata_confidence,

                COUNT(DISTINCT e.id)
                    AS episode_count,

                COUNT(DISTINCT a.id)
                    AS alias_count

            FROM shows s

            LEFT JOIN show_aliases a
                ON a.show_id = s.id

            LEFT JOIN episodes e
                ON e.show_id = s.id

            WHERE s.metadata_status = 'matched'

            GROUP BY s.id

            ORDER BY
                s.title COLLATE NOCASE
        """)

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def get_show_episodes(show_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                e.id AS episode_id,
                e.show_id,
                e.season_number,
                e.episode_number,
                e.title AS episode_title,
                e.overview,
                e.runtime,
                e.still_url,
                e.metadata_status,

                a.local_title,

                m.id AS media_id,
                m.path,
                m.filename,
                m.play_count,
                m.last_played

            FROM episodes e

            JOIN show_aliases a
                ON a.id = e.show_alias_id

            JOIN episode_files ef
                ON ef.episode_id = e.id

            JOIN media m
                ON m.id = ef.media_id

            WHERE e.show_id = ?

            ORDER BY
                e.season_number,
                e.episode_number,
                a.local_title COLLATE NOCASE
        """, (show_id,))

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

def get_show_by_id(show_id):
    with get_connection() as connection:
        cursor = connection.cursor()

        cursor.execute("""
            SELECT
                id,
                tmdb_id,
                title,
                original_title,
                year,
                overview,
                poster_url,
                backdrop_url,
                genres,
                tmdb_rating,
                metadata_status,
                metadata_confidence
            FROM shows
            WHERE id = ?
        """, (show_id,))

        row = cursor.fetchone()

        if row is None:
            return None

        return dict(row)

    
def main():
    create_database()

    print(f"Database created: {DATABASE_PATH}")


if __name__ == "__main__":
    main()