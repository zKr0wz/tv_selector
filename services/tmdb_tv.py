from datetime import datetime
from difflib import SequenceMatcher

from services.tmdb import (
    tmdb_get,
    IMAGE_BASE_URL,
)

TV_MANUAL_MATCHES = {
    "Avatar - The Last Airbender": 246,
}

TV_SEARCH_ALIASES = {
    "Sword Art Online II":
        "Sword Art Online",

    "Sword Art Online - Alicization":
        "Sword Art Online",

    "Sword Art Online - Alicization War Of Underworld":
        "Sword Art Online",
}

BACKDROP_BASE_URL = (
    "https://image.tmdb.org/t/p/w1280"
)


STILL_BASE_URL = (
    "https://image.tmdb.org/t/p/w780"
)


def normalize_tv_episode(data):
    still_path = data.get("still_path")

    return {
        "tmdb_episode_id": data.get("id"),
        "season_number": data.get(
            "season_number"
        ),
        "episode_number": data.get(
            "episode_number"
        ),
        "title": data.get("name"),
        "overview": data.get("overview"),
        "runtime": data.get("runtime"),
        "still_url": (
            f"{STILL_BASE_URL}{still_path}"
            if still_path
            else None
        ),
    }

def normalize_tv_show(data):

    poster_path = data.get(
        "poster_path"
    )

    backdrop_path = data.get(
        "backdrop_path"
    )

    return {
        "tmdb_id": data.get("id"),

        "title": data.get("name"),

        "original_title":
            data.get("original_name"),

        "year": get_year(
            data.get("first_air_date")
        ),

        "overview":
            data.get("overview"),

        "poster_url": (
            f"{IMAGE_BASE_URL}"
            f"{poster_path}"
            if poster_path
            else None
        ),

        "backdrop_url": (
            f"{BACKDROP_BASE_URL}"
            f"{backdrop_path}"
            if backdrop_path
            else None
        ),

        "genres": [
            genre["name"]
            for genre
            in data.get("genres", [])
        ],

        "tmdb_rating":
            data.get("vote_average"),
    }

def get_year(date_string):
    if not date_string:
        return None

    try:
        return datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).year

    except ValueError:
        return None


def normalize_title(title):
    if not title:
        return ""

    title = title.lower()

    for char in "._-:'\"!?()[]":
        title = title.replace(
            char,
            " ",
        )

    return " ".join(
        title.split()
    )


def title_similarity(
    local_title,
    tmdb_title,
):
    return SequenceMatcher(
        None,
        normalize_title(local_title),
        normalize_title(tmdb_title),
    ).ratio()


def search_tv(
    title,
    year=None,
):
    params = {
        "query": title,
        "include_adult": False,
    }

    # Try the local year first.
    if year:
        params[
            "first_air_date_year"
        ] = year

    data = tmdb_get(
        "/search/tv",
        params=params,
    )

    results = data.get(
        "results",
        [],
    )

    # If the year produced no results,
    # retry using title only.
    if not results and year:

        params.pop(
            "first_air_date_year",
            None,
        )

        data = tmdb_get(
            "/search/tv",
            params=params,
        )

        results = data.get(
            "results",
            [],
        )

    return results

def get_tv_details(tmdb_id):
    return tmdb_get(
        f"/tv/{tmdb_id}"
    )


def calculate_confidence(
    local_title,
    local_year,
    result,
):
    tmdb_title = result.get(
        "name",
        "",
    )

    similarity = title_similarity(
        local_title,
        tmdb_title,
    )

    tmdb_year = get_year(
        result.get("first_air_date")
    )

    score = similarity

    if (local_year and tmdb_year):
        year_difference = abs(
            local_year - tmdb_year
        )

        if year_difference == 0:
            score += 0.15

        elif year_difference == 1:
            score -= 0.05
        else:
            score -= 0.20

    score = max(
        0.0,
        min(score, 1.0),
    )

    return {
        "score": score,
        "tmdb_year": tmdb_year,
    }

def get_tv_seasons(tmdb_id):
    details = get_tv_details(tmdb_id)

    return [
        {
            "season_number": season.get("season_number"),
            "name": season.get("name"),
            "episode_count": season.get("episode_count"),
            "air_date": season.get("air_date"),
            "id": season.get("id"),
        }
        for season in details.get("seasons", [])
    ]

def get_tv_episode(
    tmdb_id,
    season_number,
    episode_number,
):
    return tmdb_get(
        f"/tv/{tmdb_id}/season/"
        f"{season_number}/episode/"
        f"{episode_number}"
    )

def find_tv_show(title, year=None,):
    manual_match = get_manual_match(
        title
    )
    if manual_match:
        return manual_match
    
    search_title = TV_SEARCH_ALIASES.get(
        title,
        title,
    )

    results = search_tv(
        search_title,
        year,
    )

    if not results:
        return {
            "status": "not_found",
            "confidence": 0,
            "candidate": None,
            "candidates": [],
        }

    candidates = []

    for result in results[:5]:

        confidence = calculate_confidence(
            search_title,
            year,
            result,
        )

        candidates.append({
            "result": result,
            "confidence": confidence,
        })

    candidates.sort(
        key=lambda item:
            item["confidence"]["score"],
        reverse=True,
    )

    best = candidates[0]

    ambiguous = False

    if len(candidates) > 1:

        best_score = candidates[0][
            "confidence"
        ]["score"]

        second_score = candidates[1][
            "confidence"
        ]["score"]

        if abs(
            best_score - second_score
        ) < 0.05:
            ambiguous = True

    score = best[
        "confidence"
    ]["score"]

    result = best["result"]

    if ambiguous:
        status = "review"

    elif score >= 0.90:
        status = "matched"

    elif score >= 0.65:
        status = "review"

    else:
        status = "low_confidence"

    candidate_list = []

    for item in candidates:

        candidate_result = item[
            "result"
        ]

        candidate_confidence = item[
            "confidence"
        ]

        candidate_list.append({
            "tmdb_id":
                candidate_result["id"],

            "title":
                candidate_result["name"],

            "year":
                candidate_confidence[
                    "tmdb_year"
                ],

            "confidence":
                candidate_confidence[
                    "score"
                ],
        })

    return {
        "status": status,
        "confidence": score,

        "candidate": {
            "tmdb_id": result["id"],
            "title": result["name"],
            "year": best[
                "confidence"
            ]["tmdb_year"],
        },

        "candidates": candidate_list,
    }

def get_manual_match(title):

    tmdb_id = TV_MANUAL_MATCHES.get(
        title
    )

    if not tmdb_id:
        return None

    data = get_tv_details(
        tmdb_id
    )

    return {
        "status": "matched",
        "confidence": 1.0,
        "manual": True,

        "candidate": {
            "tmdb_id": data["id"],
            "title": data["name"],
            "year": get_year(
                data.get(
                    "first_air_date"
                )
            ),
        },

        "candidates": [],
    }

def main():

    tests = [
        ("Totally Spies!", 2001),
        ("The Boondocks", 2005),
        ("The Legend of Korra", None),
        (
            "Avatar - The Last Airbender",
            None,
        ),
        (
            "Sword Art Online",
            None,
        ),
        (
            "Sword Art Online II",
            None,
        ),
        (
            "Sword Art Online - Alicization",
            None,
        ),
        (
            "Sword Art Online - "
            "Alicization War Of Underworld",
            None,
        ),
        (
            "Sword Art Online - "
            "Gun Gale Online",
            None,
        ),
    ]

    for title, year in tests:

        result = find_tv_show(
            title,
            year,
        )

        print("\n" + "=" * 70)

        print(
            f"LOCAL: {title}"
        )

        print(
            f"STATUS: "
            f"{result['status']}"
        )

        print(
            f"CONFIDENCE: "
            f"{result['confidence']:.0%}"
        )

        candidate = result.get(
            "candidate"
        )

        if candidate:
            print(
                f"BEST: "
                f"{candidate['title']} "
                f"({candidate['year']})"
            )

        print("CANDIDATES:")

        for candidate in result.get(
            "candidates",
            [],
        ):
            print(
                f"  {candidate['confidence']:.0%} | "
                f"{candidate['title']} "
                f"({candidate['year']}) | "
                f"TMDB ID: {candidate['tmdb_id']}"
            )

if __name__ == "__main__":
    main()