from alembic import context
from sqlalchemy import create_engine, text

from veritasgraph.structured.store.schema import SCHEMA, metadata

cfg = context.config


def run() -> None:
    engine = create_engine(cfg.get_main_option("sqlalchemy.url"))
    with engine.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{SCHEMA}"'))
        context.configure(
            connection=conn,
            target_metadata=metadata,
            version_table="alembic_version",
            version_table_schema=SCHEMA,
            include_schemas=True,
        )
        with context.begin_transaction():
            context.run_migrations()


run()
