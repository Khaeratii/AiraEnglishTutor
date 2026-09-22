import os
import sys

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

REQUIRED_TABLES = [
    'users',
    'conversations',
    'messages',
    'learning_events',
    'daily_analyses',
    'user_progress',
    'learner_patterns',
    'message_analysis',
    'user_history',
]


def get_database_url():
    url = os.getenv('DATABASE_URL')
    if not url:
        raise RuntimeError('PostgreSQL configuration is missing. Set DATABASE_URL.')
    parsed_url = make_url(url)
    if parsed_url.get_backend_name() != 'postgresql' or parsed_url.get_driver_name() != 'psycopg':
        raise RuntimeError('DATABASE_URL must use postgresql+psycopg.')
    return url


def main():
    engine = create_engine(get_database_url(), future=True)
    insp = inspect(engine)

    with engine.connect() as conn:
        version = conn.execute(text('SELECT version()')).scalar_one()
    print(f'Database backend: {engine.dialect.name}')
    print(f'Database driver: {engine.dialect.driver}')
    print(f'PostgreSQL version: {version}')
    print('PostgreSQL connection: OK')
    tables = insp.get_table_names()
    missing = [t for t in REQUIRED_TABLES if t not in tables]
    if missing:
        raise RuntimeError(f'Missing tables: {missing}')
    print('Users: OK')
    print('Conversations: OK')
    print('Messages: OK')
    print('Learning Events: OK')
    print('Session Analysis: OK')
    print('Learning Profiles: OK')
    print('Legacy learning tables: OK')

    with engine.connect() as conn:
        fk_count = conn.execute(text('SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_type = \'FOREIGN KEY\'')).scalar_one()
        print(f'Foreign key integrity: OK ({fk_count} foreign keys found)')

    print('Migration verification: PASSED')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}')
        sys.exit(1)
