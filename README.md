# Movie Project

A command-line movie collection that retrieves real movie details from the
[OMDb API](https://www.omdbapi.com/), stores them in SQLite, provides collection
statistics and search tools, and generates a poster-based HTML website.

## Features

- Add movies by title using OMDb data
- Store titles, release years, IMDb ratings, and poster URLs in SQLite
- List, search, update, delete, sort, and randomly select movies
- Show rating statistics and generate a rating histogram
- Generate a static movie website from the saved collection

## Project structure

```text
movie_project_API_SQL_HTML/
├── data/
│   └── movies.db              # Created automatically
├── storage/
│   ├── __init__.py
│   └── movie_storage_sql.py   # SQLite CRUD operations
├── _static/
│   ├── index_template.html
│   ├── style.css
│   └── index.html             # Generated website
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

Choose an action from the numbered menu. Option 2 retrieves a movie from OMDb.
Option 9 generates `_static/index.html`, which can then be opened in a browser.

SQL logging is enabled during development through SQLAlchemy's `echo=True`
setting.
