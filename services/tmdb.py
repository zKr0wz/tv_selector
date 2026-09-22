import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from difflib import SequenceMatcher


load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")

BASE_URL = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/w500"


def check_api_key():
    if not API_KEY:
        raise RuntimeError(
            "TMDB_API_KEY was not found. "
            "Check your .env file."
        )


def tmdb_get(endpoint, params=None):
    check_api_key()

    if params is None:
        params = {}

    params["api_key"] = API_KEY

    response = requests.get(
        f"{BASE_URL}{endpoint}",
        params=params,
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


def search_movie(title, year=None):
    params = {
        "query": title,
        "include_adult": False,
    }

    if year:
        params["year"] = year

    data = tmdb_get(
        "/search/movie",
        params=params,
    )

    return data.get("results", [])


def get_movie_details(tmdb_id):
    return tmdb_get(
        f"/movie/{tmdb_id}"
    )


def get_year(release_date):
    if not release_date:
        return None

    try:
        return datetime.strptime(
            release_date,
            "%Y-%m-%d",
        ).year

    except ValueError:
        return None


def normalize_movie(data):
    poster_path = data.get("poster_path")

    poster_url = None

    if poster_path:
        poster_url = (
            f"{IMAGE_BASE_URL}{poster_path}"
        )

    genres = [
        genre["name"]
        for genre in data.get("genres", [])
    ]

    return {
        "tmdb_id": data.get("id"),
        "title": data.get("title"),
        "original_title": data.get("original_title"),
        "year": get_year(
            data.get("release_date")
        ),
        "overview": data.get("overview"),
        "runtime": data.get("runtime"),
        "genres": genres,
        "poster_url": poster_url,
        "vote_average": data.get("vote_average"),
    }

def normalize_title(title):
    """
    Normalize a title for comparison.
    """

    if not title:
        return ""

    title = title.lower()

    # Remove common punctuation
    for char in "._-:'\"!?()[]":
        title = title.replace(char, " ")

    # Collapse duplicate spaces
    title = " ".join(title.split())

    return title


def title_similarity(title1, title2):
    """
    Return title similarity from 0.0 to 1.0.
    """

    title1 = normalize_title(title1)
    title2 = normalize_title(title2)

    return SequenceMatcher(
        None,
        title1,
        title2,
    ).ratio()


def calculate_confidence(
    local_title,
    local_year,
    tmdb_result,
):
    tmdb_title = tmdb_result.get("title", "")

    similarity = title_similarity(
        local_title,
        tmdb_title,
    )

    release_year = get_year(
        tmdb_result.get("release_date")
    )

    score = similarity

    year_match = None

    if local_year and release_year:

        if local_year == release_year:
            score += 0.15
            year_match = True

        else:
            score -= 0.20
            year_match = False

    score = max(0.0, min(score, 1.0))

    return {
        "score": score,
        "title_similarity": similarity,
        "year_match": year_match,
        "tmdb_year": release_year,
    }

def find_movie(title, year=None):

    results = search_movie(
        title=title,
        year=year,
    )

    if not results:
        return {
            "status": "not_found",
            "confidence": 0,
            "movie": None,
        }

    candidates = []

    for result in results[:5]:

        confidence = calculate_confidence(
            title,
            year,
            result,
        )

        candidates.append({
            "result": result,
            "confidence": confidence,
        })

    candidates.sort(
        key=lambda item: item["confidence"]["score"],
        reverse=True,
    )

    best = candidates[0]

    score = best["confidence"]["score"]

    if score >= 0.90:
        status = "matched"

    elif score >= 0.70:
        status = "review"

    else:
        status = "low_confidence"

    movie = None

    if status == "matched":

        details = get_movie_details(
            best["result"]["id"]
        )

        movie = normalize_movie(details)

    return {
        "status": status,
        "confidence": score,
        "title_similarity":
            best["confidence"]["title_similarity"],
        "year_match":
            best["confidence"]["year_match"],
        "movie": movie,
        "candidate": {
            "tmdb_id": best["result"]["id"],
            "title": best["result"]["title"],
            "year": best["confidence"]["tmdb_year"],
        },
    }

def main():

    tests = [
        ("The Matrix", 1999),
        ("Blade", 1998),
        ("Shrek", 2001),
        ("Princess Mononoke", 1997),
        ("Howl's Moving Castle", 2004),
        (
            "The Lord of the Rings "
            "The Fellowship of the Ring",
            None,
        ),
    ]

    for title, year in tests:

        result = find_movie(
            title,
            year,
        )

        print("\n" + "=" * 70)
        print(f"SEARCH: {title} ({year or 'Unknown Year'})")
        print(f"STATUS: {result['status']}")
        print(
            f"CONFIDENCE: "
            f"{result['confidence']:.2%}"
        )

        candidate = result.get("candidate")

        if candidate:
            print(
                f"MATCH: {candidate['title']} "
                f"({candidate['year']})"
            )


if __name__ == "__main__":
    main()