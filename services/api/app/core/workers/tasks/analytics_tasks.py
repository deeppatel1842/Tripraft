# Purpose: Analytics Tasks Cache warming and daily metrics aggregation.
"""
Analytics Tasks
Cache warming and daily metrics aggregation.
"""
import logging
from datetime import datetime, timedelta, timezone

from app.core.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='app.core.workers.tasks.analytics_tasks.warmup_search_cache')
def warmup_search_cache():
    """Pre-warm cache for popular destination searches."""
    from app.core.cache import redis_client

    if not redis_client.available:
        logger.warning('Redis unavailable, skipping cache warmup')
        return {'status': 'skipped'}

    # Top search terms can be extended as real usage data is collected
    popular_terms = [
        'goa', 'manali', 'jaipur', 'mumbai', 'delhi',
        'bangalore', 'kerala', 'shimla', 'udaipur', 'varanasi',
    ]
    warmed = 0
    for term in popular_terms:
        cache_key = f'places:search:{term}'
        if not redis_client.get(cache_key):
            # Trigger the search so the result is cached by the service layer
            try:
                from app.places.repository import PlaceRepository
                repo = PlaceRepository()
                repo.search_places(term)
                warmed += 1
            except Exception as e:
                logger.debug('Cache warmup skipped for %s: %s', term, e)

    logger.info('Cache warmup complete: %d/%d terms refreshed', warmed, len(popular_terms))
    return {'warmed': warmed, 'total': len(popular_terms)}


@celery_app.task(name='app.core.workers.tasks.analytics_tasks.aggregate_daily_metrics')
def aggregate_daily_metrics():
    """Aggregate daily usage metrics for analytics dashboard."""
    from app.core.db.connection import get_db
    from sqlalchemy import func, text

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    with get_db() as session:
        from app.expenses.models import Expense, Group, Settlement
        from app.auth.models import User

        new_users = session.query(func.count(User.id)).filter(
            func.date(User.created_at) == yesterday
        ).scalar() or 0

        new_groups = session.query(func.count(Group.id)).filter(
            func.date(Group.created_at) == yesterday
        ).scalar() or 0

        new_expenses = session.query(func.count(Expense.id)).filter(
            func.date(Expense.created_at) == yesterday,
            Expense.is_deleted == False,
        ).scalar() or 0

        total_expense_amount = session.query(func.sum(Expense.amount)).filter(
            func.date(Expense.created_at) == yesterday,
            Expense.is_deleted == False,
        ).scalar() or 0

        new_settlements = session.query(func.count(Settlement.id)).filter(
            func.date(Settlement.created_at) == yesterday,
            Settlement.is_deleted == False,
        ).scalar() or 0

    metrics = {
        'date': yesterday.isoformat(),
        'new_users': new_users,
        'new_groups': new_groups,
        'new_expenses': new_expenses,
        'total_expense_amount': float(total_expense_amount),
        'new_settlements': new_settlements,
    }

    # Store in Redis for the admin dashboard
    from app.core.cache import redis_client
    if redis_client.available:
        import json
        redis_client.set(
            f'analytics:daily:{yesterday.isoformat()}',
            json.dumps(metrics),
            ex=60 * 60 * 24 * 30,  # Keep 30 days
        )

    logger.info('Daily metrics aggregated for %s: %s', yesterday, metrics)
    return metrics
