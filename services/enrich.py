import time

from database import (
    create_database,
    get_movies_needing_metadata,
    save_movie_metadata,
    set_metadata_status,
)

from services.tmdb import find_movie


def enrich_library():

    create_database()

    movies = get_movies_needing_metadata()

    total = len(movies)

    print("\nTMDB METADATA ENRICHMENT")
    print("=" * 70)
    print(f"Movies needing metadata: {total}\n")

    if total == 0:
        print("Nothing to update.")
        return

    matched = 0
    review = 0
    not_found = 0

    for number, movie in enumerate(
        movies,
        start=1,
    ):
        title = movie["title"]
        year = movie["year"]

        print(
            f"[{number}/{total}] "
            f"{title} "
            f"({year or 'Unknown'})"
        )

        try:
            result = find_movie(
                title,
                year,
            )

            status = result["status"]
            confidence = result["confidence"]

            if (
                status == "matched"
                and result["movie"]
            ):
                save_movie_metadata(
                    movie["id"],
                    result["movie"],
                    confidence,
                )

                matched += 1

                print(
                    f"   ✓ Matched "
                    f"({confidence:.0%})"
                )

            elif status in {
                "review",
                "low_confidence",
            }:
                set_metadata_status(
                    movie["id"],
                    "review",
                    confidence,
                )

                review += 1

                candidate = result.get(
                    "candidate"
                )

                if candidate:
                    print(
                        f"   ? Review: "
                        f"{candidate['title']} "
                        f"({candidate['year']}) "
                        f"[{confidence:.0%}]"
                    )

            else:
                set_metadata_status(
                    movie["id"],
                    "not_found",
                    confidence,
                )

                not_found += 1

                print("   ✗ Not found")

        except Exception as error:
            # Leave this movie pending so a future
            # run can try it again.
            print(
                f"   ERROR: {error}"
            )

        # Be polite to the API.
        time.sleep(0.1)

    print("\n" + "=" * 70)
    print("ENRICHMENT COMPLETE")
    print("=" * 70)

    print(f"Matched:    {matched}")
    print(f"Review:     {review}")
    print(f"Not Found:  {not_found}")


if __name__ == "__main__":
    enrich_library()