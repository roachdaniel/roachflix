"""APScheduler jobs for RoachFlix daily checks."""
import json
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)
scheduler = BackgroundScheduler(daemon=True)


def check_new_episodes(app, notify=True):
    """Update next_episode_date for Watching/Up to Date shows; notify if date changed."""
    from app.models import Title, WatchlistEntry
    from app import tmdb, simkl
    from app.telegram import send_alert

    with app.app_context():
        calendar = simkl.fetch_calendar()

        tv_titles = (Title.query
                     .join(WatchlistEntry)
                     .filter(WatchlistEntry.status.in_(['watching', 'uptodate']),
                             Title.media_type == 'tv')
                     .distinct().all())

        for title in tv_titles:
            try:
                # SIMKL calendar covers next 33 days; fall back to TMDB for further out
                new_date = calendar.get(title.tmdb_id) or tmdb.get_tv_next_episode(title.tmdb_id)
                if new_date and new_date != title.next_episode_date:
                    title.next_episode_date = new_date
                    from app.models import db
                    db.session.commit()
                    if notify and new_date >= datetime.now(timezone.utc).date().isoformat():
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


def update_want_episode_dates(app):
    """Sync next_episode_date for Want TV shows from SIMKL calendar (badge data only)."""
    from app.models import db, Title, WatchlistEntry
    from app import simkl

    with app.app_context():
        calendar = simkl.fetch_calendar()
        if not calendar:
            return

        tv_titles = (Title.query
                     .join(WatchlistEntry)
                     .filter(WatchlistEntry.status == 'want',
                             Title.media_type == 'tv')
                     .distinct().all())

        for title in tv_titles:
            try:
                new_date = calendar.get(title.tmdb_id)
                if new_date and new_date != title.next_episode_date:
                    title.next_episode_date = new_date
                    db.session.commit()
            except Exception as e:
                log.warning('Want date update failed for %s: %s', title.title, e)


def send_episode_reminders(app, days):
    """Send a heads-up for episodes/premieres airing in `days` days."""
    from app.models import Title, WatchlistEntry
    from app.telegram import send_alert

    with app.app_context():
        target = (datetime.now(timezone.utc).date() + timedelta(days=days)).isoformat()
        day_str = f"{days} day{'s' if days != 1 else ''}"

        # Watching / Up to Date — next episode reminders
        tv_titles = (Title.query
                     .join(WatchlistEntry)
                     .filter(WatchlistEntry.status.in_(['watching', 'uptodate']),
                             Title.media_type == 'tv',
                             Title.next_episode_date == target)
                     .distinct().all())

        for title in tv_titles:
            try:
                entries = (WatchlistEntry.query
                           .filter(WatchlistEntry.title_id == title.id,
                                   WatchlistEntry.status.in_(['watching', 'uptodate']))
                           .all())
                names = ', '.join(e.user.username for e in entries)
                send_alert(
                    f"📺 <b>{title.title}</b> — new episode in {day_str} ({title.next_episode_date})\n"
                    f"Watching: {names}"
                )
            except Exception as e:
                log.warning('Episode reminder failed for %s: %s', title.title, e)

        # Want to Watch — premiere reminders (TV via next_episode_date, movies via release_date)
        want_tv = (Title.query
                   .join(WatchlistEntry)
                   .filter(WatchlistEntry.status == 'want',
                           Title.media_type == 'tv',
                           Title.next_episode_date == target)
                   .distinct().all())

        want_movies = (Title.query
                       .join(WatchlistEntry)
                       .filter(WatchlistEntry.status == 'want',
                               Title.media_type == 'movie',
                               Title.release_date == target)
                       .distinct().all())

        for title in want_tv + want_movies:
            try:
                entries = WatchlistEntry.query.filter_by(title_id=title.id, status='want').all()
                names = ', '.join(e.user.username for e in entries)
                send_alert(
                    f"🎬 <b>{title.title}</b> — premieres in {day_str} ({target})\n"
                    f"Want to Watch: {names}"
                )
            except Exception as e:
                log.warning('Premiere reminder failed for %s: %s', title.title, e)


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


def sync_show_statuses(app):
    """Move shows to Watched or Up to Date based on their TMDB status."""
    from app.models import db, Title, WatchlistEntry
    from app import tmdb

    with app.app_context():
        tv_titles = (Title.query
                     .join(WatchlistEntry)
                     .filter(WatchlistEntry.status.in_(['watching', 'uptodate', 'watched']),
                             Title.media_type == 'tv')
                     .distinct().all())

        for title in tv_titles:
            try:
                details = tmdb.get_details(title.tmdb_id, 'tv')
                new_status = details.get('status')
                if new_status and new_status != title.tmdb_status:
                    title.tmdb_status = new_status

                if title.tmdb_status in ('Ended', 'Canceled'):
                    entries = WatchlistEntry.query.filter(
                        WatchlistEntry.title_id == title.id,
                        WatchlistEntry.status.in_(['watching', 'uptodate'])
                    ).all()
                    for e in entries:
                        e.status = 'watched'

                elif title.tmdb_status == 'Returning Series':
                    entries = WatchlistEntry.query.filter_by(
                        title_id=title.id, status='watched'
                    ).all()
                    for e in entries:
                        e.status = 'uptodate'

                db.session.commit()
            except Exception as e:
                log.warning('Status sync failed for %s: %s', title.title, e)


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
        update_want_episode_dates,
        'cron',
        hour=8,
        minute=1,
        args=[app],
        id='update_want_dates',
        replace_existing=True,
    )
    scheduler.add_job(
        send_episode_reminders,
        'cron',
        hour=8,
        minute=5,
        args=[app, 7],
        id='episode_reminders_7d',
        replace_existing=True,
    )
    scheduler.add_job(
        send_episode_reminders,
        'cron',
        hour=8,
        minute=6,
        args=[app, 1],
        id='episode_reminders_1d',
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
    scheduler.add_job(
        sync_show_statuses,
        'cron',
        hour=8,
        minute=30,
        args=[app],
        id='sync_statuses',
        replace_existing=True,
    )
    scheduler.start()
    log.info('RoachFlix scheduler started.')
