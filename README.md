# 智业AI职业规划助手（CareerAid AI）

> 一个基于 AI 的大学生职业规划 Web 应用：**简历解析 → 能力画像 → 人岗匹配 → 职业发展报告 → 提升计划** 全流程闭环。
> 后端 Flask + SQLite，前端原生 HTML/CSS/JS（无框架），AI 能力采用"大模型优先 + 离线规则兜底"的双引擎设计，未配置任何 API Key 也能完整运行。

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-local-003B57?logo=sqlite&logoColor=white)](https://sqlite.org)
[![Frontend](https://img.shields.io/badge/HTML%2FCSS%2FJS-native-E34F26?logo=html5&logoColor=white)](#)
[![Docs](https://img.shields.io/badge/docs-ALGORITHM%20%26%20PROMPTS-brightgreen)](docs/ALGORITHM.md)

## 🏆 竞赛答辩定位

- **不是 Demo**：登录、简历解析、人岗匹配、报告导出、管理员后台形成可运行的完整业务闭环。
- **算法可解释**：四维加权匹配 + 技能 Jaccard 重合度 + 可选 RandomForest 回归增强，详细推导见 [docs/ALGORITHM.md](docs/ALGORITHM.md)。
- **工程可降级**：大模型不可用时自动切换离线规则引擎，保证演示现场不因 API Key 或网络问题翻车。
- **开箱可展示**：数据库首次启动自动建表并写入 12 个演示岗位，无需手动导入即可走通全流程。

## ✨ 功能亮点

| 模块 | 说明 |
|---|---|
| **简历解析** | 上传 `.docx` / `.pdf` 或手动录入，抽取 10 维就业能力画像（专业技能、沟通能力、抗压能力…）+ 完整度/竞争力评分 |
| **人岗匹配** | 从**基础要求、职业技能、职业素养、发展潜力** 4 维度加权分析，技能重合度 + 差距分析 + 提升建议；可选 scikit-learn 模型增强 |
| **岗位关联图谱** | 垂直晋升 + 横向换岗路径可视化（ECharts），5+ 岗位族 |
| **职业发展报告** | 一键生成 → 在线编辑 → 完整性检查 → **TXT / Word / PDF 三种格式导出** + 历史报告随时再下载 |
| **AI 对话** | 基于简历与性格测评的上下文问答，记忆关键事实 |
| **用户系统** | 注册/登录（PBKDF2 加盐哈希）、7 天会话、修改密码、退出登录、**管理员后台**（用户管理/岗位管理/统计图表） |
| **性格测评** | 大五人格 + 职业兴趣 + 可利用资源，映射岗位适配与短板诊断 |

## 🛠 技术栈

- **后端**：Python · Flask · Flask-SQLAlchemy · SQLite
- **前端**：原生 HTML/CSS/JS（Neo-Brutalism 蓝白主题）· ECharts（本地化，无 CDN 依赖）
- **AI 接入**：多 Provider 适配（火山引擎/豆包、OpenAI 兼容、讯飞星火），未配置自动回退离线规则
- **文档处理**：python-docx · pdfplumber · reportlab（中文字体自动探测）
- **可选 ML**：scikit-learn（人岗匹配回归增强模型，含训练脚本）

## 🚀 快速开始

环境要求：Python 3.10+

```bash
git clone <你的仓库地址>
cd <项目目录>
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

# 国内网络如安装失败，可加镜像：-i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.txt

python app.py
```

浏览器打开 **http://127.0.0.1:5000/** 即可使用。

测试账号：`admin` / `123456`（首次登录后请在「管理员后台 → 修改密码」中更改，初始密码可用环境变量 `ADMIN_INIT_PASSWORD` 覆盖）

> 数据库 `careeraid.db` 启动时自动创建；岗位数据为空时会自动写入 12 个演示岗位，无需手动导入。

## 📸 界面预览

建议启动服务后截取以下四个核心页面，保存到 `docs/screenshots/`，再替换为真实图片链接：

| 页面 | 建议截图内容 |
|---|---|
| 首页 | 能力画像雷达图与推荐岗位入口 |
| 人岗匹配 | 四维匹配得分、技能重合度与差距分析 |
| 报告导出 | 职业发展报告在线编辑页或 PDF 导出结果 |
| 管理员后台 | 用户 / 岗位管理与统计图表 |

```markdown
![首页](docs/screenshots/home.png)
![人岗匹配](docs/screenshots/match.png)
![报告导出](docs/screenshots/report.png)
![管理员后台](docs/screenshots/admin.png)
```

## 📁 项目结构

```
├── app.py                 # Flask 入口
├── routes.py              # API 路由（认证/简历/测评/匹配/报告/聊天/管理员）
├── ai_client.py           # 大模型客户端（火山/OpenAI兼容/星火，多 Provider）
├── ai_helper.py           # 简历解析/岗位画像/匹配/报告（LLM 优先 + 离线兜底）
├── career_graph.py        # 岗位关联图谱数据
├── trend_analysis.py      # 行业趋势分析
├── game_theory.py         # 博弈论遗憾匹配（职业决策）
├── models.py              # ORM 模型
├── database.py / cache.py / context_memory.py / knowledge.py
├── *.html                 # 12 个前端页面（首页/登录/注册/简历/测评/匹配/报告/计划/图谱/分析/后台/对话）
├── static/                # style.css / app.js / echarts.min.js / favicon.svg
├── docs/
│   ├── ALGORITHM.md       # 匹配算法详解
│   └── PROMPTS.md         # AI Prompt 设计
├── scripts/               # 企业岗位数据导入脚本（XLS/XLSX/CSV）
├── ml/                    # 可选的人岗匹配模型训练
└── requirements*.txt      # 基础 / ML / OCR 三份依赖清单
```

## 🧠 核心算法（可重点讲）

1. **简历解析**：正则规则抽取（技能/证书/项目/教育）+ 经验公式打分生成 10 维画像；大模型可用时由其直接输出结构化 JSON。
2. **人岗匹配**：四维加权（基础要求 40% / 职业技能 30% / 职业素养 20% / 发展潜力 10%）+ 技能 Jaccard 重合度 + 项目/教育相关性，输出匹配分与差距建议；`MLMatchEnhancer` 可用历史匹配数据训练 RandomForest 回归增强。
3. **报告生成**：结构化章节模板 + 完整性检查（缺失章节提示），支持 TXT/Word/PDF 导出。
4. **博弈论**：职业选择场景使用遗憾匹配算法辅助决策。

详细说明见 [docs/ALGORITHM.md](docs/ALGORITHM.md)。

## ⚙️ 配置大模型（可选，不配也能跑）

复制 `.env.example` 为 `.env` 后填写：

| Provider | 环境变量 | 说明 |
|---|---|---|
| 火山引擎/豆包 | `AI_PROVIDER=volc` + `VOLC_BASE_URL` / `VOLC_API_KEY` / `VOLC_MODEL` | 推荐 |
| OpenAI 兼容 | `AI_PROVIDER=openai_compatible` + `OPENAI_BASE_URL` / `OPENAI_API_KEY` / `OPENAI_MODEL` | 可接任意兼容服务 |
| 讯飞星火 | `AI_PROVIDER=spark` + `SPARK_*` | 按官方文档补齐鉴权 |

未配置时自动以 `offline` 模式运行，功能完整可用。

## 🧪 测试

```bash
# 启动服务后，运行接口冒烟测试（登录 + 人岗匹配）
python test_api.py
```

## 📄 说明

- 本项目为个人学习/作品展示项目，岗位数据为演示用途，可替换为企业真实数据（`scripts/` 提供导入脚本）。
- 如需商用部署，请替换 `SECRET_KEY`、修改管理员初始密码并关闭 `debug=True`。
