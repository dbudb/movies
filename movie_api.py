"""Client functions for retrieving movie information from the OMDb API."""

import os
import re

import requests
from dotenv import load_dotenv

OMDB_URL = "https://www.omdbapi.com/"
REQUEST_TIMEOUT = 10


class MovieAPIError(Exception):
    """Raised when movie data cannot be retrieved from OMDb."""


class MovieNotFoundError(MovieAPIError):
    """Raised when OMDb cannot find the requested movie."""


def _parse_year(year_value: str) -> int:
    """Extract the first four-digit year from an OMDb year value."""
    match = re.search(r"\d{4}", year_value)
    if not match:
        raise MovieAPIError("OMDb returned an invalid release year.")
    return int(match.group())


def _parse_rating(rating_value: str) -> float:
    """Convert an OMDb IMDb rating into a numeric rating."""
    try:
        return float(rating_value)
    except (TypeError, ValueError) as error:
        raise MovieAPIError(
            "OMDb does not provide a valid IMDb rating for this movie."
        ) from error


def get_movie(title: str) -> dict:
    """Retrieve a movie's title, year, rating, poster, and IMDb ID."""
    load_dotenv()
    api_key = os.getenv("OMDB_API")
    if not api_key:
        raise MovieAPIError("OMDB_API is missing. Add it to the project's .env file.")

    try:
        response = requests.get(
            OMDB_URL,
            params={"apikey": api_key, "t": title},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        raise MovieAPIError(
            "The OMDb API is currently not accessible. Please try again later."
        ) from error
    except ValueError as error:
        raise MovieAPIError("OMDb returned an invalid response.") from error

    if data.get("Response") == "False":
        message = data.get("Error", "Movie not found.")
        if "not found" in message.lower():
            raise MovieNotFoundError(f"Movie '{title}' was not found.")
        raise MovieAPIError(f"OMDb error: {message}")

    poster = data.get("Poster", "")
    if poster == "N/A":
        poster = ""

    return {
        "title": data["Title"],
        "year": _parse_year(data.get("Year", "")),
        "rating": _parse_rating(data.get("imdbRating", "")),
        "poster": poster,
        "imdb_id": data.get("imdbID", ""),
    }
