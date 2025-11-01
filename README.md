# Personal Finance & Investment System (PFIS)

PFIS 是一个基于 **FastAPI + HTMX + Tailwind 风格样式** 的个人理财管理系统，可在本地运行，支持现金流管理、理财操作追踪、产品指标维护、模拟收益实验以及图形化分析。项目默认使用 SQLite 数据库，无需额外依赖。

## 🚀 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 初始化数据库（可选，首次启动会自动执行）
python -m app.db_init

# 启动服务
uvicorn app.main:app --reload --port 8000
```

访问 http://localhost:8000 即可打开仪表盘。

## 📁 项目结构

```
app/
├── main.py                # FastAPI 入口 & 路由注册
├── db_init.py             # 初始化数据库及主数据
├── database.py            # SQLAlchemy engine / Session 管理
├── models.py              # ORM 模型定义
├── schemas.py             # Pydantic 入参模型
├── crud.py                # 数据访问封装
├── routers/               # 功能模块路由
│   ├── analytics.py
│   ├── cash_flow.py
│   ├── investment_log.py
│   ├── master_data.py
│   ├── ocr_pending.py
│   ├── product_tracker.py
│   └── simulation_lab.py
├── templates/             # Jinja2 模板（支持 HTMX 局部刷新）
│   ├── base.html
│   ├── dashboard.html
│   ├── analytics.html
│   ├── simulation_lab.html
│   ├── master_data.html
│   ├── ocr_pending.html
│   ├── settings.html
│   ├── cash_flow/
│   │   ├── list.html
│   │   └── form.html
│   ├── investment_log/
│   │   ├── list.html
│   │   └── form.html
│   ├── product_tracker/
│   │   ├── list.html
│   │   └── detail.html
│   └── partials/
│       ├── simulation_result.html
│       ├── master_data_table.html
│       └── master_data_options.html
├── static/
│   ├── css/tailwind.css   # 精简 Tailwind 风格样式
│   ├── js/plotly.min.js   # Plotly 异步加载器
│   └── uploads/ocr_pending/  # OCR 上传占位目录
└── __init__.py

requirements.txt
```

## ✨ 主要功能

- **仪表盘概览**：展示总收入、支出、投资及现金结余；快速导航各模块。
- **收支记录**：通过 HTMX 动态加载表单及列表，支持上传凭证，自动登记 OCR 待处理。
- **理财操作**：记录买入/赎回等动作，可选择同步生成现金流。
- **产品追踪**：维护产品主档与指标，详情页使用 Plotly 展示收益曲线。
- **模拟实验室**：输入产品和金额，动态返回收益预测卡片，可继续发起买入。
- **分析中心**：聚合统计与月度净现金流柱状图。
- **主数据维护**：账户、类别、来源、产品维度等均可即时新增；可供其他表单通过 HTMX 刷新选项。
- **OCR 待处理**：展示所有上传凭证的占位信息，为后续识别功能打基础。

## 🛠️ 开发说明

- 所有数据存储于 `db/finance.db`，如需重置可删除文件后重新运行 `python -m app.db_init`。
- 模板中使用 HTMX (`hx-*` 属性) 完成局部刷新，同时集成 Hyperscript 提供未来扩展能力。
- Plotly 通过自定义脚本异步加载，模板使用 `window.PFISPlotlyReady` 注册绘图回调。
- 静态资源采用轻量化 Tailwind 风格工具类，可根据需求自行替换为完整 Tailwind 构建。

欢迎在此基础上扩展更多分析维度、自动化策略或接入真实 OCR 能力。祝使用愉快！
