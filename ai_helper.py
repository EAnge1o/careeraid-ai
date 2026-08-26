from __future__ import annotations

import json
import re
import math
import pickle
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from trend_analysis import generate_trend_report
import random

from ai_client import AIClient
from cache import (
    cache_job_profile, 
    get_cached_job_profile, 
    cache_match_result, 
    get_cached_match_result
)

# 尝试导入机器学习库
try:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# 不少于 10 个就业岗位/学生能力画像维度
PROFILE_DIMENSIONS = [
    "专业技能",
    "证书要求",
    "创新能力",
    "学习能力",
    "抗压能力",
    "沟通能力",
    "实习能力",
    "团队协作",
    "问题解决",
    "职业稳定性",
]

# 人岗匹配四维度及权重：基础要求、职业技能、职业素养、发展潜力
MATCH_DIMENSIONS_4 = ["基础要求", "职业技能", "职业素养", "发展潜力"]
# 匹配权重：基础要求（40%）+ 职业技能（30%）+ 职业素养（20%）+ 发展潜力（10%）
MATCH_WEIGHTS_4 = {"基础要求": 0.4, "职业技能": 0.3, "职业素养": 0.2, "发展潜力": 0.1}
# 10 维到 4 维的映射（用于加权汇总）
DIM10_TO_DIM4 = {
    "专业技能": "职业技能",
    "证书要求": "基础要求",
    "创新能力": "发展潜力",
    "学习能力": "发展潜力",
    "抗压能力": "职业素养",
    "沟通能力": "职业素养",
    "实习能力": "职业技能",
    "团队协作": "职业素养",
    "问题解决": "职业素养",
    "职业稳定性": "发展潜力",
}


def _tokenize(text: str) -> list[str]:
    if not text:
        return []
    t = re.sub(r"[\r\n\t]+", " ", text)
    t = re.sub(r"[，。；;、/|()（）【】\\[\\]{}<>“”\"'`~!@#$%^&*+=?：:.-]+", " ", t)
    parts = [p.strip().lower() for p in t.split(" ") if p.strip()]
    return parts


def _extract_skills(text: str) -> list[str]:
    if not text:
        return []
    skills = set()
    # 提取具体技术技能，排除通用领域术语
    candidates = re.findall(r"(python|java|c\\+\\+|c#|javascript|typescript|sql|mysql|postgres|mongodb|redis|flask|django|fastapi|spring|react|vue|node|docker|kubernetes|linux|git|excel|powerbi|tableau|pytorch|tensorflow|nlp|llm|prompt|数据分析|机器学习|深度学习|自然语言处理|算法)", text, flags=re.I)
    for c in candidates:
        skills.add(c.lower())
    # 兼容"技能：xxx, yyy"写法
    m = re.search(r"(技能|skill|skills)[:：]\\s*(.+)", text, flags=re.I)
    if m:
        tail = m.group(2)[:200]
        for p in re.split(r"[，,、;；/\\s]+", tail):
            p = p.strip()
            # 过滤通用领域术语
            if 1 <= len(p) <= 24 and p.lower() not in ['产品', '运营', '市场', '测试', '前端', '后端', '数据']:
                skills.add(p.lower())
    # 确保返回的是列表
    return list(sorted(skills))


def _extract_certs(text: str) -> list[str]:
    if not text:
        return []
    certs = set()
    for pat in [r"CET-?4", r"CET-?6", r"计算机二级", r"PMP", r"软考", r"教师资格证", r"ACCA", r"CPA"]:
        if re.search(pat, text, flags=re.I):
            certs.add(pat.upper().replace("\\", ""))
    m = re.search(r"(证书|cert|certs)[:：]\\s*(.+)", text, flags=re.I)
    if m:
        tail = m.group(2)[:200]
        for p in re.split(r"[，,、;；/\\s]+", tail):
            p = p.strip()
            if 1 <= len(p) <= 30:
                certs.add(p)
    return sorted(certs)


def _extract_projects(text: str) -> list[str]:
    """
    从简历文本中提取项目经验
    """
    if not text:
        return []
    projects = []
    # 提取项目经验
    project_patterns = [
        r"(项目|project)[:：]\s*(.+?)(?=(项目|project|实习|intern|教育|education|$))",
        r"(项目经验|project experience)[:：]\s*(.+?)(?=(项目|project|实习|intern|教育|education|$))"
    ]
    for pattern in project_patterns:
        matches = re.finditer(pattern, text, re.S | re.I)
        for match in matches:
            project_desc = match.group(2).strip()
            if project_desc:
                projects.append(project_desc[:200])
    return projects


def _extract_education(text: str) -> dict[str, Any]:
    """
    从简历文本中提取教育背景
    """
    if not text:
        return {}
    education = {}
    # 提取学历
    degree_patterns = [r"(本科|硕士|博士|bachelor|master|phd)" , r"(学历|degree)[:：]\s*([\u4e00-\u9fa5A-Za-z0-9\-\s]{2,40})"]
    for pattern in degree_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            education['degree'] = match.group(1) if len(match.groups()) == 1 else match.group(2)
            break
    # 提取GPA
    gpa_match = re.search(r"(gpa|绩点|平均分)[:：]?\s*([0-9.]+)", text, re.I)
    if gpa_match:
        try:
            education['gpa'] = float(gpa_match.group(2))
        except:
            pass
    return education


def _load_feedback_weights() -> dict[str, float]:
    """
    加载反馈权重，用于优化匹配算法
    """
    try:
        # 从数据库加载用户反馈数据，计算权重
        from database import db
        from models import Feedback
        
        # 获取所有反馈数据
        feedbacks = db.session.query(Feedback).all()
        
        if not feedbacks:
            # 没有反馈数据，使用默认权重
            return {
                "skill_match": 0.4,
                "dimension_match": 0.3,
                "project_relevance": 0.2,
                "education_relevance": 0.1
            }
        
        # 计算平均评分
        avg_rating = sum(f.rating for f in feedbacks) / len(feedbacks)
        
        # 根据反馈调整权重
        weights = {
            "skill_match": 0.4,
            "dimension_match": 0.3,
            "project_relevance": 0.2,
            "education_relevance": 0.1
        }
        
        # 如果平均评分低于3，增加技能匹配的权重
        if avg_rating < 3:
            weights["skill_match"] += 0.1
            weights["dimension_match"] -= 0.05
            weights["project_relevance"] -= 0.05
        # 如果平均评分高于4，增加项目和教育相关性的权重
        elif avg_rating > 4:
            weights["project_relevance"] += 0.05
            weights["education_relevance"] += 0.05
            weights["skill_match"] -= 0.1
        
        # 确保权重和为1
        total = sum(weights.values())
        for key in weights:
            weights[key] = weights[key] / total
        
        return weights
    except Exception:
        # 出错时使用默认权重
        return {
            "skill_match": 0.4,
            "dimension_match": 0.3,
            "project_relevance": 0.2,
            "education_relevance": 0.1
        }

def offline_parse_resume(text: str, manual: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    manual = manual or {}
    skills = _extract_skills(text + " " + (manual.get("skills") or ""))
    certs = _extract_certs(text + " " + (manual.get("certs") or ""))
    internships = manual.get("internships") or ""
    projects = _extract_projects(text)
    education = _extract_education(text)

    major = manual.get("major") or ""
    if not major:
        m = re.search(r"(专业|major)[:：]\s*([\u4e00-\u9fa5A-Za-z0-9\-\s]{2,40})", text)
        if m:
            major = m.group(2).strip()

    # 10 维能力画像 + 完整度与竞争力评分
    dims = {}
    dims["专业技能"] = min(100, 25 + 7 * len(skills))
    dims["证书要求"] = min(100, 30 + 15 * len(certs))
    dims["创新能力"] = min(100, 40 + 5 * len(projects))  # 项目经验提升创新能力
    dims["学习能力"] = 58
    dims["抗压能力"] = 52
    dims["沟通能力"] = 55
    dims["实习能力"] = 65 if internships else 40
    dims["团队协作"] = 54
    dims["问题解决"] = 52
    dims["职业稳定性"] = 50

    # 根据教育背景调整能力评分
    if education.get('gpa') and education['gpa'] >= 3.5:
        dims["学习能力"] = min(100, dims["学习能力"] + 10)
    if education.get('degree') in ['硕士', '博士', 'master', 'phd']:
        dims["专业技能"] = min(100, dims["专业技能"] + 5)

    filled = sum(1 for v in [major, skills, certs, internships, projects, education] if v) if isinstance(skills, list) else 0
    completeness = min(100, 20 + 15 * filled + (15 if skills else 0) + (10 if certs else 0) + (10 if projects else 0))
    competitiveness = min(100, sum(dims.values()) // 10)

    profile = {
        "major": major or None,
        "skills": skills,
        "certs": certs,
        "internships": internships,
        "projects": projects,
        "education": education,
        "highlights": [s for s in (skills[:8] if isinstance(skills, list) else [])],
        "dimensions": dims,
        "completeness_score": round(completeness, 1),
        "competitiveness_score": round(competitiveness, 1),
    }
    return profile


def offline_generate_job_profile(job: dict[str, Any]) -> dict[str, Any]:
    req = (job.get("requirements_text") or "") + " " + (job.get("title") or "") + " " + (job.get("job_desc") or "")
    skills = _extract_skills(req)
    certs = _extract_certs(req)
    # 确保 skills 是列表
    if isinstance(skills, set):
        skills = list(skills)
    # 不少于 10 维岗位画像
    dims = {}
    dims["专业技能"] = min(100, 60 + 4 * len(skills))
    dims["证书要求"] = min(100, 30 + 12 * len(certs))
    dims["创新能力"] = 55
    dims["学习能力"] = 62
    dims["抗压能力"] = 58
    dims["沟通能力"] = 60
    dims["实习能力"] = 55
    dims["团队协作"] = 58
    dims["问题解决"] = 58
    dims["职业稳定性"] = 52
    profile = {
        "title": job.get("title"),
        "industry": job.get("industry"),
        "key_skills": skills[:12],
        "cert_requirements": certs[:6] if certs else [],
        "dimensions": dims,
        "summary": f"该岗位关注：{', '.join(skills[:8])}" if skills else "该岗位关注通用能力与业务理解。",
    }
    return profile


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


def _load_feedback_weights() -> dict[str, float]:
    """
    加载反馈权重，用于优化匹配算法
    """
    # 这里可以从数据库加载用户反馈数据，计算权重
    # 目前使用默认权重
    return {
        "skill_match": 0.4,
        "dimension_match": 0.3,
        "project_relevance": 0.2,
        "education_relevance": 0.1
    }


def _calculate_project_relevance(student_projects: list[str], job_skills: set[str]) -> float:
    """
    计算项目经验与岗位技能的相关性
    """
    if not student_projects or not job_skills:
        return 0.0
    
    relevance_score = 0.0
    for project in student_projects:
        project_skills = set(_extract_skills(project))
        if project_skills:
            overlap = _jaccard(project_skills, job_skills)
            relevance_score += overlap
    
    return min(1.0, relevance_score / len(student_projects))


def _calculate_education_relevance(student_education: dict[str, Any], job_title: str) -> float:
    """
    计算教育背景与岗位的相关性
    """
    if not student_education:
        return 0.0
    
    # 学历权重
    degree_score = 0.0
    degree = student_education.get('degree', '').lower()
    if '博士' in degree or 'phd' in degree:
        degree_score = 1.0
    elif '硕士' in degree or 'master' in degree:
        degree_score = 0.8
    elif '本科' in degree or 'bachelor' in degree:
        degree_score = 0.6
    
    # GPA权重
    gpa_score = 0.0
    gpa = student_education.get('gpa')
    if gpa:
        gpa_score = min(1.0, (gpa - 2.0) / 2.0)  # 假设GPA范围2.0-4.0
    
    return (degree_score + gpa_score) / 2.0


class MLMatchEnhancer:
    """
    机器学习匹配增强器
    使用随机森林算法提升匹配准确性
    """
    
    def __init__(self):
        self.model_path = 'ml_match_model.pkl'
        self.scaler_path = 'ml_match_scaler.pkl'
        self.model = None
        self.scaler = None
        self.load_model()
    
    def load_model(self):
        """加载预训练模型"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                with open(self.model_path, 'rb') as f:
                    self.model = pickle.load(f)
                with open(self.scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                print("模型加载成功")
            else:
                # 如果模型文件不存在，自动训练
                print("模型文件不存在，开始自动训练...")
                train_ml_model()
                # 重新加载模型
                if os.path.exists(self.model_path) and os.path.exists(self.scaler_path):
                    with open(self.model_path, 'rb') as f:
                        self.model = pickle.load(f)
                    with open(self.scaler_path, 'rb') as f:
                        self.scaler = pickle.load(f)
                    print("模型训练并加载成功")
        except Exception as e:
            print(f"加载模型失败: {e}")
            pass
    
    def save_model(self):
        """保存模型"""
        try:
            if self.model and self.scaler:
                with open(self.model_path, 'wb') as f:
                    pickle.dump(self.model, f)
                with open(self.scaler_path, 'wb') as f:
                    pickle.dump(self.scaler, f)
        except Exception:
            pass
    
    def extract_features(self, student_profile: dict, job_profile: dict) -> List[float]:
        """提取特征向量"""
        # 技能匹配
        s_skills = student_profile.get("skills", [])
        j_skills = job_profile.get("key_skills", [])
        # 确保 s_skills 和 j_skills 是可迭代的
        if isinstance(s_skills, set):
            s_skills = list(s_skills)
        if isinstance(j_skills, set):
            j_skills = list(j_skills)
        # 转换为集合进行计算
        s_skills_set = set(s_skills)
        j_skills_set = set(j_skills)
        skill_overlap = _jaccard(s_skills_set, j_skills_set)
        
        # 维度匹配
        s_dim = student_profile.get("dimensions", {})
        j_dim = job_profile.get("dimensions", {})
        dim_scores = []
        # 直接硬编码维度列表，避免使用可能被修改的PROFILE_DIMENSIONS变量
        profile_dimensions = [
            "专业技能",
            "证书要求",
            "创新能力",
            "学习能力",
            "抗压能力",
            "沟通能力",
            "实习能力",
            "团队协作",
            "问题解决",
            "职业稳定性",
        ]
        for k in profile_dimensions:
            sv = float(s_dim.get(k, 50))
            jv = float(j_dim.get(k, 50))
            diff = abs(sv - jv)
            dim_scores.append(max(0.0, 100.0 - diff * 1.2) / 100.0)
        
        # 项目相关性
        student_projects = student_profile.get("projects", [])
        project_relevance = _calculate_project_relevance(student_projects, j_skills_set)
        
        # 教育相关性
        student_education = student_profile.get("education", {})
        job_title = job_profile.get("title", "")
        education_relevance = _calculate_education_relevance(student_education, job_title)
        
        # 其他特征
        num_skills = len(s_skills)
        num_projects = len(student_projects)
        
        # 组合特征
        features = [skill_overlap, project_relevance, education_relevance, num_skills, num_projects]
        features.extend(dim_scores)
        
        return features
    
    def train(self, X, y):
        """训练模型"""
        if not ML_AVAILABLE:
            return
        
        # 数据标准化
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # 划分训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
        
        # 训练随机森林模型
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        
        # 评估模型
        y_pred = self.model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        # 计算R2评分
        from sklearn.metrics import r2_score
        r2 = r2_score(y_test, y_pred)
        print(f"Model trained with MSE: {mse:.4f}, R2: {r2:.4f}")
        
        # 保存模型
        self.save_model()
    
    def predict(self, student_profile: dict, job_profile: dict) -> float:
        """预测匹配分数"""
        if not ML_AVAILABLE or not self.model or not self.scaler:
            return None
        
        try:
            features = self.extract_features(student_profile, job_profile)
            features_scaled = self.scaler.transform([features])
            score = self.model.predict(features_scaled)[0]
            return min(100.0, max(0.0, score))
        except Exception as e:
            print(f"预测失败: {e}")
            return None


# 创建机器学习增强器实例
ml_enhancer = MLMatchEnhancer()


def check_model_status():
    """检查模型状态"""
    if not ML_AVAILABLE:
        return {"status": "error", "message": "机器学习库未安装"}
    
    if ml_enhancer.model is None or ml_enhancer.scaler is None:
        return {"status": "warning", "message": "模型未加载，将使用规则匹配"}
    
    return {"status": "ok", "message": "模型已就绪"}


def offline_match(student_profile: dict[str, Any], job_profile: dict[str, Any]) -> dict[str, Any]:
    # 确保技能是集合类型
    s_skills = student_profile.get("skills") or []
    j_skills = job_profile.get("key_skills") or []
    # 确保 s_skills 和 j_skills 是可迭代的
    if isinstance(s_skills, set):
        s_skills = list(s_skills)
    if isinstance(j_skills, set):
        j_skills = list(j_skills)
    # 转换为集合进行计算
    s_skills_set = set(s_skills)
    j_skills_set = set(j_skills)
    skill_overlap = _jaccard(s_skills_set, j_skills_set)

    s_dim = student_profile.get("dimensions") or {}
    j_dim = job_profile.get("dimensions") or {}
    dim_scores = {}
    # 直接硬编码维度列表，避免使用可能被修改的PROFILE_DIMENSIONS变量
    profile_dimensions = [
        "专业技能",
        "证书要求",
        "创新能力",
        "学习能力",
        "抗压能力",
        "沟通能力",
        "实习能力",
        "团队协作",
        "问题解决",
        "职业稳定性",
    ]
    for k in profile_dimensions:
        sv = float(s_dim.get(k, 50))
        jv = float(j_dim.get(k, 50))
        diff = abs(sv - jv)
        dim_scores[k] = round(max(0.0, 100.0 - diff * 1.2), 1)

    # 四维度能力分析并加权综合：基础要求、职业技能、职业素养、发展潜力
    dim4_scores = {}
    for d4 in MATCH_DIMENSIONS_4:
        vals = [dim_scores.get(d10, 50) for d10, parent in DIM10_TO_DIM4.items() if parent == d4]
        dim4_scores[d4] = round(sum(vals) / max(1, len(vals)), 1)
    
    # 计算项目相关性
    student_projects = student_profile.get("projects") or []
    project_relevance = _calculate_project_relevance(student_projects, j_skills_set)
    
    # 计算教育相关性
    student_education = student_profile.get("education") or {}
    job_title = job_profile.get("title", "")
    education_relevance = _calculate_education_relevance(student_education, job_title)
    
    # 加载反馈权重
    weights = _load_feedback_weights()
    
    # 加权计算
    weighted = sum(MATCH_WEIGHTS_4.get(d, 0) * (dim4_scores.get(d, 0) / 100.0) for d in MATCH_DIMENSIONS_4)
    raw = (
        weights["skill_match"] * skill_overlap +
        weights["dimension_match"] * weighted +
        weights["project_relevance"] * project_relevance +
        weights["education_relevance"] * education_relevance
    )
    score = round(100.0 * min(1.0, (1.0 / (1.0 + math.exp(-6 * (raw - 0.35))))), 1)
    
    # 生成基础推理文本
    reasoning = "；".join([f"{d}={dim4_scores.get(d, 0)}%" for d in MATCH_DIMENSIONS_4]) + \
               f"；技能重叠{round(skill_overlap*100,1)}%" +\
               f"；项目相关{round(project_relevance*100,1)}%" +\
               f"；教育相关{round(education_relevance*100,1)}%"
    
    # 使用机器学习模型增强匹配
    ml_score = ml_enhancer.predict(student_profile, job_profile)
    if ml_score is not None:
        # 融合规则匹配和机器学习预测结果
        score = round((score * 0.7 + ml_score * 0.3), 1)
        reasoning += f"；AI增强匹配{round(ml_score,1)}%"
    
    reasoning += "。"

    # 过滤掉通用领域术语
    common_terms = {'产品', '运营', '市场', '测试', '前端', '后端', '数据'}
    missing = [skill for skill in sorted(list(j_skills_set - s_skills_set)) if skill not in common_terms][:10]
    
    # 生成更具体的建议
    suggestions = []
    if missing:
        suggestions.append(f"优先补齐：{', '.join(missing[:5])}")
    
    # 根据项目经验添加建议
    if not student_projects:
        suggestions.append("建议增加项目经验，通过实际项目提升技能应用能力。")
    elif len(student_projects) < 2:
        suggestions.append("建议再增加1-2个项目经验，丰富作品集。")
    
    # 根据教育背景添加建议
    if not student_education.get('degree'):
        suggestions.append("建议在简历中明确教育背景，包括学历和GPA。")
    
    # 通用建议
    suggestions.append("用 1-2 个作品集项目证明能力（含 README、截图、部署链接）。")
    suggestions.append("针对目标岗位 JD 做简历关键词优化与 STAR 案例准备。")
    
    gap = {
        "missing_skills": missing,
        "suggestions": suggestions,
        "project_relevance": round(project_relevance * 100, 1),
        "education_relevance": round(education_relevance * 100, 1),
        "ml_enhanced": ml_score is not None
    }

    return {
        "score": score,
        "dimension_scores": dim_scores,
        "dimension_scores_4": dim4_scores,
        "gap_analysis": gap,
        "reasoning": reasoning,
        "ml_enhanced": ml_score is not None
    }


def train_ml_model():
    """
    训练机器学习模型
    可以在系统初始化时调用，或通过API触发
    """
    if not ML_AVAILABLE:
        return {"ok": False, "message": "机器学习库未安装"}
    
    try:
        # 尝试从数据库获取真实数据
        X = []
        y = []
        
        try:
            from database import db
            from models import MatchResult, Student, Job
            
            # 获取所有匹配结果
            match_results = db.session.query(MatchResult).all()
            
            if match_results:
                for match in match_results:
                    try:
                        # 获取学生信息
                        student = db.session.get(Student, match.student_id)
                        if not student or not student.resume_parsed_json:
                            continue
                        
                        # 获取岗位信息
                        job = db.session.get(Job, match.job_id)
                        if not job:
                            continue
                        
                        # 解析学生画像和岗位画像
                        import json
                        student_profile = json.loads(student.resume_parsed_json)
                        
                        if job.job_profile_json:
                            job_profile = json.loads(job.job_profile_json)
                        else:
                            # 生成岗位画像
                            job_dict = job.to_dict()
                            job_dict['id'] = job.id
                            job_profile = offline_generate_job_profile(job_dict)
                        
                        # 提取特征
                        features = ml_enhancer.extract_features(student_profile, job_profile)
                        
                        # 获取目标分数
                        target_score = match.score
                        
                        X.append(features)
                        y.append(target_score)
                    except Exception:
                        # 跳过解析失败的记录
                        continue
        except Exception:
            # 数据库访问失败，使用模拟数据
            pass
        
        # 如果没有真实数据，使用模拟数据
        if not X:
            # 生成一些模拟数据
            for i in range(1000):
                # 生成随机特征
                skill_overlap = random.uniform(0, 1)
                project_relevance = random.uniform(0, 1)
                education_relevance = random.uniform(0, 1)
                # 确保num_skills和num_projects在合理范围内
                num_skills = random.randint(0, 20)  # 合理范围：0-20
                num_projects = random.randint(0, 5)   # 合理范围：0-5
                
                # 生成维度分数（模拟学生和岗位的维度差异）
                profile_dimensions = [
                    "专业技能", "证书要求", "创新能力", "学习能力", "抗压能力",
                    "沟通能力", "实习能力", "团队协作", "问题解决", "职业稳定性"
                ]
                # 模拟学生和岗位在各个维度上的分数
                student_dims = [random.uniform(30, 90) for _ in profile_dimensions]
                job_dims = [random.uniform(40, 100) for _ in profile_dimensions]
                # 计算维度差异，与extract_features方法一致
                dim_scores = []
                for sv, jv in zip(student_dims, job_dims):
                    diff = abs(sv - jv)
                    dim_scores.append(max(0.0, 100.0 - diff * 1.2) / 100.0)
                
                # 组合特征
                features = [skill_overlap, project_relevance, education_relevance, num_skills, num_projects]
                features.extend(dim_scores)
                
                # 生成目标分数（模拟真实匹配分数）
                base_score = (
                    0.4 * skill_overlap +
                    0.3 * sum(dim_scores[:5])/5 +
                    0.2 * project_relevance +
                    0.1 * education_relevance
                )
                # 添加一些噪声
                final_score = min(100, max(0, 100 * base_score + random.uniform(-10, 10)))
                
                X.append(features)
                y.append(final_score)
        
        # 训练模型
        ml_enhancer.train(X, y)
        
        return {"ok": True, "message": f"模型训练成功，使用了{len(X)}条数据"}
    except Exception as e:
        return {"ok": False, "message": f"模型训练失败: {str(e)}"}


def offline_generate_report(
    student: dict[str, Any], top_matches: list[dict[str, Any]], goal: str = ""
) -> str:
    name = student.get("name") or student.get("username") or "同学"
    major = student.get("major") or ""
    goal = goal or "找到与自身优势匹配的高成长岗位"

    lines = []
    lines.append("职业生涯发展报告（AI 生成）")
    lines.append("")
    lines.append("一、基本信息")
    lines.append(f"- 姓名/账号：{name}")
    if major:
        lines.append(f"- 专业：{major}")
    lines.append(f"- 职业目标：{goal}")
    lines.append("")

    lines.append("二、学生就业能力画像")
    try:
        resume_profile = json.loads(student.get("resume_parsed_json") or "{}")
    except Exception:
        resume_profile = {}
    dims = resume_profile.get("dimensions") or {}
    if dims:
        lines.append("- 能力维度得分（0-100）：")
        # 直接硬编码维度列表，避免使用可能被修改的PROFILE_DIMENSIONS变量
        profile_dimensions = [
            "专业技能",
            "证书要求",
            "创新能力",
            "学习能力",
            "抗压能力",
            "沟通能力",
            "实习能力",
            "团队协作",
            "问题解决",
            "职业稳定性",
        ]
        for k in profile_dimensions:
            if k in dims:
                lines.append(f"  - {k}：{dims[k]}")
    comp = resume_profile.get("completeness_score") or resume_profile.get("competitiveness_score")
    if comp is not None:
        lines.append(f"- 画像完整度/竞争力评分：{comp}")
    skills = resume_profile.get("skills") or []
    if skills:
        lines.append(f"- 关键技能：{', '.join(skills[:12])}")
    lines.append("")

    lines.append("三、职业探索与岗位匹配（人岗匹配度分析）")
    for i, m in enumerate(top_matches[:5], start=1):
        lines.append(f"{i}. {m.get('job_title')}（综合匹配度 {m.get('score')}%）")
        d4 = m.get("dimension_scores_4") or m.get("dimension_scores") or {}
        for d in MATCH_DIMENSIONS_4:
            if d in d4:
                lines.append(f"   - {d}：{d4[d]}%")
        gap = m.get("gap_analysis") or {}
        miss = gap.get("missing_skills") or []
        if miss:
            lines.append(f"   - 主要差距：{', '.join(miss[:6])}")
    lines.append("")

    lines.append("四、职业目标设定与职业路径规划")
    if top_matches:
        top = top_matches[0]
        lines.append(f"- 近期主攻方向：{top.get('job_title')}（结合个人意愿与市场需求）")
        lines.append("- 垂直晋升路径示例：实习/校招 → 初级岗位（0-2年）→ 中级（2-4年）→ 资深/小组长（4-6年）→ 负责人/专家")
        lines.append("- 换岗路径：同领域相近岗位可互相迁移（如数据分析↔商业分析↔产品分析）；技术岗可向产品/项目管理延伸。")
    lines.append("")

    lines.append("五、行动计划与成果展示（分阶段可执行）")
    lines.append("- 短期（1-2 周）：完善简历（JD 关键词+量化成果），整理 3 个 STAR 案例；选定 1 个目标岗位序列。")
    lines.append("- 中期（1-3 个月）：完成 1 个作品集项目（可部署/可复现），补齐缺失技能清单前 3 项；投递与复盘（每周 30-50 个），模拟面试 6-10 次。")
    lines.append("- 评估周期与指标：每 2 周复盘简历打开率与面试邀约；每月更新能力画像与匹配度；按季度调整目标岗位与学习路径。")
    lines.append("")

    lines.append("六、备注")
    lines.append("- 本报告基于当前简历/测评数据自动生成，扬长避短、精准匹配；补充经历与作品后可重新生成以提升准确率。")
    return "\n".join(lines)


def offline_personality_analysis(
    resume_profile: dict[str, Any],
    personality_test: dict[str, Any],
) -> dict[str, Any]:
    """
    性格分析 + 岗位适配 + 短板诊断（离线规则版）。
    例如：成绩好但内向 -> 诊断沟通/表达短板，推荐可提升方向与适配岗位。
    """
    scores = personality_test.get("scores") or {}
    summary = personality_test.get("summary") or {}
    note = personality_test.get("note") or ""
    career_interest = personality_test.get("career_interest") or {}
    resources = personality_test.get("resources") or []

    dims = resume_profile.get("dimensions") or {}
    skills = resume_profile.get("skills") or []
    competitiveness = float(resume_profile.get("competitiveness_score") or 50)

    e = float(scores.get("E") or 50)
    c = float(scores.get("C") or 50)
    n = float(scores.get("N") or 50)
    o = float(scores.get("O") or 50)
    a = float(scores.get("A") or 50)

    is_introvert = e < 40
    is_high_grade = competitiveness >= 70 or float(dims.get("专业技能", 50)) >= 65
    is_anxious = n >= 60
    is_low_conscientious = c < 45

    shortcomings = []
    suggestions = []
    job_fit = []

    if is_high_grade and is_introvert:
        shortcomings.append("成绩优秀但偏内向，沟通表达、公开演讲可能是短板")
        suggestions.append("优先提升：小组汇报、模拟面试、1分钟自我介绍；可从小范围分享开始")
        job_fit.extend(["技术研发、数据分析、算法工程师、后端开发等偏独立交付的岗位"])

    if is_anxious:
        shortcomings.append("抗压与情绪管理需要关注")
        suggestions.append("建议选择支持体系较好的团队，并练习正念/时间管理")

    if is_low_conscientious:
        shortcomings.append("计划性与执行力可加强")
        suggestions.append("用甘特图拆解目标，设置阶段性检查点，养成复盘习惯")

    if o >= 65:
        job_fit.extend(["产品、创新方向、研究型岗位"])
    if a >= 65:
        job_fit.extend(["项目管理、运营、协作型岗位"])

    job_fit = list(dict.fromkeys(job_fit))[:8]
    if not shortcomings:
        shortcomings.append("整体较均衡，可结合兴趣与资源聚焦 1-2 个方向")
    if not suggestions:
        suggestions.append("继续巩固核心技能，多参加实习/项目积累经验")

    return {
        "summary": "；".join(shortcomings),
        "shortcomings": shortcomings,
        "suggestions": suggestions,
        "job_fit": job_fit,
        "scores_5": scores,
        "tags": summary.get("tags", []),
        "env": summary.get("env", []),
    }


def report_completeness_check(content: str) -> dict[str, Any]:
    """报告内容完整性检查，返回缺失章节与建议。"""
    required = ["基本信息", "能力画像", "岗位匹配", "职业目标", "路径", "行动计划", "评估"]
    missing = []
    for s in required:
        if s not in content:
            missing.append(s)
    return {"complete": len(missing) == 0, "missing_sections": missing}


@dataclass
class AIHelper:
    client: AIClient

    def parse_resume(self, resume_text: str, manual: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        manual = manual or {}
        system = "你是职业规划助手，从简历中抽取结构化就业能力画像。画像须包含：专业技能、证书、创新能力、学习能力、抗压能力、沟通能力、实习能力、团队协作、问题解决、职业稳定性；并给出完整度与竞争力评分(0-100)。"
        # 直接硬编码维度列表，避免使用可能被修改的PROFILE_DIMENSIONS变量
        profile_dimensions = [
            "专业技能",
            "证书要求",
            "创新能力",
            "学习能力",
            "抗压能力",
            "沟通能力",
            "实习能力",
            "团队协作",
            "问题解决",
            "职业稳定性",
        ]
        # 使用json.dumps生成schema字符串，避免字符串格式化的语法错误
        schema_dict = {
            "major": "专业(可空)",
            "skills": ["技能"],
            "certs": ["证书"],
            "internships": "实习摘要",
            "highlights": ["亮点"],
            "dimensions": {d: "0-100" for d in profile_dimensions},
            "completeness_score": "0-100",
            "competitiveness_score": "0-100"
        }
        schema = json.dumps(schema_dict, ensure_ascii=False)
        prompt = f"请解析以下简历文本，并结合手动信息输出 JSON。\n\n【手动信息】{_safe_json_dumps(manual)}\n\n【简历文本】\n{resume_text[:8000]}"
        try:
            data = self.client.chat_json(system, prompt, schema_hint=schema)
            if isinstance(data, dict) and "skills" in data and "dimensions" in data:
                return data
        except Exception:
            pass
        return offline_parse_resume(resume_text, manual=manual)

    def generate_job_profile(self, job: dict[str, Any]) -> dict[str, Any]:
        # 尝试从缓存获取
        job_id = job.get('id')
        if job_id:
            cached_profile = get_cached_job_profile(job_id)
            if cached_profile:
                return cached_profile
        
        system = "你是人岗匹配专家，将岗位JD抽象成不少于10维的岗位画像：专业技能、证书要求、创新能力、学习能力、抗压能力、沟通能力、实习能力、团队协作、问题解决、职业稳定性；每维0-100。"
        # 直接硬编码维度列表，避免使用可能被修改的PROFILE_DIMENSIONS变量
        profile_dimensions = [
            "专业技能",
            "证书要求",
            "创新能力",
            "学习能力",
            "抗压能力",
            "沟通能力",
            "实习能力",
            "团队协作",
            "问题解决",
            "职业稳定性",
        ]
        # 使用json.dumps生成schema字符串，避免字符串格式化的语法错误
        schema_dict = {
            "title": "岗位名称",
            "industry": "行业",
            "key_skills": ["核心技能"],
            "cert_requirements": ["证书要求"],
            "dimensions": {d: "0-100" for d in profile_dimensions},
            "summary": "画像描述"
        }
        schema = json.dumps(schema_dict, ensure_ascii=False)
        prompt = f"根据岗位信息输出岗位画像JSON。\n\n{_safe_json_dumps(job)}"
        
        try:
            data = self.client.chat_json(system, prompt, schema_hint=schema)
            if isinstance(data, dict) and "key_skills" in data and "dimensions" in data:
                # 缓存结果
                if job_id:
                    cache_job_profile(job_id, data)
                return data
        except Exception:
            pass
        
        profile = offline_generate_job_profile(job)
        # 缓存离线生成的结果
        if job_id:
            cache_job_profile(job_id, profile)
        return profile

    def match(self, student_profile: dict[str, Any], job_profile: dict[str, Any], use_online: bool = True) -> dict[str, Any]:
        """同时执行在线和离线匹配，返回两种结果"""
        # 在线匹配
        online_result = None
        if use_online:
            system = "你是人岗匹配模型。从基础要求、职业技能、职业素养、发展潜力四维度对比学生与岗位，输出每维得分(0-100)、综合加权得分、缺失技能与建议。"
            schema = '{"score":0-100,"dimension_scores":{},"dimension_scores_4":{"基础要求":0-100,"职业技能":0-100,"职业素养":0-100,"发展潜力":0-100},"gap_analysis":{"missing_skills":[],"suggestions":[]},"reasoning":"一句话"}'
            prompt = f"学生画像：{_safe_json_dumps(student_profile)}\n岗位画像：{_safe_json_dumps(job_profile)}\n请输出JSON。"
            try:
                data = self.client.chat_json(system, prompt, schema_hint=schema)
                if isinstance(data, dict) and "score" in data:
                    online_result = data
            except Exception:
                pass
        
        # 离线匹配
        offline_result = offline_match(student_profile, job_profile)
        
        # 整合结果
        result = {
            "score": offline_result["score"],  # 默认使用离线结果作为主得分
            "dimension_scores": offline_result["dimension_scores"],
            "dimension_scores_4": offline_result["dimension_scores_4"],
            "gap_analysis": offline_result["gap_analysis"],
            "reasoning": offline_result["reasoning"],
            "ml_enhanced": offline_result["ml_enhanced"],
            "online_result": online_result,  # 在线结果
            "offline_result": offline_result  # 离线结果
        }
        
        return result

    def generate_report(
        self, student: dict[str, Any], top_matches: list[dict[str, Any]], goal: str = ""
    ) -> str:
        system = "你是大学生职业规划顾问，输出结构化的职业规划报告（中文）。"
        prompt = f"学生信息：{_safe_json_dumps(student)}\n匹配结果TOP5：{_safe_json_dumps(top_matches[:5])}\n目标：{goal or ''}\n请输出一份可直接展示的报告正文。"
        try:
            data = self.client.chat_json(system, prompt, schema_hint="直接输出 {\"content\":\"...\"} 或纯文本")
            if isinstance(data, dict) and "content" in data and isinstance(data["content"], str):
                return data["content"]
        except Exception:
            pass
        return offline_generate_report(student, top_matches, goal=goal)

    def analyze_personality_for_jobs(
        self, resume_profile: dict[str, Any], personality_test: dict[str, Any]
    ) -> dict[str, Any]:
        """性格分析→岗位适配+短板诊断+可提升建议。优先使用离线处理，只有在需要时才调用AI模型。"""
        # 首先使用离线处理
        result = offline_personality_analysis(resume_profile, personality_test)
        
        # 检查是否需要调用AI模型（例如，当用户提供了补充信息时）
        note = personality_test.get("note") or ""
        if note:
            # 只有当用户提供了补充信息时，才调用AI模型
            system = (
                "你是职业规划与心理学专家。根据简历能力画像与性格测评（Big Five），"
                "你必须：1) 诊断短板（如成绩好但内向→沟通表达短板）；2) 推荐适合岗位类型；"
                "3) 给出可执行的提升建议。输出 JSON：summary、shortcomings、suggestions、job_fit。"
            )
            prompt = (
                f"简历画像：{_safe_json_dumps(resume_profile)}\n\n性格测评：{_safe_json_dumps(personality_test)}\n\n"
                "输出 JSON：{\"summary\":\"一句话\",\"shortcomings\":[],\"suggestions\":[],\"job_fit\":[]}"
            )
            try:
                data = self.client.chat_json(system, prompt, schema_hint="")
                if isinstance(data, dict) and "shortcomings" in data:
                    return data
            except Exception:
                pass
        
        # 默认使用离线处理结果
        return result