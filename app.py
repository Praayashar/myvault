from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    migrate = Migrate(app, db)

    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please login to access MyVault.'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

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
    app.register_blueprint(auth)
    app.register_blueprint(main)
    app.register_blueprint(finance)
    app.register_blueprint(bills)
    app.register_blueprint(investments)
    app.register_blueprint(life)
    app.register_blueprint(vault)
    app.register_blueprint(family)
    app.register_blueprint(ai)
    app.register_blueprint(reports)

    # Import extra models so they are tracked by migrations
    from routes.life import FuelLog, HomeTask, HomeLog, GasLog, Trip, TripExpense
    from routes.vault import TicketVault

    with app.app_context():
        try:
            db.create_all()
            logger.info("Database tables created successfully")
            # Run safe migrations for new columns
            with db.engine.connect() as conn:
                conn.execute(db.text("""
                    ALTER TABLE users
                    ADD COLUMN IF NOT EXISTS reset_token VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS reset_token_expiry TIMESTAMP;
                """))
                conn.commit()
            logger.info("Database migration complete")
        except Exception as e:
            logger.error(f"Database init error: {e}")
            pass

    @app.context_processor
    def inject_config():
        return dict(config=app.config)

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
