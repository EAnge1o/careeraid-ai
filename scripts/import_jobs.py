from __future__ import annotations

import csv
import sys
from pathlib import Path

from app import create_app
from ai_client import AIClient
from ai_helper import AIHelper, _safe_json_dumps
from database import db
from models import Job


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python scripts/import_jobs.py <jobs.csv>")
        print("CSV列建议包含：title,industry,salary,requirements_text")
        return 2

    csv_path = Path(sys.argv[1]).resolve()
    if not csv_path.exists():
        print(f"文件不存在：{csv_path}")
        return 2

    app = create_app()
    ai = AIHelper(client=AIClient())

    with app.app_context():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        imported = 0
        for r in rows:
            title = (r.get("title") or r.get("岗位名称") or "").strip()
            if not title:
                continue
            industry = (r.get("industry") or r.get("行业") or "").strip() or None
            salary = (r.get("salary") or r.get("薪资") or "").strip() or None
            req = (r.get("requirements_text") or r.get("岗位要求") or r.get("要求") or "").strip() or None

            job = db.session.query(Job).filter_by(title=title).one_or_none()
            if not job:
                job = Job(title=title)

            job.industry = industry
            job.salary = salary
            job.requirements_text = req

            job_profile = ai.generate_job_profile(
                {"title": title, "industry": industry, "salary": salary, "requirements_text": req}
            )
            job.job_profile_json = _safe_json_dumps(job_profile)

            db.session.add(job)
            imported += 1

        db.session.commit()
        print(f"导入完成：{imported} 条岗位（含更新）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

