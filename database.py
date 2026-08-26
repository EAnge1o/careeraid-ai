from __future__ import annotations

import os
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def get_sqlite_uri(base_dir: str) -> str:
    db_path = os.path.join(base_dir, "careeraid.db")
    return f"sqlite:///{db_path}"


def init_db(app, base_dir: str) -> None:
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", get_sqlite_uri(base_dir))
    app.config.setdefault("SQLALCHEMY_TRACK_MODIFICATIONS", False)
    db.init_app(app)


def create_all(app) -> None:
    with app.app_context():
        db.create_all()
        _migrate_job_columns(app)


def _migrate_job_columns(app) -> None:
    """为已有 jobs 表添加企业数据字段（若不存在）。"""
    uri = app.config.get("SQLALCHEMY_DATABASE_URI") or ""
    if "sqlite" not in uri:
        return
    from sqlalchemy import text
    for col in ("work_address", "company_name", "company_scale", "company_nature", "job_code", "job_desc", "company_intro"):
        try:
            with db.engine.connect() as conn:
                conn.execute(text(f"ALTER TABLE jobs ADD COLUMN {col} TEXT"))
                conn.commit()
        except Exception:
            pass
