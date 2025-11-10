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
│   ├── cash_flow.py
│   ├── dashboard.py
│   ├── data_tools.py
│   ├── investment_log.py
│   ├── master_data.py
│   ├── ocr_pending.py
│   ├── product_tracker/
│   │   ├── __init__.py
│   │   ├── products.py
│   │   └── metrics.py
│   └── simulation_lab.py
├── templates/             # Jinja2 模板（支持 HTMX 局部刷新）
│   ├── base.html
│   ├── dashboard.html
│   ├── simulation_lab.html
│   ├── ocr_pending.html
│   ├── cash_flow/
│   │   ├── index.html
│   │   ├── list.html
│   │   └── row.html
│   ├── investment_log/
│   │   ├── index.html
│   │   └── table.html
│   ├── product_tracker/
│   │   ├── products/
│   │   │   ├── index.html
│   │   │   ├── form.html
│   │   │   └── table.html
│   │   └── metrics/
│   │       ├── index.html
│   │       ├── form.html
│   │       └── table.html
│   ├── master_data/
│   │   ├── index.html
│   │   ├── list.html
│   │   └── row.html
│   └── partials/            # 共享弹窗、行模板、导入导出等片段
├── static/
│   └── css/tailwind.css   # 精简 Tailwind 风格样式
└── __init__.py

requirements.txt
```

## ✨ 主要功能

- **仪表盘概览**：展示总收入、支出、投资及现金结余；双图对比月度收支与净现金流；快速导航各模块。
- **收支记录**：HTMX 异步加载表单与表格，支持逻辑删除，自动标记状态。
- **理财操作**：记录买入/赎回等动作，与账户维度联动并支持逻辑删除。
- **产品追踪**：分离产品主数据与指标模块，Plotly 展示指标趋势并提供 JSON 数据接口。
- **模拟实验室**：输入产品和金额，动态返回收益预测卡片，可继续发起买入。
- **主数据维护**：账户、类别、来源、指标等维度即时新增，逻辑删除前自动提示影响。
- **数据导入/导出**：仪表盘提供 Excel 备份与恢复工具，支持全量重建或增量导入模式。
- **OCR 待处理**：展示所有上传凭证的占位信息，为后续识别功能打基础。

## 🛠️ 开发说明

- 所有数据存储于 `db/finance.db`，如需重置可删除文件后重新运行 `python -m app.db_init`。
- 模板中使用 HTMX (`hx-*` 属性) 完成局部刷新，同时集成 Hyperscript 提供未来扩展能力。
- Plotly 通过自定义脚本异步加载，模板使用 `window.PFISPlotlyReady` 注册绘图回调。
- 静态资源采用轻量化 Tailwind 风格工具类，可根据需求自行替换为完整 Tailwind 构建。

欢迎在此基础上扩展更多分析维度、自动化策略或接入真实 OCR 能力。祝使用愉快！
