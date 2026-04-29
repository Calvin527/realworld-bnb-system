import os
from flask import Flask
from dotenv import load_dotenv


load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')
    app.config['ADMIN_EMAIL'] = os.getenv('ADMIN_EMAIL', '')

    app.config['DB_NAME'] = os.getenv('DB_NAME', 'bnb_system')
    app.config['DB_USER'] = os.getenv('DB_USER', 'postgres')
    app.config['DB_PASSWORD'] = os.getenv('DB_PASSWORD', '')
    app.config['DB_HOST'] = os.getenv('DB_HOST', 'localhost')
    app.config['DB_PORT'] = os.getenv('DB_PORT', '5432')

    app.config['MAIL_ENABLED'] = os.getenv('MAIL_ENABLED', 'False').strip().lower() == 'true'
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').strip().lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', '')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', '')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv(
        'MAIL_DEFAULT_SENDER', os.getenv('MAIL_USERNAME', '')
    )

    from .db import close_db
    app.teardown_appcontext(close_db)

    from .auth.routes import auth_bp
    from .system.routes import system_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(system_bp)

    return app
