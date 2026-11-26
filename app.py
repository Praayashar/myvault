from flask import Flask, jsonify, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
from config import Config
from models import db, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)

    # CSRF protection on every POST. Without it, any site your father visits
    # while logged in could silently send commands to MyVault in his name.
    csrf.init_app(app)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access MyVault.'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from routes.auth import auth
    from routes.main import main
    from routes.finance import finance
    from routes.bills import bills
    from routes.investments import investments
    from routes.life import life
    from routes.vault import vault
    from routes.family import family
    from routes.ai import ai
    from routes.reports import reports
    from routes.cron import cron

    for bp in (auth, main, finance, bills, investments, life,
               vault, family, ai, reports, cron):
        app.register_blueprint(bp)

    # The cron endpoints are machine-to-machine (Google Apps Script) and carry
    # their own CRON_SECRET, so they have no browser session to protect.
    csrf.exempt(cron)

    # Import extra models so they are created by db.create_all()
    from routes.life import FuelLog, HomeTask, HomeLog, GasLog, Trip, TripExpense
    from routes.vault import TicketVault

    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables ready")
        except Exception as e:
            logger.error(f"Database init error: {e}")

        # One-off migration for the reset-token columns added in v1.
        # Postgres only - SQLite does not support this syntax and does not
        # need it, since create_all() builds the table fresh locally.
        if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgresql'):
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("""
                        ALTER TABLE users
                        ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100),
                        ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP;
                    """))
                    conn.commit()
                logger.info("Column migration complete")
            except Exception as e:
                logger.error(f"Column migration skipped: {e}")

        # Warn loudly about anything that will fail silently later.
        if not app.config.get('VAULT_KEY'):
            logger.warning(
                "VAULT_KEY is not set - the password vault cannot save new "
                "entries. Add it in Render > Environment."
            )
        if not app.config.get('CRON_SECRET'):
            logger.warning(
                "CRON_SECRET is not set - automatic reminders are disabled."
            )
        if not app.config.get('GEMINI_API_KEY'):
            logger.warning(
                "GEMINI_API_KEY is not set - the AI assistant will show a "
                "setup message instead of answering."
            )

    @app.context_processor
    def inject_globals():
        return dict(config=app.config, csrf_token=generate_csrf)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Usually means the session expired in a background tab.
        if request.is_json or request.path.startswith(
                ('/finance/', '/vault/', '/trips/', '/goals/', '/emi/')):
            return jsonify({
                'success': False,
                'message': 'Your session expired. Please refresh the page and try again.'
            }), 400
        return ('Your session expired. Please go back, refresh the page '
                'and try again.'), 400

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
