import json
import time
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import requests
from bs4 import BeautifulSoup

# 项目根目录
ROOT = Path(__file__).resolve().parent

# 固定的计算机行业趋势知识资料
COMPUTER_INDUSTRY_TRENDS = {
    "计算机软件": {
        "growth_rate": 9.2,
        "hot_jobs": ["软件工程师", "前端开发", "后端开发", "全栈开发", "移动开发"],
        "emerging_skills": ["人工智能", "机器学习", "云计算", "大数据", "DevOps"],
        "future_outlook": "计算机软件行业将持续快速增长，AI和云计算成为核心驱动力，数字化转型需求旺盛",
        "recruitment_trend": "技术岗需求持续增长，特别是AI、云计算、大数据相关岗位，薪资水平高于平均水平"
    },
    "互联网": {
        "growth_rate": 8.5,
        "hot_jobs": ["产品经理", "运营专员", "数据分析师", "用户体验设计师"],
        "emerging_skills": ["产品思维", "数据分析", "用户研究", "增长黑客", "内容创作"],
        "future_outlook": "互联网行业逐渐成熟，精细化运营和用户体验成为核心竞争力",
        "recruitment_trend": "产品和运营岗竞争激烈，需要具备数据分析和用户洞察能力"
    },
    "人工智能": {
        "growth_rate": 15.8,
        "hot_jobs": ["AI工程师", "机器学习工程师", "数据科学家", "算法工程师"],
        "emerging_skills": ["深度学习", "自然语言处理", "计算机视觉", "强化学习", "大模型应用"],
        "future_outlook": "人工智能行业爆发式增长，大模型和生成式AI成为热点",
        "recruitment_trend": "AI相关岗位需求激增，薪资水平高，竞争激烈"
    },
    "云计算": {
        "growth_rate": 12.3,
        "hot_jobs": ["云架构师", "DevOps工程师", "云运维工程师", "容器工程师"],
        "emerging_skills": ["Kubernetes", "Docker", "AWS/Azure/GCP", "CI/CD", "微服务"],
        "future_outlook": "云计算成为企业数字化转型的基础设施，混合云和边缘计算成为趋势",
        "recruitment_trend": "云相关技能需求持续增长，认证和项目经验重要"
    }
}

# 计算机相关岗位关联性数据
COMPUTER_JOB_RELATIONS = {
    "前端开发": {
        "related_jobs": ["后端开发", "全栈开发", "UI/UX设计", "产品经理"],
        "skill_overlap": {"后端开发": 0.6, "全栈开发": 0.8, "UI/UX设计": 0.4, "产品经理": 0.3},
        "transition_difficulty": {"后端开发": 3, "全栈开发": 2, "UI/UX设计": 4, "产品经理": 3}
    },
    "后端开发": {
        "related_jobs": ["前端开发", "全栈开发", "DevOps工程师", "数据工程师"],
        "skill_overlap": {"前端开发": 0.6, "全栈开发": 0.8, "DevOps工程师": 0.5, "数据工程师": 0.4},
        "transition_difficulty": {"前端开发": 3, "全栈开发": 2, "DevOps工程师": 3, "数据工程师": 4}
    },
    "数据分析师": {
        "related_jobs": ["数据科学家", "商业分析师", "数据工程师", "产品经理"],
        "skill_overlap": {"数据科学家": 0.7, "商业分析师": 0.8, "数据工程师": 0.5, "产品经理": 0.4},
        "transition_difficulty": {"数据科学家": 4, "商业分析师": 2, "数据工程师": 3, "产品经理": 3}
    },
    "产品经理": {
        "related_jobs": ["运营", "市场营销", "UI/UX设计", "项目经理"],
        "skill_overlap": {"运营": 0.7, "市场营销": 0.6, "UI/UX设计": 0.5, "项目经理": 0.8},
        "transition_difficulty": {"运营": 2, "市场营销": 3, "UI/UX设计": 4, "项目经理": 2}
    },
    "AI工程师": {
        "related_jobs": ["机器学习工程师", "数据科学家", "算法工程师", "软件工程师"],
        "skill_overlap": {"机器学习工程师": 0.9, "数据科学家": 0.8, "算法工程师": 0.7, "软件工程师": 0.5},
        "transition_difficulty": {"机器学习工程师": 1, "数据科学家": 2, "算法工程师": 2, "软件工程师": 3}
    }
}

# 从Excel文件读取计算机相关岗位信息
def read_computer_jobs() -> List[Dict[str, Any]]:
    """
    从computer_related_jobs.xlsx文件读取计算机相关岗位信息
    """
    xlsx_path = ROOT / "computer_related_jobs.xlsx"
    if not xlsx_path.exists():
        return []
    
    try:
        import openpyxl
        wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return []
        headers = [str(h).strip() if h is not None else "" for h in rows[0]]
        jobs = []
        for row in rows[1:]:
            if any(v is not None for v in row):
                job_dict = dict(zip(headers, row))
                jobs.append(job_dict)
        return jobs
    except Exception as e:
        print(f"读取Excel文件失败: {e}")
        return []

# 联网搜索行业趋势信息
def search_industry_trends(industry: str) -> Optional[Dict[str, Any]]:
    """
    联网搜索行业趋势信息
    """
    try:
        # 使用百度搜索行业趋势
        query = f"{industry}行业趋势 2026"
        url = f"https://www.baidu.com/s?wd={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            # 提取搜索结果
            results = []
            for item in soup.select(".result.c-container")[:3]:
                title = item.select_one(".t a").text if item.select_one(".t a") else ""
                content = item.select_one(".c-abstract").text if item.select_one(".c-abstract") else ""
                if title and content:
                    results.append({"title": title, "content": content})
            return {"search_results": results}
    except Exception as e:
        print(f"搜索行业趋势失败: {e}")
    return None


def analyze_industry_trends(industry: str) -> Dict[str, Any]:
    """
    分析行业趋势
    
    Args:
        industry: 行业名称
    
    Returns:
        行业趋势分析结果
    """
    # 使用固定的计算机行业趋势数据
    trend_data = COMPUTER_INDUSTRY_TRENDS.get(industry, {
        "growth_rate": 7.0,
        "hot_jobs": ["软件工程师", "数据分析师", "产品经理"],
        "emerging_skills": ["人工智能", "云计算", "大数据"],
        "future_outlook": "计算机行业持续发展，数字化转型需求旺盛",
        "recruitment_trend": "技术岗需求稳定，薪资水平高于平均水平"
    })
    
    # 联网搜索行业趋势信息
    search_results = search_industry_trends(industry)
    
    # 生成趋势分析报告
    analysis = {
        "industry": industry,
        "growth_rate": trend_data["growth_rate"],
        "hot_jobs": trend_data["hot_jobs"],
        "emerging_skills": trend_data["emerging_skills"],
        "future_outlook": trend_data["future_outlook"],
        "recruitment_trend": trend_data["recruitment_trend"],
        "job_market_analysis": f"{industry}行业增长率为{trend_data['growth_rate']}%，热门岗位包括{', '.join(trend_data['hot_jobs'])}，新兴技能需求包括{', '.join(trend_data['emerging_skills'])}。",
        "recommendations": f"建议关注{', '.join(trend_data['emerging_skills'])}等新兴技能，以适应行业发展趋势。",
        "search_results": search_results
    }
    
    return analysis


def analyze_job_relations(job_title: str, user_skills: List[str]) -> Dict[str, Any]:
    """
    分析岗位关联性
    
    Args:
        job_title: 岗位名称
        user_skills: 用户技能列表
    
    Returns:
        岗位关联性分析结果
    """
    # 使用固定的计算机岗位关联性数据
    relation_data = COMPUTER_JOB_RELATIONS.get(job_title, {
        "related_jobs": [],
        "skill_overlap": {},
        "transition_difficulty": {}
    })
    
    # 分析用户技能与相关岗位的匹配度
    related_jobs_analysis = []
    for related_job in relation_data["related_jobs"]:
        # 计算技能匹配度
        skill_match = 0.0
        if user_skills:
            # 简单计算技能匹配度：用户技能与岗位技能的重叠度
            # 这里简化处理，实际应用中可以更复杂
            skill_match = min(1.0, len(user_skills) / 10.0)  # 假设需要10个技能
        else:
            skill_match = 0.5
        
        related_jobs_analysis.append({
            "job_title": related_job,
            "skill_overlap": relation_data["skill_overlap"].get(related_job, 0.5),
            "transition_difficulty": relation_data["transition_difficulty"].get(related_job, 3),
            "skill_match": round(skill_match, 2),
            "recommendation": f"从{job_title}转向{related_job}的难度为{relation_data['transition_difficulty'].get(related_job, 3)}/5，技能重叠度为{relation_data['skill_overlap'].get(related_job, 0.5)*100:.1f}%。"
        })
    
    # 按技能匹配度排序
    related_jobs_analysis.sort(key=lambda x: x["skill_match"], reverse=True)
    
    analysis = {
        "target_job": job_title,
        "related_jobs": related_jobs_analysis,
        "user_skills": user_skills,
        "summary": f"{job_title}的相关岗位包括{', '.join(relation_data['related_jobs'])}，其中技能匹配度最高的是{related_jobs_analysis[0]['job_title'] if related_jobs_analysis else '无'}。",
        "recommendations": "建议根据个人技能优势选择合适的职业发展路径，关注技能重叠度高、转型难度低的岗位。"
    }
    
    return analysis


def generate_trend_report(industry: str, job_title: str, user_skills: List[str]) -> str:
    """
    生成趋势分析报告
    
    Args:
        industry: 行业名称
        job_title: 岗位名称
        user_skills: 用户技能列表
    
    Returns:
        趋势分析报告
    """
    # 分析行业趋势
    industry_analysis = analyze_industry_trends(industry)
    
    # 分析岗位关联性
    job_analysis = analyze_job_relations(job_title, user_skills)
    
    # 生成报告
    lines = []
    lines.append("七、行业趋势与岗位关联性分析")
    lines.append("")
    
    # 行业趋势部分
    lines.append("1. 行业趋势分析")
    lines.append(f"- 行业：{industry_analysis['industry']}")
    lines.append(f"- 增长率：{industry_analysis['growth_rate']}%")
    lines.append(f"- 热门岗位：{', '.join(industry_analysis['hot_jobs'])}")
    lines.append(f"- 新兴技能：{', '.join(industry_analysis['emerging_skills'])}")
    lines.append(f"- 未来展望：{industry_analysis['future_outlook']}")
    lines.append(f"- 招聘趋势：{industry_analysis['recruitment_trend']}")
    lines.append(f"- 市场分析：{industry_analysis['job_market_analysis']}")
    lines.append(f"- 建议：{industry_analysis['recommendations']}")
    
    # 添加联网搜索结果
    if industry_analysis.get('search_results'):
        lines.append("")
        lines.append("- 最新行业动态：")
        for i, result in enumerate(industry_analysis['search_results'].get('search_results', [])[:2], start=1):
            lines.append(f"  {i}. {result.get('title')}")
            lines.append(f"     {result.get('content')[:100]}...")
    
    lines.append("")
    
    # 岗位关联性部分
    lines.append("2. 岗位关联性分析")
    lines.append(f"- 目标岗位：{job_analysis['target_job']}")
    lines.append(f"- 个人技能：{', '.join(job_analysis['user_skills']) if job_analysis['user_skills'] else '无'}")
    lines.append(f"- 分析总结：{job_analysis['summary']}")
    lines.append("")
    
    lines.append("- 相关岗位分析：")
    for i, related_job in enumerate(job_analysis['related_jobs'][:3], start=1):
        lines.append(f"  {i}. {related_job['job_title']}")
        lines.append(f"     - 技能重叠度：{related_job['skill_overlap']*100:.1f}%")
        lines.append(f"     - 转型难度：{related_job['transition_difficulty']}/5")
        lines.append(f"     - 技能匹配度：{related_job['skill_match']*100:.1f}%")
        lines.append(f"     - 建议：{related_job['recommendation']}")
    lines.append("")
    
    lines.append(f"- 关联性分析建议：{job_analysis['recommendations']}")
    
    return "\n".join(lines)

# 读取计算机相关岗位信息
computer_jobs = read_computer_jobs()
print(f"读取到 {len(computer_jobs)} 个计算机相关岗位")