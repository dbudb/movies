import random
import re
from html import escape
from pathlib import Path

import matplotlib.pyplot as plt
from Levenshtein import distance

import movie_api
from storage import movie_storage_sql as storage

STATIC_DIRECTORY = Path(__file__).parent / "_static"
TEMPLATE_FILE = STATIC_DIRECTORY / "index_template.html"
WEBSITE_FILE = STATIC_DIRECTORY / "index.html"
WEBSITE_TITLE = "My Movie App"


def get_menu_choice() -> int:
    """Prompt for and return a valid menu choice from 0 through 11."""
    while True:
        user_input = input("Enter Choice (0-11): ")
        try:
            user_input = int(user_input)
            if 0 <= user_input <= 11:
                return user_input
            else:
                print("Valid numbers are 0 - 11 (including)!")
        except ValueError:
            print("Number must be a digit (between 0 and 11).")


def get_movie_title(prompt: str) -> str:
    """Prompts the user (with prompt given as argument) to input a movie title,
    validates the input as not empty and returns it.
    """
    while True:
        movie_title = input(prompt).strip()
        if movie_title:
            return movie_title
        else:
            print("Title can not be empty.")


def get_user_name(prompt: str) -> str:
    """Prompt for and return a non-empty profile name."""
    while True:
        user_name = input(prompt).strip()
        if user_name:
            return user_name
        print("User name can not be empty.")


def select_user() -> dict | None:
    """Let the user select an existing profile or create a new one."""
    while True:
        users = storage.list_users()
        print("\nSelect a user:")
        for index, user in enumerate(users, start=1):
            print(f"{index}. {user['name']}")

        create_choice = len(users) + 1
        print(f"{create_choice}. Create new user")
        print("0. Exit")

        try:
            choice = int(input("Enter choice: "))
        except ValueError:
            print("Please enter one of the displayed numbers.")
            continue

        if choice == 0:
            return None
        if choice == create_choice:
            name = get_user_name("Enter new user name: ")
            user_id = storage.add_user(name)
            if user_id is not None:
                return {"id": user_id, "name": name}
            continue
        if 1 <= choice <= len(users):
            return users[choice - 1]

        print("Please enter one of the displayed numbers.")


def get_file_name(prompt: str) -> str:
    """Prompts the user (with prompt given as argument) to input a filename.
    Validates the input and returns the validated filename.
    """
    while True:
        file_name = input(prompt).strip()
        if file_name and "/" not in file_name and "\\" not in file_name:
            return file_name
        else:
            print("Filename can not be empty or contain / or \\ .")


def list_movies(movies: dict[str, dict]) -> str:
    """Expects a dictionary for example {'Pulp Fiction': {'rating': 9.9, 'year': 1994}, ...} and returns a formated
    string like:
    '1 movies in total
    Pulp Fiction (1994): 9.9'
    """
    total_movie_count = len(movies)
    output = f"{total_movie_count} movies in total\n"
    for movie in movies:
        output += f"{movie} ({movies[movie]['year']}): {movies[movie]['rating']}\n"
    return output


def find_movie_matches(
    movies: dict[str, dict],
    search_title: str,
    *,
    allow_partial: bool = True,
    max_distance: int = 2,
) -> list[str]:
    """Return stored titles matching a query, ordered by match quality."""
    normalized_search = search_title.strip().casefold()
    if not normalized_search:
        return []

    exact_matches = [
        stored_title
        for stored_title in movies
        if stored_title.casefold() == normalized_search
    ]
    if exact_matches:
        return exact_matches

    if allow_partial:
        partial_matches = [
            stored_title
            for stored_title in movies
            if normalized_search in stored_title.casefold()
        ]
        if partial_matches:
            return partial_matches

    if max_distance <= 0:
        return []

    scored_titles = [
        (
            distance(normalized_search, stored_title.casefold()),
            stored_title,
        )
        for stored_title in movies
    ]
    if not scored_titles:
        return []

    best_distance = min(item[0] for item in scored_titles)
    if best_distance > max_distance:
        return []

    return [
        stored_title
        for title_distance, stored_title in scored_titles
        if title_distance == best_distance
    ]


def resolve_movie_title(
    movies: dict[str, dict],
    search_title: str,
) -> str | None:
    """Return one unambiguous canonical title for a user's search."""
    matches = find_movie_matches(movies, search_title)
    if len(matches) != 1:
        return None
    return matches[0]


def find_exact_movie(movies: dict[str, dict], search_title: str) -> str | None:
    """Return a case-insensitive exact title match."""
    matches = find_movie_matches(
        movies,
        search_title,
        allow_partial=False,
        max_distance=0,
    )
    return matches[0] if matches else None


def command_add_movie(movies: dict[str, dict], user_id: int) -> None:
    """Retrieve a movie from OMDb and add it to the database."""
    requested_title = get_movie_title("Enter new movie name: ")
    existing_title = find_exact_movie(movies, requested_title)
    if existing_title:
        print(f"Movie '{existing_title}' already exists!")
        return

    try:
        movie = movie_api.get_movie(requested_title)
    except movie_api.MovieNotFoundError as error:
        print(error)
        return
    except movie_api.MovieAPIError as error:
        print(f"Could not add movie: {error}")
        return

    movie_title = movie["title"]
    existing_title = find_exact_movie(movies, movie_title)
    if existing_title:
        print(f"Movie '{existing_title}' already exists!")
        return

    storage.add_movie(
        user_id,
        movie_title,
        movie["year"],
        movie["rating"],
        movie["poster"],
    )


def stats(movies: dict[str, dict]) -> str:
    """Expects a dictionary for example {'Pulp Fiction': 9.9, ...} and returns either 'Database empty' for empty dicts or
    formatted string:
    Average rating: 9.9
    Median rating: 9.9
    Best movie: Pulp Fiction, 9.9
    Worst movie: Pulp Fiction, 9.9
    """
    if not movies:
        return "Database is empty. No stats available."

    ratings = [movie["rating"] for movie in movies.values()]
    average_rating = sum(ratings) / len(ratings)
    ratings_sorted = sorted(ratings)

    if len(ratings_sorted) % 2 == 0:
        upper_middle = len(ratings_sorted) // 2
        lower_middle = len(ratings_sorted) // 2 - 1
        median_rating = (
            ratings_sorted[lower_middle] + ratings_sorted[upper_middle]
        ) / 2
    else:
        median_index = (len(ratings_sorted) - 1) // 2
        median_rating = ratings_sorted[median_index]

    max_rating = max(ratings)
    min_rating = min(ratings)
    best_movies = []
    worst_movies = []

    for movie, info in movies.items():
        if info["rating"] == max_rating:
            best_movies.append(movie)
        if info["rating"] == min_rating:
            worst_movies.append(movie)

    best_movies_str = ", ".join(best_movies)
    worst_movies_str = ", ".join(worst_movies)
    formatted_output = (
        f"Average rating: {average_rating:.1f}\n"
        f"Median rating: {median_rating:.1f}\n"
        f"Best movie: {best_movies_str}, {max_rating}\n"
        f"Worst movie: {worst_movies_str}, {min_rating}"
    )
    return formatted_output


def random_movie(movies: dict[str, dict]) -> str:
    """Expects a dictionary for example {'Pulp Fiction': 9.9, ...} and returns a random movie and its rating as
    f-string.
    """
    if not movies:
        return "Database is empty. No movie to recommend."
    movie_list = list(movies.keys())
    rand_movie = random.choice(movie_list)
    return f"Your movie for tonight: {rand_movie}, it's rated {movies[rand_movie]['rating']}"


def search_movie(movies: dict[str, dict], movie_title: str) -> str:
    """Return formatted exact, partial, or fuzzy movie matches."""
    matches = find_movie_matches(movies, movie_title)
    if not matches:
        return "No matching movies found."

    return "".join(f"{title}, {movies[title]['rating']}\n" for title in matches)


def sort_movie_by_rating(movies: dict[str, dict]) -> str:
    """Expects a dictionary for example {'Pulp Fiction': 9.9, ...} and returns a formatted output that lists all movies
    sorted by their rating (from best to worst).
    """
    if not movies:
        return "Database is empty. No movies to sort."
    movies_sorted = sorted(
        movies.items(), key=lambda item: item[1]["rating"], reverse=True
    )
    formatted_output = ""
    for movie in movies_sorted:
        formatted_output += f"{movie[0]}: {movie[1]['rating']}\n"
    return formatted_output


def _create_movie_html(title: str, movie: dict) -> str:
    """Create the HTML markup for one movie card."""
    safe_title = escape(title)
    safe_title_attribute = escape(title, quote=True)
    safe_year = escape(str(movie["year"]))
    safe_rating = escape(f"{movie['rating']:.1f}")
    poster_url = escape(movie.get("poster", ""), quote=True)
    note = movie.get("notes", "")
    safe_note = escape(note)
    safe_note_attribute = escape(note, quote=True)

    if poster_url:
        poster = (
            f'<img class="movie-poster" src="{poster_url}" '
            f'alt="{safe_title_attribute} poster">'
        )
    else:
        poster = (
            '<div class="movie-poster movie-poster-missing">'
            "No poster available"
            "</div>"
        )

    if safe_note:
        poster_html = (
            '<div class="movie-poster-container" tabindex="0" '
            f'aria-label="Movie note: {safe_note_attribute}">\n'
            f"                        {poster}\n"
            '                        <div class="movie-note" '
            f'role="tooltip">{safe_note}</div>\n'
            "                    </div>"
        )
    else:
        poster_html = poster

    return (
        "            <li>\n"
        '                <div class="movie">\n'
        f"                    {poster_html}\n"
        f'                    <div class="movie-title">{safe_title}</div>\n'
        f'                    <div class="movie-year">{safe_year}</div>\n'
        f'                    <div class="movie-rating" '
        f'aria-label="Rating: {safe_rating} out of 10">'
        f"&#9733; {safe_rating}</div>\n"
        "                </div>\n"
        "            </li>"
    )


def generate_website(
    movies: dict[str, dict],
    output_file: Path = WEBSITE_FILE,
    website_title: str = WEBSITE_TITLE,
) -> None:
    """Generate a movie website from the HTML template."""
    template = TEMPLATE_FILE.read_text(encoding="utf-8")
    movie_grid = "\n".join(
        _create_movie_html(title, movie) for title, movie in movies.items()
    )
    website = template.replace("__TEMPLATE_TITLE__", website_title)
    website = website.replace("__TEMPLATE_MOVIE_GRID__", movie_grid)
    output_file.write_text(website, encoding="utf-8")


def get_profile_website_file(user: dict) -> Path:
    """Return a safe profile-specific website path."""
    safe_name = re.sub(r"[^A-Za-z0-9_-]+", "_", user["name"]).strip("_")
    if not safe_name:
        safe_name = f"user_{user['id']}"
    return STATIC_DIRECTORY / f"{safe_name}.html"


def main():
    """Run the profile selection and movie command loops."""
    print("Welcome to the Movie App!")

    while True:
        active_user = select_user()
        if active_user is None:
            print("Bye!")
            return

        print(f"\nWelcome back, {active_user['name']}!")

        while True:
            movies = storage.list_movies(active_user["id"])
            print("\nMenu:")
            print("0. Exit")
            print("1. List movies")
            print("2. Add movie")
            print("3. Delete movie")
            print("4. Update movie")
            print("5. Stats")
            print("6. Random movie")
            print("7. Search movie")
            print("8. Movies sorted by rating")
            print("9. Generate website")
            print("10. Print rating histogram")
            print("11. Switch user")

            user_input = get_menu_choice()

            if user_input == 0:
                print("Bye!")
                return

            if user_input == 1:
                if movies:
                    print(list_movies(movies))
                else:
                    print(
                        f"{active_user['name']}, your movie collection "
                        "is empty. Add some movies!"
                    )

            elif user_input == 2:
                command_add_movie(movies, active_user["id"])

            elif user_input == 3:
                search_title = get_movie_title("Enter movie name to delete: ")
                movie_title = resolve_movie_title(movies, search_title)
                if movie_title:
                    if movie_title.casefold() != search_title.casefold():
                        print(f"Using closest match: {movie_title}")
                    storage.delete_movie(active_user["id"], movie_title)
                else:
                    print(f"Movie {search_title} not found.")

            elif user_input == 4:
                search_title = get_movie_title("Enter movie name: ")
                movie_title = resolve_movie_title(movies, search_title)
                if not movie_title:
                    print(f"{search_title} not in database.")
                    continue

                if movie_title.casefold() != search_title.casefold():
                    print(f"Using closest match: {movie_title}")
                movie_note = input("Enter movie note: ").strip()
                storage.update_movie(
                    active_user["id"],
                    movie_title,
                    movie_note,
                )

            elif user_input == 5:
                print(stats(movies))

            elif user_input == 6:
                print(random_movie(movies))

            elif user_input == 7:
                user_title = input("Enter part of movie name: ")
                print(search_movie(movies, user_title))

            elif user_input == 8:
                print(sort_movie_by_rating(movies))

            elif user_input == 9:
                website_file = get_profile_website_file(active_user)
                website_title = f"{active_user['name']}'s Movie Collection"
                generate_website(
                    movies,
                    output_file=website_file,
                    website_title=website_title,
                )
                print("Website was generated successfully.")
                print(f"Saved as {website_file.name}.")

            elif user_input == 10:
                if not movies:
                    print("Database is empty. No histogram to create.")
                else:
                    plt.hist([movie["rating"] for movie in movies.values()])
                    file_name = get_file_name(
                        "In which file do you want to save your " "histogram? "
                    )
                    try:
                        plt.savefig(file_name)
                        print(f"Successfully saved as {file_name}.")
                    except Exception as error:
                        print(f"Could not save the histogram: {error}")
                    finally:
                        plt.clf()

            elif user_input == 11:
                print("Switching user...")
                break

            input("\nPress enter to continue")


if __name__ == "__main__":
    main()
