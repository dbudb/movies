import tempfile
from pathlib import Path

from sqlalchemy import create_engine

from storage import movie_storage_sql as storage


def check_legacy_migration():
    """Verify that shared legacy movies migrate to a default profile."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_file = Path(temporary_directory) / "legacy_movies.db"
        legacy_engine = create_engine(f"sqlite:///{database_file.as_posix()}")

        with legacy_engine.connect() as connection:
            connection.exec_driver_sql("""
                CREATE TABLE movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE NOT NULL,
                    year INTEGER NOT NULL,
                    rating REAL NOT NULL,
                    poster TEXT NOT NULL
                )
                """)
            connection.exec_driver_sql(
                """
                INSERT INTO movies (title, year, rating, poster)
                VALUES (?, ?, ?, ?)
                """,
                ("Legacy Movie", 2000, 7.5, ""),
            )
            connection.commit()

        legacy_engine.dispose()
        storage.engine = create_engine(f"sqlite:///{database_file.as_posix()}")
        storage._initialize_database()

        users = storage.list_users()
        assert users == [{"id": 1, "name": "Default"}]
        legacy_movie = storage.list_movies(users[0]["id"])["Legacy Movie"]
        assert legacy_movie["notes"] == ""

        print("Legacy migration preservation check: OK")
        storage.engine.dispose()


def main():
    """Run an isolated profile and movie storage sanity check."""
    with tempfile.TemporaryDirectory() as temporary_directory:
        database_file = Path(temporary_directory) / "test_movies.db"
        storage.engine = create_engine(f"sqlite:///{database_file.as_posix()}")
        storage._initialize_database()

        sara_id = storage.add_user("Sara")
        john_id = storage.add_user("John")

        storage.add_movie(
            sara_id,
            "Inception",
            2010,
            8.8,
            "https://example.com/inception.jpg",
        )
        storage.add_movie(
            john_id,
            "Inception",
            2010,
            8.8,
            "https://example.com/inception.jpg",
        )

        storage.update_movie(sara_id, "Inception", "My favorite movie!")
        assert (
            storage.list_movies(sara_id)["Inception"]["notes"] == "My favorite movie!"
        )
        assert storage.list_movies(john_id)["Inception"]["notes"] == ""

        storage.delete_movie(sara_id, "Inception")
        assert storage.list_movies(sara_id) == {}
        assert "Inception" in storage.list_movies(john_id)

        print("User profile isolation sanity check: OK")
        storage.engine.dispose()

    check_legacy_migration()


if __name__ == "__main__":
    main()
