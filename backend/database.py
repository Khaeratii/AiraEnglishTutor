import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
for env_path in [ROOT_DIR / '.env', BACKEND_DIR / '.env']:
    if env_path.exists():
        load_dotenv(env_path)


def get_database_url() -> str:
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise RuntimeError('PostgreSQL configuration is missing. Set DATABASE_URL.')

    try:
        database_url_obj = make_url(database_url)
    except Exception as exc:
        raise RuntimeError('DATABASE_URL is not a valid PostgreSQL connection URL.') from exc

    if database_url_obj.get_backend_name() != 'postgresql':
        raise RuntimeError('DATABASE_URL must use the PostgreSQL dialect.')

    if database_url_obj.get_driver_name() != 'psycopg':
        raise RuntimeError('DATABASE_URL must use the psycopg driver, for example postgresql+psycopg://...')

    return database_url


class Base(DeclarativeBase):
    pass


engine = create_engine(
    get_database_url(),
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def init_db() -> None:
    required_tables = {
        'users',
        'conversations',
        'messages',
        'learning_events',
        'recurring_mistakes',
        'learning_profiles',
        'daily_analyses',
        'user_progress',
        'password_reset_tokens',
    }
    inspector = inspect(engine)
    missing_tables = sorted(required_tables.difference(inspector.get_table_names()))
    if missing_tables:
        try:
            from . import models
            Base.metadata.create_all(bind=engine)
        except Exception as exc:
            raise RuntimeError(
                'PostgreSQL schema is incomplete. Missing tables: '
                + ', '.join(missing_tables)
                + '. Run the database migration before starting Aira.'
            ) from exc

        inspector = inspect(engine)
        missing_tables = sorted(required_tables.difference(inspector.get_table_names()))
        if missing_tables:
            raise RuntimeError(
                'PostgreSQL schema is incomplete. Missing tables: '
                + ', '.join(missing_tables)
                + '. Run the database migration before starting Aira.'
            )


def get_database_info() -> dict[str, str]:
    with engine.connect() as connection:
        version = connection.execute(text('SELECT version()')).scalar_one()
    return {
        'backend': engine.dialect.name,
        'driver': engine.dialect.driver,
        'version': version,
    }
