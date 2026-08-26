from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, send_from_directory
from flask_cors import CORS

from database import init_db, create_all
from routes import api


BASE_DIR = str(Path(__file__).resolve().parent)


def create_app() -> Flask:
    load_dotenv()
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
    CORS(app)

    init_db(app, BASE_DIR)
    app.register_blueprint(api)
    create_all(app)

    # 前端静态页面（放在项目根目录）
    @app.get("/")
    def _root():
        return send_from_directory(BASE_DIR, "index.html")

    @app.get("/<path:filename>")
    def _pages(filename: str):
        # 优先静态资源
        if filename.startswith("static/"):
            return send_from_directory(BASE_DIR, filename)

        # 仅允许访问根目录下的 html（避免随意读文件）
        if filename.endswith(".html"):
            return send_from_directory(BASE_DIR, filename)

        # 兼容 favicon
        if filename in {"favicon.ico"} and os.path.exists(os.path.join(BASE_DIR, filename)):
            return send_from_directory(BASE_DIR, filename)

        return ("Not Found", 404)

    return app


if __name__ == "__main__":
    from ai_helper import train_ml_model
    train_ml_model()
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
    

