import os
from pathlib import Path
import re

from sqlalchemy.engine import Engine

from .database import engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _database_dir_candidates() -> list[Path]:
    configured_dir = os.getenv("DATABASE_SCRIPTS_DIR")
    candidates = []
    if configured_dir:
        candidates.append(Path(configured_dir))

    candidates.append(Path("/database"))
    for parent in Path(__file__).resolve().parents:
        candidates.append(parent / "database")
    return candidates


def get_sql_script_path(filename: str) -> Path:
    checked_paths = []
    for database_dir in _database_dir_candidates():
        path = database_dir / filename
        checked_paths.append(path)
        if path.exists():
            return path
    checked = ", ".join(str(path) for path in checked_paths)
    raise FileNotFoundError(f"SQL script not found: {filename}; checked: {checked}")


def read_sql_script(filename: str) -> str:
    return get_sql_script_path(filename).read_text(encoding="utf-8")


def _to_sqlite_compatible(sql: str) -> str:
    script = sql
    script = re.sub(r"\bSERIAL PRIMARY KEY\b", "INTEGER PRIMARY KEY AUTOINCREMENT", script)
    script = re.sub(r"\bBOOLEAN\b", "INTEGER", script)
    script = re.sub(r"\bTIMESTAMP\b", "DATETIME", script)
    script = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", script)
    script = re.sub(r"^SELECT setval\(.*?\);\s*$", "", script, flags=re.MULTILINE)
    return script


def execute_sql_script(filename: str, target_engine: Engine | None = None) -> None:
    active_engine = target_engine or engine
    script = read_sql_script(filename)

    connection = active_engine.raw_connection()
    try:
        cursor = connection.cursor()
        try:
            if active_engine.dialect.name == "sqlite":
                cursor.executescript(_to_sqlite_compatible(script))
            else:
                cursor.execute(script)
            connection.commit()
        finally:
            cursor.close()
    finally:
        connection.close()


def apply_init_schema(target_engine: Engine | None = None) -> None:
    execute_sql_script("init.sql", target_engine=target_engine)


def apply_seed_data(target_engine: Engine | None = None) -> None:
    execute_sql_script("seed.sql", target_engine=target_engine)
