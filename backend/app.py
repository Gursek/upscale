import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from models.db import db
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from datetime import timedelta
from sqlalchemy import text


load_dotenv()
migrate = Migrate()

def create_app(test_config=None):
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    database_url = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(basedir, 'instance', 'upscale.db')}",
    )
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    if not app.config["SECRET_KEY"] and os.getenv("FLASK_ENV") == "production":
        raise RuntimeError("SECRET_KEY is required in production")
    app.config["SECRET_KEY"] = app.config["SECRET_KEY"] or "dev-secret-change-me"
    allowed_origins = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    ]
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
    if not app.config["JWT_SECRET_KEY"] and os.getenv("FLASK_ENV") == "production":
        raise RuntimeError("JWT_SECRET_KEY is required in production")
    app.config["JWT_SECRET_KEY"] = app.config["JWT_SECRET_KEY"] or "dev-jwt-secret-change-me"
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
    jwt = JWTManager(app)

    from routes.products import products_bp
    from routes.invoices import invoices_bp
    from routes.inventory import inventory_bp
    from routes.suppliers import suppliers_bp
    from routes.scale import scale_bp
    from routes.auth import auth_bp
    from routes.readings import readings_bp
    from routes.dashboard import dashboard_bp
    from routes.compliance import compliance_bp

    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(suppliers_bp, url_prefix="/api/suppliers")
    app.register_blueprint(scale_bp, url_prefix="/api/scale")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(readings_bp, url_prefix="/api/readings")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(compliance_bp, url_prefix="/api/compliance")

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()
        if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
            user_columns = {
                row[1] for row in db.session.execute(text("PRAGMA table_info(users)")).fetchall()
            }
            for column in ("sells_fish", "sells_veggies"):
                if column not in user_columns:
                    db.session.execute(text(
                        f"ALTER TABLE users ADD COLUMN {column} BOOLEAN DEFAULT 0"
                    ))
            db.session.commit()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
