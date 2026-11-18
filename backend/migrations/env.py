from alembic import context

from app.config import get_settings
from app.database import create_database_engine, require_write_authorization
from app.models import Base


def include_object(object, name, type_, reflected, compare_to):
    # These deliberately reference Supabase's externally owned schema, not ORM metadata.
    return not (
        type_ == "foreign_key_constraint"
        and reflected
        and name in {"fk_progress_auth_owner", "fk_review_auth_owner", "fk_attempt_auth_owner"}
    )


if context.is_offline_mode():
    context.configure(
        url="postgresql+psycopg://",
        target_metadata=Base.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    # Only test harnesses supply an explicit isolated local connection.
    supplied = context.config.attributes.get("connection")
    if supplied is not None:
        context.configure(
            connection=supplied, target_metadata=Base.metadata, include_object=include_object
        )
        with context.begin_transaction():
            context.run_migrations()
    else:
        options = context.get_x_argument(as_dictionary=True)
        require_write_authorization(options.get("allow_remote_write") == "true")
        settings = get_settings()
        from sqlalchemy.engine import make_url

        if (
            settings.migration_database_url
            and make_url(settings.migration_database_url.get_secret_value()).port == 6543
        ):
            raise RuntimeError(
                "Migrations require a direct/session connection, not transaction port 6543"
            )
        engine = create_database_engine(settings, migration=True)
        with engine.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout = '5s'")
            connection.exec_driver_sql("SET LOCAL statement_timeout = '60s'")
            context.configure(
                connection=connection, target_metadata=Base.metadata, include_object=include_object
            )
            with context.begin_transaction():
                context.run_migrations()
        engine.dispose()
