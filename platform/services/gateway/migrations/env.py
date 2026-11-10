"""Alembic uses only the explicit connection supplied by the operator command."""

from alembic import context
from sqlalchemy.engine import Connection

connection = context.config.attributes.get("connection")
if not isinstance(connection, Connection):
    raise RuntimeError("Supply an explicit migration connection through app.storage.migrate.")
context.configure(connection=connection, version_table_schema="platform", transactional_ddl=True)
with context.begin_transaction():
    context.run_migrations()
