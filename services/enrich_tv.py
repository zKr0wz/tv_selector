import time

from database import (
    create_database,
    get_unique_tv_shows,
    save_show,
)

from services.tmdb_tv import (
    find_tv_show,
    get_tv_details,
    normalize_tv_show,
)


def enrich_tv():

    create_database()

    shows = get_unique_tv_shows()

    matched = 0
    review = 0
    not_found = 0
    low_confidence = 0
    errors = 0

    print(
        f"Found {len(shows)} "
        f"TV title groups.\n"
    )

    for show in shows:

        local_title = show["title"]
        year = show["year"]
        file_count = show["file_count"]

        print("=" * 70)

        print(
            f"{local_title} "
            f"({file_count} files)"
        )

        try:
            result = find_tv_show(
                local_title,
                year,
            )

            status = result["status"]

            if status == "matched":

                candidate = result[
                    "candidate"
                ]

                tmdb_id = candidate[
                    "tmdb_id"
                ]

                details = get_tv_details(
                    tmdb_id
                )

                metadata = normalize_tv_show(
                    details
                )

                save_show(
                    local_title,
                    metadata,
                    result["confidence"],
                )

                print(
                    f"MATCHED -> "
                    f"{metadata['title']} "
                    f"({metadata['year']})"
                )

                matched += 1

            elif status == "review":

                candidate = result.get(
                    "candidate"
                )

                if candidate:
                    print(
                        f"REVIEW -> "
                        f"{candidate['title']} "
                        f"({candidate['year']})"
                    )

                else:
                    print("REVIEW")

                review += 1

            elif status == "not_found":

                print("NOT FOUND")

                not_found += 1

            else:

                candidate = result.get(
                    "candidate"
                )

                if candidate:
                    print(
                        f"LOW CONFIDENCE -> "
                        f"{candidate['title']} "
                        f"({candidate['year']})"
                    )

                else:
                    print(
                        "LOW CONFIDENCE"
                    )

                low_confidence += 1

        except Exception as error:

            print(
                f"ERROR -> {error}"
            )

            errors += 1

        time.sleep(0.1)

    print("\n" + "=" * 70)

    print("TV enrichment complete.")
    print(f"Matched:        {matched}")
    print(f"Review:         {review}")
    print(f"Not Found:      {not_found}")
    print(
        f"Low Confidence: {low_confidence}"
    )
    print(f"Errors:         {errors}")


def main():
    enrich_tv()


if __name__ == "__main__":
    main()