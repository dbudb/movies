"""One-time importer for a random sample of real, rated IMDb movies."""

import csv
import gzip
import random

import requests
from sqlalchemy import text

from storage import movie_storage_sql as storage

MOVIE_COUNT = 1_000
MINIMUM_VOTES = 1_000
REQUEST_TIMEOUT = 120
RATINGS_URL = "https://datasets.imdbws.com/title.ratings.tsv.gz"
BASICS_URL = "https://datasets.imdbws.com/title.basics.tsv.gz"


def iter_dataset_rows(url):
    """Yield dictionaries from a gzipped IMDb TSV dataset."""
    with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
        response.raise_for_status()
        response.raw.decode_content = True
        with gzip.GzipFile(fileobj=response.raw) as compressed_file:
            lines = (line.decode("utf-8") for line in compressed_file)
            yield from csv.DictReader(lines, delimiter="\t")


def load_ratings():
    """Return ratings for titles with enough votes to be meaningful."""
    ratings = {}
    for row in iter_dataset_rows(RATINGS_URL):
        if int(row["numVotes"]) >= MINIMUM_VOTES:
            ratings[row["tconst"]] = float(row["averageRating"])
    return ratings


def select_movies(ratings, excluded_titles):
    """Reservoir-sample unique, non-adult feature films."""
    selected = []
    selected_titles = set()
    eligible_seen = 0
    random_source = random.SystemRandom()

    for row in iter_dataset_rows(BASICS_URL):
        imdb_id = row["tconst"]
        title = row["primaryTitle"].strip()
        year = row["startYear"]
        normalized_title = title.casefold()

        if (
            row["titleType"] != "movie"
            or row["isAdult"] != "0"
            or imdb_id not in ratings
            or year == r"\N"
            or not title
            or normalized_title in excluded_titles
            or normalized_title in selected_titles
        ):
            continue

        movie = {
            "title": title,
            "year": int(year),
            "rating": ratings[imdb_id],
            "poster": "",
            "notes": "",
            "imdb_id": imdb_id,
        }
        eligible_seen += 1

        if len(selected) < MOVIE_COUNT:
            selected.append(movie)
            selected_titles.add(normalized_title)
            continue

        replacement_index = random_source.randrange(eligible_seen)
        if replacement_index < MOVIE_COUNT:
            replaced_title = selected[replacement_index]["title"].casefold()
            selected_titles.remove(replaced_title)
            selected[replacement_index] = movie
            selected_titles.add(normalized_title)

    if len(selected) != MOVIE_COUNT:
        raise RuntimeError(
            f"Only {len(selected)} eligible unique movies were available."
        )
    return selected


def main():
    """Add exactly 1,000 random IMDb movies to the sole user profile."""
    storage.engine.echo = False
    users = storage.list_users()
    if len(users) != 1:
        raise RuntimeError("Expected exactly one user profile.")

    user_id = users[0]["id"]
    existing_movies = storage.list_movies(user_id)
    excluded_titles = {title.casefold() for title in existing_movies}

    ratings = load_ratings()
    movies = select_movies(ratings, excluded_titles)
    rows = [{"user_id": user_id, **movie} for movie in movies]

    with storage.engine.begin() as connection:
        before_count = connection.execute(
            text("SELECT COUNT(*) FROM movies WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()
        connection.execute(
            text("""
                INSERT INTO movies (
                    user_id, title, year, rating, poster, notes, imdb_id
                )
                VALUES (
                    :user_id, :title, :year, :rating, :poster, :notes,
                    :imdb_id
                )
                """),
            rows,
        )
        after_count = connection.execute(
            text("SELECT COUNT(*) FROM movies WHERE user_id = :user_id"),
            {"user_id": user_id},
        ).scalar_one()

        if after_count - before_count != MOVIE_COUNT:
            raise RuntimeError("The database did not receive the complete batch.")

    print(
        f"Added {MOVIE_COUNT} random IMDb movies to "
        f"{users[0]['name']}. Total: {after_count}."
    )


if __name__ == "__main__":
    main()
