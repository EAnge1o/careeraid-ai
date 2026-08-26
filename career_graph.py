# -*- coding: utf-8 -*-
"""
CareerAid 岗位关联图谱
---------------------------------
作用：
1. 根据岗位名称匹配岗位族（family）
2. 返回该岗位族的垂直晋升路径（vertical）
3. 返回该岗位族的横向换岗路径（lateral）及补充技能（lateral_skills）
4. 兼容原有接口：
   - get_graph_for_title(title)
   - build_echarts_data(title)
   - list_all_families()

设计原则：
- 优先覆盖 jobs_sample.csv 与 computer_related_jobs.xlsx 中的主流岗位
- 匹配时兼顾中文包含、英文边界匹配与精确岗位名匹配
- 避免 "pm" / "go" / "ai" 这类短词误匹配
"""

from __future__ import annotations

import re
from typing import Any

from cache import cache, get_cache_key


CAREER_GRAPH: list[dict[str, Any]] = [
    {
        "family": "Java后端开发",
        "description": "面向企业业务系统、后台服务、接口开发与系统架构演进的核心研发岗位族。",
        "aliases": [
            "java后端", "java开发", "java工程师", "后端开发", "spring boot", "springboot",
            "spring", "mybatis", "jvm", "redis", "后台开发"
        ],
        "exact_titles": [
            "Java后端开发工程师", "Java开发工程师", "Java开发实习生", "后端开发工程师"
        ],
        "vertical": [
            "Java开发实习生",
            "Java后端开发工程师",
            "高级Java开发工程师",
            "技术组长(TL)",
            "架构师/研发经理"
        ],
        "lateral": [
            "全栈开发工程师",
            "大数据开发工程师",
            "DevOps/SRE",
            "技术支持工程师"
        ],
        "lateral_skills": {
            "全栈开发工程师": [
                "前端基础(HTML/CSS/JavaScript)",
                "接口联调",
                "数据库设计",
                "工程化协作"
            ],
            "大数据开发工程师": [
                "Hadoop/Spark/Flink",
                "分布式计算",
                "数据仓库",
                "Kafka/ETL"
            ],
            "DevOps/SRE": [
                "Linux",
                "CI/CD",
                "Docker/Kubernetes",
                "监控与告警"
            ],
            "技术支持工程师": [
                "系统部署",
                "故障排查",
                "客户沟通",
                "文档输出"
            ]
        }
    },
    {
        "family": "前端开发",
        "description": "面向 Web 页面、管理后台、可视化系统与多端交互体验建设的岗位族。",
        "aliases": [
            "前端", "前端开发", "web前端", "frontend", "front-end",
            "react", "vue", "javascript", "typescript", "h5"
        ],
        "exact_titles": [
            "前端开发工程师"
        ],
        "vertical": [
            "前端开发实习生",
            "前端开发工程师",
            "资深前端开发工程师",
            "前端技术负责人",
            "前端架构师/技术专家"
        ],
        "lateral": [
            "全栈开发工程师",
            "移动端开发工程师",
            "UI/UX设计师",
            "产品经理"
        ],
        "lateral_skills": {
            "全栈开发工程师": [
                "Node.js/Python/Go 基础",
                "数据库设计",
                "API 设计",
                "服务端协同开发"
            ],
            "移动端开发工程师": [
                "React Native",
                "Flutter",
                "Kotlin/Swift",
                "移动端适配"
            ],
            "UI/UX设计师": [
                "Figma/Sketch",
                "交互设计",
                "用户体验分析",
                "视觉规范"
            ],
            "产品经理": [
                "需求分析",
                "原型设计",
                "跨部门协同",
                "产品迭代管理"
            ]
        }
    },
    {
        "family": "C/C++开发",
        "description": "面向底层模块、客户端、工业软件、嵌入式与高性能程序开发的岗位族。",
        "aliases": [
            "c/c++", "c++", "cpp", "c开发", "c++开发",
            "qt", "嵌入式", "底层开发", "客户端开发", "linux c"
        ],
        "exact_titles": [
            "C/C++开发工程师"
        ],
        "vertical": [
            "C/C++开发实习生",
            "C/C++开发工程师",
            "高级C/C++开发工程师",
            "底层技术负责人",
            "系统架构师"
        ],
        "lateral": [
            "嵌入式开发工程师",
            "硬件测试工程师",
            "算法工程师",
            "客户端开发工程师"
        ],
        "lateral_skills": {
            "嵌入式开发工程师": [
                "单片机/ARM",
                "驱动开发",
                "接口协议",
                "板级调试"
            ],
            "硬件测试工程师": [
                "示波器/频谱仪",
                "可靠性测试",
                "板卡联调",
                "测试报告"
            ],
            "算法工程师": [
                "数据结构与算法",
                "数学基础",
                "性能优化",
                "工程实现能力"
            ],
            "客户端开发工程师": [
                "Qt/GUI",
                "多线程",
                "内存管理",
                "跨平台开发"
            ]
        }
    },
    {
        "family": "测试岗位",
        "description": "覆盖功能测试、自动化测试、质量保障与测试开发等质量类岗位。",
        "aliases": [
            "测试", "软件测试", "自动化测试", "qa", "qc", "testing", "test",
            "selenium", "playwright", "appium", "set"
        ],
        "exact_titles": [
            "软件测试工程师", "自动化测试工程师", "测试开发工程师"
        ],
        "vertical": [
            "测试实习生",
            "软件测试工程师",
            "高级测试工程师",
            "测试经理",
            "质量保证(QA)负责人"
        ],
        "lateral": [
            "自动化测试工程师",
            "测试开发工程师(SET)",
            "产品经理",
            "技术支持工程师"
        ],
        "lateral_skills": {
            "自动化测试工程师": [
                "Python/Java",
                "Selenium/Playwright/Appium",
                "接口自动化",
                "持续集成"
            ],
            "测试开发工程师(SET)": [
                "测试框架设计",
                "脚本平台化",
                "CI/CD",
                "质量门禁建设"
            ],
            "产品经理": [
                "需求分析",
                "用户逻辑",
                "缺陷与体验洞察",
                "迭代推进"
            ],
            "技术支持工程师": [
                "故障复现",
                "问题定位",
                "客户沟通",
                "知识库整理"
            ]
        }
    },
    {
        "family": "硬件测试",
        "description": "围绕板卡、接口、设备可靠性、实验验证与电子测试流程的岗位族。",
        "aliases": [
            "硬件测试", "板卡测试", "可靠性测试", "仪器测试",
            "示波器", "频谱仪", "万用表"
        ],
        "exact_titles": [
            "硬件测试工程师"
        ],
        "vertical": [
            "硬件测试实习生",
            "硬件测试工程师",
            "高级硬件测试工程师",
            "硬件测试负责人",
            "质量/验证经理"
        ],
        "lateral": [
            "硬件研发工程师",
            "嵌入式开发工程师",
            "软件测试工程师",
            "技术支持工程师"
        ],
        "lateral_skills": {
            "硬件研发工程师": [
                "电路基础",
                "器件选型",
                "板级设计理解",
                "联调分析"
            ],
            "嵌入式开发工程师": [
                "MCU/ARM",
                "驱动调试",
                "串口/CAN/I2C/SPI",
                "硬软协同"
            ],
            "软件测试工程师": [
                "测试流程",
                "缺陷管理",
                "质量意识",
                "文档输出"
            ],
            "技术支持工程师": [
                "设备部署",
                "现场问题排查",
                "客户培训",
                "技术文档"
            ]
        }
    },
    {
        "family": "实施与技术支持",
        "description": "面向客户交付、系统部署、培训、驻场支持与售后问题处理的交付型岗位族。",
        "aliases": [
            "实施工程师", "技术支持", "售后支持", "运维支持", "helpdesk",
            "部署", "驻场", "客户支持", "项目实施"
        ],
        "exact_titles": [
            "实施工程师", "实施工程师（实习）", "技术支持工程师"
        ],
        "vertical": [
            "实施/支持实习生",
            "实施工程师",
            "高级实施/技术支持工程师",
            "项目经理",
            "交付负责人/解决方案经理"
        ],
        "lateral": [
            "技术支持工程师",
            "信息化项目助理",
            "解决方案顾问",
            "产品经理"
        ],
        "lateral_skills": {
            "技术支持工程师": [
                "故障定位",
                "数据库/网络基础",
                "培训表达",
                "问题闭环"
            ],
            "信息化项目助理": [
                "进度跟踪",
                "需求整理",
                "会议纪要",
                "跨部门协调"
            ],
            "解决方案顾问": [
                "方案讲解",
                "客户需求分析",
                "售前支持",
                "行业理解"
            ],
            "产品经理": [
                "需求抽象",
                "流程设计",
                "客户场景理解",
                "协同推进"
            ]
        }
    },
    {
        "family": "AI科研与算法",
        "description": "面向机器学习、深度学习、论文复现、模型训练与科研转化的算法类岗位族。",
        "aliases": [
            "ai", "算法", "算法工程师", "科研工程师", "机器学习", "深度学习",
            "nlp", "cv", "推荐", "大模型", "llm", "pytorch", "tensorflow"
        ],
        "exact_titles": [
            "AI科研工程师", "算法工程师", "机器学习工程师"
        ],
        "vertical": [
            "算法/科研实习生",
            "AI科研工程师",
            "高级算法工程师",
            "算法负责人/实验室骨干",
            "首席科学家/研究负责人"
        ],
        "lateral": [
            "机器学习工程师",
            "数据分析师",
            "大数据开发工程师",
            "技术顾问"
        ],
        "lateral_skills": {
            "机器学习工程师": [
                "模型工程化部署",
                "特征工程",
                "训练/推理优化",
                "Python/C++"
            ],
            "数据分析师": [
                "SQL",
                "统计分析",
                "可视化",
                "业务解释能力"
            ],
            "大数据开发工程师": [
                "Spark/Flink",
                "ETL",
                "数据管道",
                "分布式系统"
            ],
            "技术顾问": [
                "技术汇报",
                "行业理解",
                "方案输出",
                "成果转化"
            ]
        }
    },
    {
        "family": "信息化项目管理",
        "description": "面向项目推进、文档输出、需求整理、招投标支持与组织协调的项目类岗位族。",
        "aliases": [
            "项目助理", "信息化项目助理", "项目管理", "pmo",
            "需求整理", "项目实施支持", "招投标"
        ],
        "exact_titles": [
            "信息化项目助理"
        ],
        "vertical": [
            "项目助理/PMO实习生",
            "信息化项目助理",
            "项目专员",
            "项目经理",
            "项目总监/交付负责人"
        ],
        "lateral": [
            "实施工程师",
            "产品经理",
            "商务/招投标专员",
            "解决方案顾问"
        ],
        "lateral_skills": {
            "实施工程师": [
                "系统部署",
                "项目交付",
                "客户培训",
                "现场支持"
            ],
            "产品经理": [
                "需求分析",
                "流程设计",
                "跨团队协同",
                "里程碑管理"
            ],
            "商务/招投标专员": [
                "标书编写",
                "商务沟通",
                "流程合规",
                "文档规范"
            ],
            "解决方案顾问": [
                "方案包装",
                "客户交流",
                "售前支持",
                "行业场景理解"
            ]
        }
    },
    {
        "family": "通用岗位",
        "description": "未匹配到明确岗位族时的通用职业路径，用于兜底展示。",
        "aliases": [],
        "exact_titles": [],
        "vertical": [
            "实习生",
            "初级工程师/专员",
            "中级工程师/专员",
            "高级工程师/主管",
            "负责人/经理"
        ],
        "lateral": [
            "项目管理",
            "产品经理",
            "数据分析师"
        ],
        "lateral_skills": {
            "项目管理": ["进度管理", "沟通协调", "文档输出"],
            "产品经理": ["需求分析", "方案设计", "跨部门协同"],
            "数据分析师": ["SQL", "数据分析", "可视化表达"]
        }
    }
]


def _normalize_text(text: str | None) -> str:
    text = (text or "").strip().lower()
    text = text.replace("（", "(").replace("）", ")")
    text = re.sub(r"\s+", "", text)
    return text


def _keyword_match_score(text: str, keyword: str) -> int:
    """
    返回单个关键词的匹配得分：
    - 精确子串匹配（中文 / 长英文词）：2
    - 英文短词边界匹配：2
    - 未命中：0
    """
    if not keyword:
        return 0

    kw = _normalize_text(keyword)
    if not kw:
        return 0

    # 中文或混合长词，直接做包含判断
    if re.search(r"[\u4e00-\u9fff]", kw) or len(kw) >= 4:
        return 2 if kw in text else 0

    # 对于 ai / pm / go / qa / ui 等短英文，使用单词边界匹配，避免误判
    raw_text = text
    pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
    return 2 if re.search(pattern, raw_text, flags=re.IGNORECASE) else 0


def _title_match_score(title: str, graph: dict[str, Any]) -> int:
    """
    综合 exact_titles / aliases / vertical / lateral 的命中情况计算分数。
    分数越高，说明岗位族越匹配。
    """
    score = 0
    normalized_title = _normalize_text(title)

    # 1) 精确岗位名优先
    for name in graph.get("exact_titles", []):
        if _normalize_text(name) in normalized_title:
            score += 6

    # 2) 别名匹配
    for alias in graph.get("aliases", []):
        score += _keyword_match_score(normalized_title, alias)

    # 3) 垂直路径岗位名
    for name in graph.get("vertical", []):
        if _normalize_text(name) in normalized_title:
            score += 4

    # 4) 横向路径岗位名
    for name in graph.get("lateral", []):
        if _normalize_text(name) in normalized_title:
            score += 3

    return score


def get_graph_for_title(title: str | None) -> dict[str, Any]:
    """
    根据岗位名称匹配岗位族，返回该族的垂直路径 + 横向路径 + 核心技能。
    若未匹配到，则返回“通用岗位”。
    """
    if not title:
        return CAREER_GRAPH[-1]

    best_graph = CAREER_GRAPH[-1]
    best_score = 0

    for graph in CAREER_GRAPH[:-1]:  # 最后一项为通用兜底
        score = _title_match_score(title, graph)
        if score > best_score:
            best_graph = graph
            best_score = score

    return best_graph


def build_echarts_data(title: str | None) -> dict[str, Any]:
    """
    返回 ECharts graph 所需的 nodes + links。
    节点分类：
    - category 0: 垂直晋升路径
    - category 1: 横向换岗路径
    """
    # 生成缓存键
    cache_key = get_cache_key("career_graph", title or "")
    
    # 尝试从缓存获取
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    graph = get_graph_for_title(title)
    vertical = graph["vertical"]
    lateral = graph["lateral"][:5]
    lateral_skills = graph.get("lateral_skills", {})

    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []

    # 垂直路径节点
    for idx, name in enumerate(vertical):
        nodes.append({
            "id": name,
            "name": name,
            "category": 0,
            "symbolSize": 46 if idx == 0 else 40,
            "value": {
                "type": "vertical",
                "family": graph["family"],
                "description": graph.get("description", "")
            }
        })

    # 横向换岗节点
    for name in lateral:
        nodes.append({
            "id": name,
            "name": name,
            "category": 1,
            "symbolSize": 38,
            "value": {
                "type": "lateral",
                "family": graph["family"],
                "core_skills": lateral_skills.get(name, [])
            }
        })

    # 垂直路径连线
    for idx in range(len(vertical) - 1):
        links.append({
            "source": vertical[idx],
            "target": vertical[idx + 1]
        })

    # 横向路径从第二个阶段岗位发散
    pivot = vertical[min(1, len(vertical) - 1)] if vertical else ""
    for name in lateral:
        links.append({
            "source": pivot,
            "target": name,
            "lineStyle": {"type": "dashed"}
        })

    result = {
        "family": graph["family"],
        "description": graph.get("description", ""),
        "vertical": vertical,
        "lateral": lateral,
        "lateral_skills": {name: lateral_skills.get(name, []) for name in lateral},
        "nodes": nodes,
        "links": links,
    }
    
    # 缓存结果
    cache.set(cache_key, result)
    
    return result


def list_all_families() -> list[dict[str, Any]]:
    """返回全部岗位族，供前端筛选、调试或管理页面展示。"""
    result = []
    for graph in CAREER_GRAPH:
        lateral = graph.get("lateral", [])[:5]
        result.append({
            "family": graph["family"],
            "description": graph.get("description", ""),
            "aliases": graph.get("aliases", []),
            "exact_titles": graph.get("exact_titles", []),
            "vertical": graph.get("vertical", []),
            "lateral": lateral,
            "lateral_count": len(lateral),
            "lateral_skills": {
                name: graph.get("lateral_skills", {}).get(name, []) for name in lateral
            }
        })
    return result


def build_dynamic_echarts_data(title: str | None, student_skills: list[str] = None, interests: list[str] = None) -> dict[str, Any]:
    """
    生成动态职业图谱，根据用户技能和兴趣调整节点和连接
    
    Args:
        title: 岗位名称
        student_skills: 学生技能列表
        interests: 学生兴趣列表
    
    Returns:
        包含nodes和links的ECharts数据
    """
    student_skills = student_skills or []
    interests = interests or []
    
    # 生成缓存键
    cache_key = get_cache_key("dynamic_career_graph", title or "", ",".join(sorted(student_skills)), ",".join(sorted(interests)))
    
    # 尝试从缓存获取
    cached_data = cache.get(cache_key)
    if cached_data:
        return cached_data
    
    # 获取基础图谱
    graph = get_graph_for_title(title)
    vertical = graph["vertical"]
    lateral = graph["lateral"][:5]
    lateral_skills = graph.get("lateral_skills", {})
    
    nodes: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    
    # 计算技能匹配度
    def calculate_skill_match(job_skills: list[str]) -> float:
        if not job_skills or not student_skills:
            return 0.0
        matched = set(student_skills) & set(job_skills)
        return len(matched) / len(job_skills)
    
    # 计算兴趣匹配度
    def calculate_interest_match(job_title: str) -> float:
        if not interests:
            return 0.0
        job_lower = job_title.lower()
        match_count = sum(1 for interest in interests if interest.lower() in job_lower)
        return match_count / len(interests)
    
    # 垂直路径节点
    for idx, name in enumerate(vertical):
        # 计算匹配度
        skill_match = 0.0
        interest_match = calculate_interest_match(name)
        
        # 调整节点大小和颜色
        symbol_size = 46 if idx == 0 else 40
        if skill_match > 0.5 or interest_match > 0.5:
            symbol_size += 5
        
        nodes.append({
            "id": name,
            "name": name,
            "category": 0,
            "symbolSize": symbol_size,
            "value": {
                "type": "vertical",
                "family": graph["family"],
                "description": graph.get("description", ""),
                "skill_match": round(skill_match, 2),
                "interest_match": round(interest_match, 2)
            }
        })
    
    # 横向换岗节点
    for name in lateral:
        # 计算技能匹配度
        job_skills = lateral_skills.get(name, [])
        skill_match = calculate_skill_match(job_skills)
        interest_match = calculate_interest_match(name)
        
        # 调整节点大小和颜色
        symbol_size = 38
        if skill_match > 0.5 or interest_match > 0.5:
            symbol_size += 5
        
        nodes.append({
            "id": name,
            "name": name,
            "category": 1,
            "symbolSize": symbol_size,
            "value": {
                "type": "lateral",
                "family": graph["family"],
                "core_skills": job_skills,
                "skill_match": round(skill_match, 2),
                "interest_match": round(interest_match, 2)
            }
        })
    
    # 垂直路径连线
    for idx in range(len(vertical) - 1):
        links.append({
            "source": vertical[idx],
            "target": vertical[idx + 1]
        })
    
    # 横向路径从第二个阶段岗位发散
    pivot = vertical[min(1, len(vertical) - 1)] if vertical else ""
    for name in lateral:
        # 计算匹配度，调整连线样式
        job_skills = lateral_skills.get(name, [])
        skill_match = calculate_skill_match(job_skills)
        interest_match = calculate_interest_match(name)
        
        # 根据匹配度调整连线粗细
        line_width = 1
        if skill_match > 0.3 or interest_match > 0.3:
            line_width = 2
        if skill_match > 0.6 or interest_match > 0.6:
            line_width = 3
        
        links.append({
            "source": pivot,
            "target": name,
            "lineStyle": {
                "type": "dashed",
                "width": line_width
            }
        })
    
    result = {
        "family": graph["family"],
        "description": graph.get("description", ""),
        "vertical": vertical,
        "lateral": lateral,
        "lateral_skills": {name: lateral_skills.get(name, []) for name in lateral},
        "nodes": nodes,
        "links": links,
        "student_skills": student_skills,
        "interests": interests
    }
    
    # 缓存结果
    cache.set(cache_key, result)
    
    return result