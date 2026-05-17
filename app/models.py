from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    entries = db.relationship('WatchlistEntry', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Title(db.Model):
    __tablename__ = 'titles'
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, nullable=False)
    media_type = db.Column(db.String(10), nullable=False)  # movie / tv
    category = db.Column(db.String(20), nullable=False)    # Movie / TV Show / Anime
    title = db.Column(db.String(300), nullable=False)
    overview = db.Column(db.Text)
    poster_path = db.Column(db.String(200))
    backdrop_path = db.Column(db.String(200))
    release_date = db.Column(db.String(20))
    tmdb_rating = db.Column(db.Float)
    providers_json = db.Column(db.Text)      # cached streaming providers
    providers_updated = db.Column(db.DateTime)
    episodes_json = db.Column(db.Text)       # cached episode info for TV
    episodes_updated = db.Column(db.DateTime)
    next_episode_date = db.Column(db.String(20))
    entries = db.relationship('WatchlistEntry', back_populates='title', lazy='dynamic')

    __table_args__ = (
        db.UniqueConstraint('tmdb_id', 'media_type', name='uq_tmdb_media'),
    )


class SubscribedService(db.Model):
    __tablename__ = 'subscribed_services'
    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    logo_url = db.Column(db.String(300))


class WatchlistEntry(db.Model):
    __tablename__ = 'watchlist_entries'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title_id = db.Column(db.Integer, db.ForeignKey('titles.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='want')  # want / watching / watched
    category_override = db.Column(db.String(20))   # user can override auto-category
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))
    user = db.relationship('User', back_populates='entries')
    title = db.relationship('Title', back_populates='entries')

    __table_args__ = (
        db.UniqueConstraint('user_id', 'title_id', name='uq_user_title'),
    )

    @property
    def effective_category(self):
        return self.category_override or self.title.category
