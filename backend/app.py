import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from models.db import db
from flask_jwt_extended import JWTManager
from datetime import timedelta


load_dotenv()

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{os.path.join(basedir, 'instance', 'upscale.db')}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")

    db.init_app(app)
    CORS(app)
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "dev-jwt-secret-change-me")
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=12)
    jwt = JWTManager(app)

    from routes.products import products_bp
    from routes.invoices import invoices_bp
    from routes.inventory import inventory_bp
    from routes.suppliers import suppliers_bp
    from routes.scale import scale_bp
    from routes.auth import auth_bp
    from routes.readings import readings_bp

    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(invoices_bp, url_prefix="/api/invoices")
    app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    app.register_blueprint(suppliers_bp, url_prefix="/api/suppliers")
    app.register_blueprint(scale_bp, url_prefix="/api/scale")
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(readings_bp, url_prefix="/api/readings")

    @app.route("/api/health")
    def health():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)