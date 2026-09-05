from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url
from alembic import context

from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect them.
from app import models  # noqa
from app.models import blood_bank, diet, referral  # noqa


config = context.config

# DATABASE_URL from .env:
# postgresql://hms_user:Dk%40123@localhost:5432/hms_db
#
# Convert it into a SQLAlchemy URL object first.
db_url = make_url(settings.DATABASE_URL)

# Pass a properly parsed URL to Alembic.
config.set_main_option(
    "sqlalchemy.url",
    db_url.render_as_string(hide_password=False).replace("%", "%%")
)


if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
