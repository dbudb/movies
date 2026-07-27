"""SQLAlchemy-backed storage operations for the movie application."""

from pathlib import Path

from sqlalchemy import create_engine, text


PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
DATA_DIRECTORY.mkdir(exist_ok=True)

DB_FILE = DATA_DIRECTORY / "movies.db"
DB_URL = f"sqlite:///{DB_FILE.as_posix()}"

engine = create_engine(DB_URL, echo=True)


with engine.connect() as connection:
    connection.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT UNIQUE NOT NULL,
                year INTEGER NOT NULL,
                rating REAL NOT NULL,
                poster TEXT NOT NULL
            )
            """
        )
    )

    columns = connection.execute(text("PRAGMA table_info(movies)")).fetchall()
    column_names = {column[1] for column in columns}
    if "poster" not in column_names:
        connection.execute(
            text(
                "ALTER TABLE movies "
                "ADD COLUMN poster TEXT NOT NULL DEFAULT ''"
            )
        )

    connection.commit()


def list_movies():
    """Retrieve all movies from the database."""
    with engine.connect() as connection:
        result = connection.execute(
            text("SELECT title, year, rating, poster FROM movies")
        )
        movies = result.fetchall()

    return {
        row[0]: {
            "year": row[1],
            "rating": row[2],
            "poster": row[3],
        }
        for row in movies
    }


def add_movie(title, year, rating, poster):
    """Add a new movie to the database."""
    with engine.connect() as connection:
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO movies (title, year, rating, poster)
                    VALUES (:title, :year, :rating, :poster)
                    """
                ),
                {
                    "title": title,
                    "year": year,
                    "rating": rating,
                    "poster": poster,
                },
            )
            connection.commit()
            print(f"Movie '{title}' added successfully.")
        except Exception as error:
            print(f"Error: {error}")


def delete_movie(title):
    """Delete a movie from the database."""
    with engine.connect() as connection:
        connection.execute(
            text("DELETE FROM movies WHERE title = :title"),
            {"title": title},
        )
        connection.commit()
        print(f"Movie '{title}' deleted successfully.")


def update_movie(title, rating):
    """Update a movie's rating in the database."""
    with engine.connect() as connection:
        connection.execute(
            text(
                """
                UPDATE movies
                SET rating = :rating
                WHERE title = :title
                """
            ),
            {"title": title, "rating": rating},
        )
        connection.commit()
        print(f"Movie '{title}' updated successfully.")
