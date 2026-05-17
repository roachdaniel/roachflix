"""APScheduler jobs for RoachFlix daily checks."""
import json
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)
scheduler = BackgroundScheduler(daemon=True)


def check_new_episodes(app):
    """Notify family when a show they're Watching has a new episode."""
    from app.models import Title, WatchlistEntry
    from app import tmdb
    from app.telegram import send_alert

    with app.app_context():
        tv_titles = (Title.query
                     .join(WatchlistEntry)
                     .filter(WatchlistEntry.status == 'watching',
                             Title.media_type == 'tv')
                     .distinct().all())

        for title in tv_titles:
            try:
                new_date = tmdb.get_tv_next_episode(title.tmdb_id)
                if new_date and new_date != title.next_episode_date:
                    old = title.next_episode_date
                    title.next_episode_date = new_date
                    from app.models import db
                    db.session.commit()
                    if new_date >= datetime.now(timezone.utc).date().isoformat():
                        watchers = (WatchlistEntry.query
                                    .filter_by(title_id=title.id, status='watching')
                                    .join(__import__('app.models', fromlist=['User']).User)
                                    .all())
                        names = ', '.join(e.user.username for e in watchers)
                        send_alert(
                            f"📺 <b>{title.title}</b> — next episode: {new_date}\n"
                            f"Watching: {names}"
                        )
            except Exception as e:
                log.warning('Episode check failed for %s: %s', title.title, e)


def check_streaming_availability(app):
    """Notify when a Want to Watch movie lands on a subscribed streaming service."""
    from app.models import Title, WatchlistEntry, SubscribedService
    from app import tmdb
    from app.telegram import send_alert

    with app.app_context():
        sub_ids = {s.provider_id for s in SubscribedService.query.all()}
        movie_titles = (Title.query
                        .join(WatchlistEntry)
                        .filter(WatchlistEntry.status == 'want',
                                Title.media_type == 'movie')
                        .distinct().all())

        for title in movie_titles:
            try:
                providers = tmdb.get_watch_providers(title.tmdb_id, 'movie')
                old_providers = json.loads(title.providers_json) if title.providers_json else []
                old_ids = {p['provider_id'] for p in old_providers if sub_ids and p.get('provider_id') in sub_ids}
                new_ids = {p['provider_id'] for p in providers if sub_ids and p.get('provider_id') in sub_ids}
                added_ids = new_ids - old_ids
                added = [p['name'] for p in providers if p.get('provider_id') in added_ids]

                if added:
                    title.providers_json = json.dumps(providers)
                    title.providers_updated = datetime.now(timezone.utc)
                    from app.models import db
                    db.session.commit()
                    platform_str = ', '.join(added)
                    wanters = (WatchlistEntry.query
                               .filter_by(title_id=title.id, status='want').all())
                    names = ', '.join(e.user.username for e in wanters)
                    send_alert(
                        f"🎬 <b>{title.title}</b> is now streaming on {platform_str}!\n"
                        f"On watchlist: {names}"
                    )
            except Exception as e:
                log.warning('Streaming check failed for %s: %s', title.title, e)


def init_scheduler(app):
    if scheduler.running:
        return
    scheduler.add_job(
        check_new_episodes,
        'cron',
        hour=8,
        minute=0,
        args=[app],
        id='check_episodes',
        replace_existing=True,
    )
    scheduler.add_job(
        check_streaming_availability,
        'cron',
        hour=8,
        minute=15,
        args=[app],
        id='check_streaming',
        replace_existing=True,
    )
    scheduler.start()
    log.info('RoachFlix scheduler started.')
