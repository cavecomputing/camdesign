from __future__ import annotations

import sqlite3
from pathlib import Path

import click
from flask import Flask, current_app, g

MIGRATIONS_DIR = Path(__file__).with_name("migrations")


def connect_database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect_database(Path(current_app.config["DATABASE"]))
    return g.db


def close_db(_error: BaseException | None = None) -> None:
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def migrate_database(database_path: Path, migrations_dir: Path = MIGRATIONS_DIR) -> None:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = connect_database(database_path)
    try:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
        )
        applied = {
            row["version"] for row in connection.execute("SELECT version FROM schema_migrations")
        }
        for migration in sorted(migrations_dir.glob("[0-9][0-9][0-9][0-9]_*.sql")):
            version = int(migration.name.split("_", maxsplit=1)[0])
            if version in applied:
                continue
            sql = migration.read_text(encoding="utf-8")
            connection.executescript(
                f"BEGIN IMMEDIATE;\n{sql}\n"
                f"INSERT INTO schema_migrations(version) VALUES ({version});\nCOMMIT;"
            )
    finally:
        connection.close()


@click.command("db-upgrade")
def db_upgrade_command() -> None:
    migrate_database(Path(current_app.config["DATABASE"]))
    click.echo("Database is up to date.")


def init_app(app: Flask) -> None:
    app.teardown_appcontext(close_db)
    app.cli.add_command(db_upgrade_command)
