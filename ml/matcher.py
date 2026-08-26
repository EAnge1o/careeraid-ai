from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib


class TrainedMatcher:
    """
    训练模型的推理封装（可选）。
    - 用于企业数据集训练后，将“人岗匹配”从规则/LLM 逐步迁移到可解释的监督模型。
    """

    def __init__(self, model_path: str = "ml/matcher.joblib") -> None:
        self.model_path = Path(model_path)
        self.model = None

    def load(self) -> None:
        if not self.model_path.exists():
            raise FileNotFoundError(f"模型不存在：{self.model_path}")
        self.model = joblib.load(self.model_path)

    def predict_proba(self, student_text: str, job_text: str) -> float:
        if self.model is None:
            self.load()
        x = [student_text + "\n[JOB]\n" + job_text]
        proba = self.model.predict_proba(x)[0][1]
        return float(proba)

