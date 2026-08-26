# -*- coding: utf-8 -*-
"""
导入企业提供的岗位数据（XLS/XLSX）。
数据字段：职位名称、工作地址、薪资范围、公司全称、所属行业、人员规模、企业性质、职位编码、职位描述、公司简介。
"""
from __future__ import annotations

import sys
from pathlib import Path

# 项目根目录加入 path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from ai_client import AIClient
from ai_helper import AIHelper, _safe_json_dumps
from database import db
from models import Job


# 企业数据列名多种写法
COL_TITLE = ("职位名称", "岗位名称", "title", "岗位")
COL_ADDRESS = ("工作地址", "地址", "work_address", "工作地点")
COL_SALARY = ("薪资范围", "薪资", "salary", "工资")
COL_COMPANY = ("公司全称", "公司名称", "company_name", "企业")
COL_INDUSTRY = ("所属行业", "行业", "industry")
COL_SCALE = ("人员规模", "规模", "company_scale")
COL_NATURE = ("企业性质", "性质", "company_nature")
COL_JOB_CODE = ("职位编码", "编码", "job_code")
COL_JOB_DESC = ("职位描述", "岗位描述", "职位要求", "job_desc", "requirements_text", "岗位要求")
COL_COMPANY_INTRO = ("公司简介", "企业简介", "company_intro")


def _col(row: dict, keys: tuple, default: str = "") -> str:
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return default


def _read_xlsx(path: Path) -> list[dict]:
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return []
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    return [dict(zip(headers, row)) for row in rows[1:] if any(v is not None for v in row)]


def _read_xls(path: Path) -> list[dict]:
    import xlrd
    wb = xlrd.open_workbook(str(path))
    sheet = wb.sheet_by_index(0)
    headers = [str(sheet.cell_value(0, c)).strip() for c in range(sheet.ncols)]
    rows = []
    for r in range(1, sheet.nrows):
        row = {}
        for c in range(sheet.ncols):
            val = sheet.cell_value(r, c)
            if isinstance(val, float) and val == int(val):
                val = int(val)
            row[headers[c]] = val
        if any(v is not None and str(v).strip() for v in row.values()):
            rows.append(row)
    return rows


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python scripts/import_jobs_xls.py <岗位数据.xls|.xlsx>")
        print("支持的列名：职位名称、工作地址、薪资范围、公司全称、所属行业、人员规模、企业性质、职位编码、职位描述、公司简介")
        return 2

    path = Path(sys.argv[1]).resolve()
    if not path.exists():
        print(f"文件不存在：{path}")
        return 2

    suffix = path.suffix.lower()
    if suffix == ".xlsx":
        raw_rows = _read_xlsx(path)
    elif suffix == ".xls":
        raw_rows = _read_xls(path)
    else:
        print("仅支持 .xls 或 .xlsx 文件")
        return 2

    app = create_app()
    ai = AIHelper(client=AIClient())

    with app.app_context():
        imported = 0
        for row in raw_rows:
            title = _col(row, COL_TITLE)
            if not title:
                continue
            work_address = _col(row, COL_ADDRESS)
            salary = _col(row, COL_SALARY)
            company_name = _col(row, COL_COMPANY)
            industry = _col(row, COL_INDUSTRY)
            company_scale = _col(row, COL_SCALE)
            company_nature = _col(row, COL_NATURE)
            job_code = _col(row, COL_JOB_CODE)
            job_desc = _col(row, COL_JOB_DESC)
            company_intro = _col(row, COL_COMPANY_INTRO)

            job = db.session.query(Job).filter_by(title=title).first()
            if not job:
                job = Job(title=title)

            job.work_address = work_address or None
            job.salary = salary or None
            job.company_name = company_name or None
            job.industry = industry or None
            job.company_scale = company_scale or None
            job.company_nature = company_nature or None
            job.job_code = job_code or None
            job.job_desc = job_desc or None
            job.company_intro = company_intro or None
            job.requirements_text = job.requirements_text or job_desc or None

            job_dict = job.to_dict()
            profile = ai.generate_job_profile(job_dict)
            job.job_profile_json = _safe_json_dumps(profile)

            db.session.add(job)
            imported += 1

        db.session.commit()
        print(f"导入完成：{imported} 条岗位（XLS/XLSX）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
