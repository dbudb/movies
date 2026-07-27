from storage.movie_storage_sql import (
    add_movie,
    delete_movie,
    list_movies,
    update_movie,
)


def main():
    """Run a basic manual CRUD sanity check."""
    add_movie(
        "Inception",
        2010,
        8.8,
        "https://example.com/inception.jpg",
    )

    movies = list_movies()
    print(movies)

    update_movie("Inception", 9.0)
    print(list_movies())

    delete_movie("Inception")
    print(list_movies())


if __name__ == "__main__":
    main()
