"""Aplica Alembic en la conexión que administra la aplicación."""

from alembic import context

from generador_asignaciones_v2.persistencia.modelos import Base

context.configure(
    connection=context.config.attributes["connection"],
    target_metadata=Base.metadata,
    transactional_ddl=True,
    render_as_batch=True,
)
with context.begin_transaction():
    context.run_migrations()
