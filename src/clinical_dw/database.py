"""Database initialization shared by Docker and hosted PostgreSQL."""

from pathlib import Path

from psycopg import Connection

SQL_INIT_DIRECTORY = Path(__file__).resolve().parents[2] / "sql" / "init"


def initialize_database(
    connection: Connection, sql_directory: Path = SQL_INIT_DIRECTORY
) -> list[str]:
    """Apply all idempotent SQL initialization files in filename order."""
    sql_files = sorted(sql_directory.glob("*.sql"))
    if not sql_files:
        raise FileNotFoundError(f"no SQL initialization files found in {sql_directory}")

    with connection.transaction(), connection.cursor() as cursor:
        for sql_file in sql_files:
            cursor.execute(sql_file.read_text(encoding="utf-8"))

    return [sql_file.name for sql_file in sql_files]
