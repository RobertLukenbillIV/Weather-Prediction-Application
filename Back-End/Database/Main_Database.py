'''
Main section for application database backend.
Responsible for all setup for the database 
and any functions used for various CRUD functions.

'''
import os
import sqlite3

from ..Startup.Main import REMOTE_SETUP, USE_DISCORD
from contextlib import contextmanager

try:
    import psycopg2
    import psycopg2.extras
except Exception:
    psycopg2 = None

class _Backend:
    kind: str
    placeholder: str

def _detect_backend() -> _Backend:
    if DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
        if psycopg2 is None:
            raise RuntimeError("psychopg2 not installed but DATABASE_URL is Postgres")
        return _Backend("postgres", "%s")
    return _Backend("sqlite", "?")

@contextmanager
def _connection() -> Iterable[Any]:
    if _BACKEND.kind == "sqlite":
        connection = sqlite3.connect(SQLITE_PATH)
        try:
            connection.row_factory = sqlite3.Row
            _ensure_schema_sqlite(con)
            yield connection
            connection.commit()
        finally:
            connection.close()
    else:
        assert psycopg2 is not None
        connection = psycopg2.connect(DATABASE_URL)
        try:
            _ensure_schema_postgres(connection)
            yield connection
            connection.commit()
        finally
            connection.close()

'''
Database Table Past Weather
'''

'''
Database Table Live Weather
id -> int (unique_key)
date -> datetime (required; ex: 12/3/25)
country -> str (required; ex: "US")
city -> str (required; ex: "New York City")

'''



'''
Database Table Future Weather
'''




# Setup for Remote connection
if REMOTE_SETUP:
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
else:
    ##
    None

if USE_DISCORD:
    SQLITE_PATH = os.getenv("SQLITE_PATH", "WPA_Bot.db").strip() or "WPA_Bot.db"

_BACKEND = _detect_backend()