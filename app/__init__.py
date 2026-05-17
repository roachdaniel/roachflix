from flask import Flask, send_from_directory
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from app.models import db, User

login_manager = LoginManager()
migrate = Migrate()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = ''

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth import auth_bp
    from app.watchlist import watchlist_bp
    from app.search import search_bp
    from app.calendar_integration import calendar_bp
    from app.settings import settings_bp
    from app.import_data import import_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(watchlist_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(import_bp)

    @app.route('/sw.js')
    def service_worker():
        resp = send_from_directory(app.static_folder, 'sw.js')
        resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        resp.headers['Service-Worker-Allowed'] = '/'
        return resp

    from app.notifications.scheduler import init_scheduler
    with app.app_context():
        init_scheduler(app)

    return app
