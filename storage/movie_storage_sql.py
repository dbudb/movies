"""SQLAlchemy-backed storage operations for users and their movies."""

from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

PROJECT_DIRECTORY = Path(__file__).resolve().parent.parent
DATA_DIRECTORY = PROJECT_DIRECTORY / "data"
DATA_DIRECTORY.mkdir(exist_ok=True)

DB_FILE = DATA_DIRECTORY / "movies.db"
DB_URL = f"sqlite:///{DB_FILE.as_posix()}"

engine = create_engine(DB_URL, echo=True)


@event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _connection_record):
    """Enable SQLite foreign-key enforcement for every connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _create_movies_table(connection, table_name="movies"):
    """Create a profile-aware movies table."""
    if table_name not in {"movies", "movies_new"}:
        raise ValueError("Unsupported table name.")

    connection.execute(text(f"""
            CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                year INTEGER NOT NULL,
                rating REAL NOT NULL,
                poster TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                imdb_id TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE,
                UNIQUE (user_id, title)
            )
            """))


def _migrate_movies_table(connection):
    """Migrate the original shared movies table to per-user storage."""
    columns = connection.execute(text("PRAGMA table_info(movies)")).fetchall()
    column_names = {column[1] for column in columns}

    if "user_id" in column_names:
        if "notes" not in column_names:
            connection.execute(
                text("ALTER TABLE movies " "ADD COLUMN notes TEXT NOT NULL DEFAULT ''")
            )
        if "imdb_id" not in column_names:
            connection.execute(
                text(
                    "ALTER TABLE movies " "ADD COLUMN imdb_id TEXT NOT NULL DEFAULT ''"
                )
            )
        return

    movie_count = connection.execute(text("SELECT COUNT(*) FROM movies")).scalar_one()
    legacy_user_id = None

    if movie_count:
        connection.execute(
            text("INSERT OR IGNORE INTO users (name) VALUES ('Default')")
        )
        legacy_user_id = connection.execute(
            text("SELECT id FROM users WHERE name = 'Default'")
        ).scalar_one()

    _create_movies_table(connection, "movies_new")

    if movie_count:
        poster_expression = "poster" if "poster" in column_names else "''"
        notes_expression = "notes" if "notes" in column_names else "''"
        imdb_id_expression = "imdb_id" if "imdb_id" in column_names else "''"
        connection.execute(
            text(f"""
                INSERT INTO movies_new (
                    id, user_id, title, year, rating, poster, notes, imdb_id
                )
                SELECT
                    id, :user_id, title, year, rating,
                    {poster_expression}, {notes_expression},
                    {imdb_id_expression}
                FROM movies
                """),
            {"user_id": legacy_user_id},
        )

    connection.execute(text("DROP TABLE movies"))
    connection.execute(text("ALTER TABLE movies_new RENAME TO movies"))


def _initialize_database():
    """Create the profile-aware schema and migrate older databases."""
    with engine.connect() as connection:
        connection.execute(text("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT COLLATE NOCASE UNIQUE NOT NULL
                )
                """))

        movies_table_exists = connection.execute(text("""
                SELECT 1
                FROM sqlite_master
                WHERE type = 'table' AND name = 'movies'
                """)).first()

        if movies_table_exists:
            _migrate_movies_table(connection)
        else:
            _create_movies_table(connection)

        connection.commit()


_initialize_database()


def list_users():
    """Return all user profiles ordered by name."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT id, name FROM users ORDER BY name COLLATE NOCASE")
        ).fetchall()
    return [{"id": row[0], "name": row[1]} for row in rows]


def add_user(name):
    """Create a user profile and return its ID, or return None on failure."""
    with engine.connect() as connection:
        try:
            result = connection.execute(
                text("INSERT INTO users (name) VALUES (:name)"),
                {"name": name.strip()},
            )
            connection.commit()
            print(f"User '{name.strip()}' created successfully.")
            return result.lastrowid
        except IntegrityError:
            connection.rollback()
            print(f"User '{name.strip()}' already exists.")
            return None
        except SQLAlchemyError as error:
            connection.rollback()
            print(f"Could not create user: {error}")
            return None


def list_movies(user_id):
    """Retrieve all movies belonging to one user."""
    with engine.connect() as connection:
        rows = connection.execute(
            text("""
                SELECT title, year, rating, poster, notes, imdb_id
                FROM movies
                WHERE user_id = :user_id
                ORDER BY title COLLATE NOCASE
                """),
            {"user_id": user_id},
        ).fetchall()

    return {
        row[0]: {
            "year": row[1],
            "rating": row[2],
            "poster": row[3],
            "notes": row[4],
            "imdb_id": row[5],
        }
        for row in rows
    }


def add_movie(user_id, title, year, rating, poster, notes="", imdb_id=""):
    """Add a movie to one user's collection."""
    with engine.connect() as connection:
        try:
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
                {
                    "user_id": user_id,
                    "title": title,
                    "year": year,
                    "rating": rating,
                    "poster": poster,
                    "notes": notes,
                    "imdb_id": imdb_id,
                },
            )
            connection.commit()
            print(f"Movie '{title}' added successfully.")
            return True
        except IntegrityError:
            connection.rollback()
            print(f"Movie '{title}' already exists in this collection.")
            return False
        except SQLAlchemyError as error:
            connection.rollback()
            print(f"Could not add movie: {error}")
            return False


def delete_movie(user_id, title):
    """Delete a movie from one user's collection."""
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                DELETE FROM movies
                WHERE user_id = :user_id AND title = :title
                """),
            {"user_id": user_id, "title": title},
        )
        connection.commit()

    if result.rowcount:
        print(f"Movie '{title}' deleted successfully.")
        return True
    return False


def update_movie(user_id, title, notes):
    """Update a movie note in one user's collection."""
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                UPDATE movies
                SET notes = :notes
                WHERE user_id = :user_id AND title = :title
                """),
            {"user_id": user_id, "title": title, "notes": notes},
        )
        connection.commit()

    if result.rowcount:
        print(f"Movie {title} successfully updated.")
        return True
    return False
