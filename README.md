# Movie Project

A command-line movie collection that retrieves real movie details from the
[OMDb API](https://www.omdbapi.com/), stores them in SQLite, provides collection
statistics and search tools, and generates a poster-based HTML website.

## Features

- Add movies by title using OMDb data
- Maintain separate movie collections for multiple user profiles
- Store titles, release years, IMDb ratings, and poster URLs in SQLite
- List, search, update, delete, sort, and randomly select movies
- Add personal notes that appear when a website poster is hovered or focused
- Display each movie's IMDb rating on its generated website card
- Show rating statistics and generate a rating histogram
- Generate a profile-specific static movie website

## Project structure

```text
movie_project_API_SQL_HTML/
├── data/
│   └── movies.db              # Users and their movie collections
├── storage/
│   ├── __init__.py
│   └── movie_storage_sql.py   # SQLite CRUD operations
├── _static/
│   ├── index_template.html
│   ├── style.css
│   └── Profile.html           # Generated per-profile website
├── movie_api.py               # OMDb API client
├── movies.py                  # Application entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and add an activated OMDb API key:

   ```text
   OMDB_API=your_api_key_here
   ```

## Usage

Start the application from the project directory:

```powershell
python movies.py
```

Select or create a user profile when the application starts. Every movie
command then applies only to that user's collection. Option 11 returns to the
profile selector.

Option 2 retrieves a movie from OMDb. Option 9 generates a profile-specific
website such as `_static/John.html`, which can then be opened in a browser.

SQL logging is enabled during development through SQLAlchemy's `echo=True`
setting.
