from __future__ import annotations

import csv
import sys
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report


def main() -> int:
    if len(sys.argv) < 2:
        print("用法：python ml/train_matcher.py <labeled_pairs.csv> [out_model.joblib]")
        print("CSV列：student_text, job_text, label（label=1 表示匹配，0 表示不匹配）")
        print("示例：student_text=技能+经历拼接文本，job_text=JD文本")
        return 2

    data_path = Path(sys.argv[1]).resolve()
    out_path = Path(sys.argv[2]).resolve() if len(sys.argv) >= 3 else Path("ml/matcher.joblib").resolve()
    if not data_path.exists():
        print(f"文件不存在：{data_path}")
        return 2

    X = []
    y = []
    with data_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            s = (r.get("student_text") or "").strip()
            j = (r.get("job_text") or "").strip()
            lab = (r.get("label") or "").strip()
            if not s or not j or lab not in {"0", "1"}:
                continue
            X.append(s + "\n[JOB]\n" + j)
            y.append(int(lab))

    if len(X) < 50:
        print(f"样本过少：{len(X)}（建议至少 200+）")
        return 2

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    pipe: Pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(max_features=40000, ngram_range=(1, 2))),
            ("clf", LogisticRegression(max_iter=2000)),
        ]
    )
    pipe.fit(X_train, y_train)
    pred = pipe.predict(X_test)
    print(classification_report(y_test, pred, digits=4))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, out_path)
    print(f"模型已保存：{out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

