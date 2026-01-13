# Database Utilities

This folder provides a small, reusable database layer based on SQLAlchemy (sync) for PostgreSQL.

## Configuration

Environment variables (see `.env`):

- `DB_CONNECTION` (default `pgsql`)
- `DB_HOST` (default `127.0.0.1`)
- `DB_PORT` (default `5432`)
- `DB_DATABASE`
- `DB_USERNAME`
- `DB_PASSWORD`

The resolved SQLAlchemy URL uses the `psycopg2` driver, e.g.:

```
postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DB
```

## Modules

- `connection.py` — global `engine`, `SessionLocal`, `metadata`, and `get_session()` context manager.
- `crud.py` — generic CRUD helpers using SQLAlchemy Core with reflection.
- `repository.py` — `Repository` class wrapping CRUD for a given table name.

All of these are re-exported from `app.infrastructure.db` for convenience.

## Quick usage

```python
from app.infrastructure.db import Repository, read_table

# Specific repositories (assumes tables exist)
users = Repository("users", id_column="id")
tokens = Repository("tokens", id_column="id")

# Read all users (first 10)
rows = users.all(limit=10)

# Filter users
active = users.filter({"is_active": True})

# Get a single user
maybe_user = users.get(1)

# Create a token
new_id = tokens.create({"user_id": 1, "token": "abc", "expires_at": "2025-12-31"})

# Update a user
updated_count = users.update(1, {"name": "New Name"})

# Delete a token
deleted_count = tokens.delete(new_id)
```

## Notes

- The CRUD functions rely on table reflection; ensure the PostgreSQL database already has the tables.
- The `create_row` helper returns the inserted PK if supported. If your table uses a different primary key name, the `Repository` still works as long as you pass the correct `id_column` for `get/update/delete`.
