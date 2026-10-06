# Purpose: Regression tests for migration contract, including success and failure behavior.
"""Schema parity, data-preserving upgrades, and unsupported legacy storage."""
from io import StringIO
from pathlib import Path

import pytest

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config as AlembicConfig
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Column, Integer, Table, create_engine, inspect, text
from sqlalchemy.orm import Session

from app.expenses.models import Group, Settlement, User
from app.trips.models import ChecklistItem, ChatMessage, Place, TravelGroup
from app.core.db import connection as database
from app.core.db.base import Base
from app.core.db.migration_checks import assert_uuid_storage


BACKEND_ROOT = Path(__file__).resolve().parent.parent


def _config(url, monkeypatch, output=None):
    monkeypatch.setenv('DATABASE_URL', url)
    config = AlembicConfig(str(BACKEND_ROOT / 'alembic.ini'), output_buffer=output)
    config.set_main_option('script_location', str(BACKEND_ROOT / 'migrations'))
    return config


def _assert_current_schema(engine, config):
    database._import_all_models()
    assert set(inspect(engine).get_table_names()) == set(Base.metadata.tables) | {'alembic_version'}
    with engine.connect() as connection:
        context = MigrationContext.configure(connection, opts={
            'compare_type': True, 'compare_server_default': True,
        })
        assert set(context.get_current_heads()) == set(ScriptDirectory.from_config(config).get_heads())
        assert compare_metadata(context, Base.metadata) == []
        assert connection.execute(text('PRAGMA foreign_key_check')).all() == []


def test_fresh_database_upgrades_to_the_current_schema(tmp_path, monkeypatch):
    """Every revision must apply to an empty database without legacy DDL."""
    database_url = "sqlite:///" + (tmp_path / "fresh-tripraft.db").as_posix()
    config = _config(database_url, monkeypatch)
    command.upgrade(config, "head")

    engine = create_engine(database_url)
    try:
        _assert_current_schema(engine, config)
        # A second deployment must be a no-op, including conditional repairs.
        command.upgrade(config, 'head')
        _assert_current_schema(engine, config)
    finally:
        engine.dispose()


def test_fresh_schema_can_downgrade_and_reinstall(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'roundtrip.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    try:
        command.upgrade(config, 'head')
        command.downgrade(config, 'base')
        assert set(inspect(engine).get_table_names()) <= {'alembic_version'}
        command.upgrade(config, 'head')
        _assert_current_schema(engine, config)
    finally:
        engine.dispose()


def test_existing_uuid_database_gains_missing_fields_without_losing_rows(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'existing.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    try:
        command.upgrade(config, 'head')
        with Session(engine) as session:
            owner = User(email='migration@example.test', password_hash='unused', display_name='Owner')
            session.add(owner)
            session.flush()
            group = Group(name='Expense group', created_by=owner.id)
            trip = TravelGroup(name='Trip', created_by=owner.id)
            session.add_all([group, trip])
            session.flush()
            settlement = Settlement(group_id=group.id, from_user_id=owner.id, to_user_id=owner.id,
                                    recorded_by=owner.id, amount=12)
            place = Place(group_id=trip.id, name='Preserved place', added_by=owner.id)
            checklist = ChecklistItem(group_id=trip.id, item='Preserved item', author_id=owner.id)
            message = ChatMessage(group_id=trip.id, sender_id=owner.id, content='Preserved chat')
            session.add_all([settlement, place, checklist, message])
            session.commit()
            owner_id, settlement_id, place_id = owner.id, settlement.id, place.id
            checklist_id, message_id = checklist.id, message.id

        # Reproduce the documented schema gaps at the previous AI revision.
        command.downgrade(config, '83f1d84d08e4')
        with engine.begin() as connection:
            operations = Operations(MigrationContext.configure(connection))
            operations.drop_table('gp_vault_documents')
            with operations.batch_alter_table('gp_places') as batch:
                batch.drop_column('suggested_time')
        command.upgrade(config, 'head')
        _assert_current_schema(engine, config)
        with Session(engine) as session:
            assert session.get(User, owner_id).display_name == 'Owner'
            assert session.get(User, owner_id).email_verified_at is None
            assert session.get(Settlement, settlement_id).amount == 12
            assert session.get(Settlement, settlement_id).deleted_at is None
            assert session.get(Place, place_id).name == 'Preserved place'
            assert session.get(Place, place_id).suggested_time is None
            assert session.get(ChecklistItem, checklist_id).priority == 'medium'
            assert session.get(ChatMessage, message_id).content == 'Preserved chat'
            assert session.get(ChatMessage, message_id).is_archived is False
    finally:
        engine.dispose()


def test_integer_uuid_conversion_is_rejected_without_changing_data(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'integer.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)'))
            connection.execute(text("INSERT INTO users VALUES (5, 'preserve@example.test')"))
        command.stamp(config, 'c4d5e6f7a8b9')
        with pytest.raises(RuntimeError, match='Legacy integer primary keys'):
            command.upgrade(config, '74866d910457')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT id, email FROM users')).one() == (5, 'preserve@example.test')
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'c4d5e6f7a8b9'
    finally:
        engine.dispose()


@pytest.mark.parametrize('stored_id', [
    5,
    '550e8400-e29b-41d4-a716-446655440000',
    '550E8400E29B41D4A716446655440000',
])
def test_uuid_typed_sqlite_columns_with_invalid_storage_are_rejected(tmp_path, monkeypatch, stored_id):
    url = 'sqlite:///' + (tmp_path / 'bad-payload.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    try:
        command.upgrade(config, 'c4d5e6f7a8b9')
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users (id, email, password_hash) VALUES (:id, 'bad@example.test', 'unused')"
            ), {'id': stored_id})
        with pytest.raises(RuntimeError, match='Invalid UUID payload'):
            command.upgrade(config, 'head')
        with engine.connect() as connection:
            assert connection.execute(text('SELECT id FROM users')).scalar_one() == str(stored_id)
            assert connection.execute(text('SELECT version_num FROM alembic_version')).scalar_one() == 'c4d5e6f7a8b9'
    finally:
        engine.dispose()


def test_integer_foreign_key_to_uuid_primary_key_is_rejected():
    engine = create_engine('sqlite:///:memory:')
    try:
        with engine.begin() as connection:
            connection.execute(text('CREATE TABLE users (id CHAR(32) PRIMARY KEY)'))
            connection.execute(text('CREATE TABLE groups (id CHAR(32) PRIMARY KEY, created_by INTEGER REFERENCES users(id))'))
            with pytest.raises(RuntimeError, match='Incompatible UUID foreign key'):
                assert_uuid_storage(connection)
    finally:
        engine.dispose()


def test_frozen_baseline_does_not_follow_future_model_changes(tmp_path, monkeypatch):
    database._import_all_models()
    future_table = Table('future_model_only', Base.metadata, Column('id', Integer, primary_key=True))
    url = 'sqlite:///' + (tmp_path / 'frozen.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    try:
        command.upgrade(config, 'head')
        assert 'future_model_only' not in inspect(engine).get_table_names()
    finally:
        Base.metadata.remove(future_table)
        engine.dispose()


def test_startup_requires_migrations_and_does_not_create_tables(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    monkeypatch.setattr(database, 'engine', engine)
    try:
        with pytest.raises(RuntimeError, match='migrations are not current'):
            database.init_db()
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


def test_startup_detects_drift_even_when_database_is_stamped_head(tmp_path, monkeypatch):
    url = 'sqlite:///' + (tmp_path / 'drift.db').as_posix()
    config = _config(url, monkeypatch)
    engine = create_engine(url)
    monkeypatch.setattr(database, 'engine', engine)
    try:
        command.upgrade(config, 'head')
        with engine.begin() as connection:
            with Operations(MigrationContext.configure(connection)).batch_alter_table('gp_places') as batch:
                batch.drop_column('suggested_time')
        with pytest.raises(RuntimeError, match='schema drift'):
            database.init_db()
        assert 'suggested_time' not in {column['name'] for column in inspect(engine).get_columns('gp_places')}
    finally:
        engine.dispose()


@pytest.mark.parametrize('url', [
    'sqlite:///',
    'postgresql://localhost/compile_only',
    'postgresql://user:p%40ss@localhost/compile_only',
])
def test_fresh_install_sql_can_be_generated_without_a_database(url, monkeypatch):
    output = StringIO()
    config = _config(url, monkeypatch, output)
    command.upgrade(config, 'head', sql=True)
    sql = output.getvalue()
    assert sql.count('CREATE TABLE ') == 30  # 29 application tables plus Alembic version.
    assert 'CREATE TABLE gp_vault_documents' in sql
    assert 'suggested_time VARCHAR(10)' in sql
    assert 'CREATE MATERIALIZED VIEW' not in sql
    assert 'PARTITION BY' not in sql
    if url.startswith('postgresql'):
        assert 'id UUID' in sql
        assert 'TYPE uuid' not in sql
