# Environment variables aur path handling ke liye os import.
import os

# Python import path modify karne ke liye sys import.
import sys

# .env file load karne ke liye helper.
from dotenv import load_dotenv

# Current project directory ko Python path mein add karte hain taaki app imports kaam karein.
sys.path.append(os.getcwd())

# .env values load karte hain, especially DATABASE_URL.
load_dotenv()

# SQLAlchemy Base import karte hain; Alembic ko metadata yahin se milega.
from app.database import Base

# Models import karna zaroori hai taaki Base.metadata mein saari tables register ho jaayein.
from app.models import User, Product, FlashSale, Order

# Alembic config ke logging setup ke liye.
from logging.config import fileConfig

# Alembic ke config se SQLAlchemy engine banane ke liye.
from sqlalchemy import engine_from_config

# Migration ke liye connection pooling disable/simple rakhne ke liye.
from sqlalchemy import pool

# Alembic runtime context import; migration commands isi se run hote hain.
from alembic import context

# Alembic config object; alembic.ini ki settings yahan available hoti hain.
config = context.config

# Agar config file available hai to logging configure karte hain.
if config.config_file_name is not None:
    # alembic.ini ke logging section ko apply karta hai.
    fileConfig(config.config_file_name)

# Alembic autogenerate ke liye models ka metadata set karte hain.
target_metadata = Base.metadata


# Offline migration mode; DB connection ke bina SQL generate kar sakta hai.
def run_migrations_offline() -> None:
    # alembic.ini se database URL read karta hai.
    url = config.get_main_option("sqlalchemy.url")
    # Alembic context ko offline mode ke liye configure karta hai.
    context.configure(
        # Database URL set karte hain.
        url=url,
        # Models metadata pass karte hain taaki schema compare ho sake.
        target_metadata=target_metadata,
        # Values ko SQL mein literal form mein render karta hai.
        literal_binds=True,
        # SQL parameter style configure karta hai.
        dialect_opts={"paramstyle": "named"},
    )

    # Migration transaction start karta hai.
    with context.begin_transaction():
        # Pending migrations run karta hai.
        context.run_migrations()


# Online migration mode; actual database connection banakar migrations apply karta hai.
def run_migrations_online() -> None:
    # .env ke DATABASE_URL ko Alembic config mein set karte hain.
    config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

    # Alembic config se database engine create karta hai.
    connectable = engine_from_config(
        # alembic.ini ka main config section leta hai.
        config.get_section(config.config_ini_section, {}),
        # sqlalchemy. prefix wali settings use karta hai.
        prefix="sqlalchemy.",
        # Migration ke liye NullPool use karta hai, persistent pool nahi.
        poolclass=pool.NullPool,
    )

    # Database connection open karta hai.
    with connectable.connect() as connection:
        # Alembic context ko actual DB connection aur metadata deta hai.
        context.configure(
            # Active database connection.
            connection=connection,
            # Models metadata.
            target_metadata=target_metadata
        )

        # Migration transaction start karta hai.
        with context.begin_transaction():
            # Pending migrations run karta hai.
            context.run_migrations()


# Agar Alembic offline mode mein chal raha hai to offline function use karo.
if context.is_offline_mode():
    # Offline migrations run karo.
    run_migrations_offline()
# Warna normal online DB migration run karo.
else:
    # Online migrations run karo.
    run_migrations_online()
