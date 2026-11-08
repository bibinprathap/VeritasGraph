"""Initial vg_structured schema."""

from alembic import op

from veritasgraph.structured.store.schema import SCHEMA, metadata

revision = "0001"
down_revision = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # Initial revision only: later revisions use explicit op.* calls.
    metadata.create_all(bind=op.get_bind())
    for table in ("term", "measure", "dataset", "field"):
        op.execute(
            f'CREATE INDEX IF NOT EXISTS {table}_name_trgm ON "{SCHEMA}".{table} '
            "USING gin (lower(name) gin_trgm_ops)"
        )


def downgrade() -> None:
    op.execute(f'DROP SCHEMA IF EXISTS "{SCHEMA}" CASCADE')
