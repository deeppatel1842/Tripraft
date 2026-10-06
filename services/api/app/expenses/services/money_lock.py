# Purpose: Serialize money validation and mutation in the same transaction.
"""Serialize money validation and mutation in the same transaction."""

from sqlalchemy import update

from app.expenses.models import Expense, Group, Settlement


def lock_group(session, group_id):
    """Hold a common group lock until the money transaction commits."""
    # SQLite ignores FOR UPDATE; a no-op write acquires its writer lock.
    if session.get_bind().dialect.name == 'sqlite':
        session.execute(
            update(Group).where(Group.id == group_id).values(id=Group.id),
        )
    return (session.query(Group).filter(Group.id == group_id)
            .populate_existing().with_for_update().first())


def lock_money_record(session, model, record_id):
    """Reload after locking so concurrent edits cannot reverse stale money."""
    if model not in (Expense, Settlement):
        raise ValueError('Unsupported money record')
    record = session.get(model, record_id)
    if record is None:
        return None
    if record.group_id is not None:
        lock_group(session, record.group_id)
    elif session.get_bind().dialect.name == 'sqlite':
        session.execute(
            update(model).where(model.id == record_id).values(id=model.id),
        )
    return (session.query(model).filter(model.id == record_id)
            .populate_existing().with_for_update().first())
