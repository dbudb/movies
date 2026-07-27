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


def get_movie_rating(prompt: str) -> float:
    """Prompts the user (with prompt given as argument) to input a movie rating.
    Validates the input and returns the validated rating.
    """
    while True:
        movie_rating = input(prompt)
        try:
            movie_rating = float(movie_rating)
            if 0.0 <= movie_rating <= 10.0:
                return movie_rating
            else:
                print("Rating must be between 0 and 10.")
        except ValueError:
            print("Please enter your rating in format '3.5'.")


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


def movie_exists(movies: dict[str, dict], movie_title: str) -> bool:
    """Returns if an exact title exists in a dictionary as key and returns a bool."""
    return movie_title in movies


def command_add_movie(movies: dict[str, dict], user_id: int) -> None:
    """Retrieve a movie from OMDb and add it to the database."""
    requested_title = get_movie_title("Enter new movie name: ")

    try:
        movie = movie_api.get_movie(requested_title)
    except movie_api.MovieNotFoundError as error:
        print(error)
        return
    except movie_api.MovieAPIError as error:
        print(f"Could not add movie: {error}")
        return

    movie_title = movie["title"]
    if movie_exists(movies, movie_title):
        print(f"Movie '{movie_title}' already exists!")
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
    """Expects a dictionary for example {'Pulp Fiction': 9.9, ...} and a movie title and returns a string, either listing
    all movie titles matching the search keyword or stating 'no matching movies'. Therefore first checks if exact movie
    title is in our dict, then, if not, looking if our search string is a substring of the title of one of our movies and
    last calling the distance function from the Levenshtein library to calculate the Levenshtein distance between the
    search string and all movie titles. If there are titles with 2 or less as the levenshtein distance, it is considered
    as matching and returned in a formatted string.
    """
    search_output = ""
    movie_title_lower = movie_title.lower()

    if movie_exists(movies, movie_title):
        search_output += f"{movie_title}, {movies[movie_title]['rating']}\n"

    else:
        for movie, info in movies.items():
            if movie_title_lower in movie.lower():
                search_output += f"{movie}, {info['rating']}\n"

        if not search_output:
            for movie, info in movies.items():
                if distance(movie_title_lower, movie.lower()) <= 2:
                    search_output += f"{movie}, {info['rating']}\n"

    return search_output if search_output else "No matching movies found."


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
    safe_year = escape(str(movie["year"]))
    poster_url = escape(movie.get("poster", ""), quote=True)

    if poster_url:
        poster_html = (
            f'<img class="movie-poster" src="{poster_url}" '
            f'alt="{safe_title} poster">'
        )
    else:
        poster_html = (
            '<div class="movie-poster movie-poster-missing">'
            "No poster available"
            "</div>"
        )

    return (
        "            <li>\n"
        '                <div class="movie">\n'
        f"                    {poster_html}\n"
        f'                    <div class="movie-title">{safe_title}</div>\n'
        f'                    <div class="movie-year">{safe_year}</div>\n'
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
                user_title = get_movie_title("Enter movie name to delete: ")
                if movie_exists(movies, user_title):
                    storage.delete_movie(active_user["id"], user_title)
                else:
                    print(f"Movie {user_title} not found.")

            elif user_input == 4:
                user_title = get_movie_title("Enter movie name: ")
                if not movie_exists(movies, user_title):
                    print(f"{user_title} not in database.")
                    continue

                print(f"{user_title}: {movies[user_title]['rating']}")
                user_rating = get_movie_rating("Enter new movie rating (0-10): ")
                storage.update_movie(
                    active_user["id"],
                    user_title,
                    user_rating,
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
