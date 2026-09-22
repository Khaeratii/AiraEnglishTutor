"""One-time migration tool for the retired SQLite Aira database."""

import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


ROOT_DIR = Path(__file__).resolve().parent
SOURCE_DB = ROOT_DIR / 'backend' / 'users.db'
BACKUP_DB = ROOT_DIR / 'backend' / 'users.db.bak'
MIGRATED_TABLES = (
    'users', 'conversations', 'messages', 'learning_events',
    'daily_analyses', 'user_progress',
)
LEGACY_TABLES = ('learner_patterns', 'message_analysis', 'user_history')
ALL_TABLES = MIGRATED_TABLES + LEGACY_TABLES
LEGACY_TABLE_DDL = {
    'learner_patterns': """
        CREATE TABLE IF NOT EXISTS learner_patterns (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            pattern_type TEXT,
            category TEXT,
            example TEXT,
            correction TEXT,
            explanation TEXT,
            frequency INTEGER,
            first_seen TEXT,
            last_seen TEXT,
            is_improving BOOLEAN
        )
    """,
    'message_analysis': """
        CREATE TABLE IF NOT EXISTS message_analysis (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            history_id INTEGER,
            timestamp TEXT,
            grammar_issues TEXT,
            grammar_categories TEXT,
            naturalness_issues TEXT,
            unique_words TEXT,
            vocabulary_opportunities TEXT,
            word_count INTEGER,
            sentence_count INTEGER,
            complexity_score DOUBLE PRECISION,
            has_reason BOOLEAN,
            has_opinion BOOLEAN,
            has_question BOOLEAN,
            has_connector BOOLEAN
        )
    """,
    'user_history': """
        CREATE TABLE IF NOT EXISTS user_history (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            timestamp TEXT,
            level TEXT,
            user_message TEXT,
            ai_message TEXT
        )
    """,
}


def log(message):
    print(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] {message}')


def quote_identifier(identifier):
    return '"' + identifier.replace('"', '""') + '"'


def connect_sqlite(path):
    if not path.exists():
        raise FileNotFoundError(f'SQLite database not found: {path}')
    return sqlite3.connect(path)


def get_postgres_url():
    load_dotenv(ROOT_DIR / '.env')
    load_dotenv(ROOT_DIR / 'backend' / '.env')
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('PostgreSQL configuration is missing. Set DATABASE_URL.')
    parsed_url = make_url(database_url)
    if parsed_url.get_backend_name() != 'postgresql' or parsed_url.get_driver_name() != 'psycopg':
        raise RuntimeError('DATABASE_URL must use postgresql+psycopg.')
    return database_url


def get_source_path():
    configured_path = os.getenv('SQLITE_SOURCE_DB')
    return Path(configured_path) if configured_path else SOURCE_DB


def ensure_backup():
    if SOURCE_DB.exists() and not BACKUP_DB.exists():
        log(f'Creating SQLite backup at {BACKUP_DB}')
        shutil.copy2(SOURCE_DB, BACKUP_DB)


def fetch_source_tables(conn):
    rows = conn.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [row[0] for row in rows]


def fetch_source_columns(conn, table_name):
    return [row[1] for row in conn.execute(
        f'PRAGMA table_info({quote_identifier(table_name)})'
    ).fetchall()]


def migrate_table(source_conn, destination_conn, destination_inspector, table_name):
    source_columns = fetch_source_columns(source_conn, table_name)
    destination_columns = {
        column['name'] for column in destination_inspector.get_columns(table_name)
    }
    columns = [column for column in source_columns if column in destination_columns]
    if not columns:
        log(f'{table_name}: skipped, no compatible columns')
        return 0

    source_rows = source_conn.execute(
        f'SELECT {", ".join(quote_identifier(column) for column in columns)} '
        f'FROM {quote_identifier(table_name)}'
    ).fetchall()
    if not source_rows:
        log(f'{table_name}: 0 rows')
        return 0

    column_sql = ', '.join(quote_identifier(column) for column in columns)
    value_sql = ', '.join(f':{column}' for column in columns)
    parameters = []
    for row in source_rows:
        values = dict(zip(columns, row))
        for boolean_column in (
            'deleted', 'is_improving', 'has_reason', 'has_opinion',
            'has_question', 'has_connector',
        ):
            if boolean_column in values:
                values[boolean_column] = bool(values[boolean_column])
        parameters.append(values)
    insert_sql = (
        f'INSERT INTO {quote_identifier(table_name)} ({column_sql}) '
        f'VALUES ({value_sql}) ON CONFLICT DO NOTHING'
    )
    destination_conn.execute(
        text(insert_sql),
        parameters,
    )
    log(f'{table_name}: {len(source_rows)} source rows processed')
    return len(source_rows)


def reset_sequences(destination_conn, destination_inspector):
    for table_name in MIGRATED_TABLES:
        columns = destination_inspector.get_columns(table_name)
        primary_key = next(
            (column['name'] for column in columns if column.get('autoincrement')), None
        )
        if not primary_key:
            continue
        destination_conn.execute(text(
            'SELECT setval(pg_get_serial_sequence(:table_name, :column_name), '
            'COALESCE((SELECT MAX(' + quote_identifier(primary_key) + ') '
            'FROM ' + quote_identifier(table_name) + '), 1), '
            'EXISTS (SELECT 1 FROM ' + quote_identifier(table_name) + '))'
        ), {'table_name': table_name, 'column_name': primary_key})


def main():
    source_path = get_source_path()
    if source_path == SOURCE_DB:
        ensure_backup()
    source_conn = connect_sqlite(source_path)
    source_conn.row_factory = sqlite3.Row
    destination_engine = create_engine(get_postgres_url(), future=True)
    source_tables = fetch_source_tables(source_conn)
    skipped_tables = sorted(set(source_tables) - set(ALL_TABLES))
    if skipped_tables:
        log('Unmapped source tables: ' + ', '.join(skipped_tables))

    try:
        with destination_engine.begin() as destination_conn:
            for table_name, ddl in LEGACY_TABLE_DDL.items():
                destination_conn.execute(text(ddl))
            inspector = inspect(destination_conn)
            for table_name in ALL_TABLES:
                if table_name not in source_tables:
                    log(f'{table_name}: not present in SQLite source')
                    continue
                migrate_table(source_conn, destination_conn, inspector, table_name)
            reset_sequences(destination_conn, inspector)

        with destination_engine.connect() as destination_conn:
            log('PostgreSQL row counts after migration:')
            for table_name in ALL_TABLES:
                count = destination_conn.execute(text(
                    f'SELECT COUNT(*) FROM {quote_identifier(table_name)}'
                )).scalar_one()
                log(f'  {table_name}: {count}')
    finally:
        source_conn.close()
        destination_engine.dispose()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}')
        sys.exit(1)
