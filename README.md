# Personal Finance & Investment System (PFIS)

本仓库提供一个可本地运行的 Python + Streamlit 原型应用，实现个人理财与投资管理功能。项目基于 SQLite 存储数据，支持现金流记录、理财操作追踪、主数据维护、模拟分析以及 OCR 截图上传预留。

## 📁 项目结构

```
finance_app/
├── app.py                # Streamlit 主入口
├── db_init.py            # 数据库初始化脚本
├── db/
│   └── finance.db        # SQLite 数据库（执行初始化脚本后生成）
├── modules/              # 功能模块
│   ├── cash_flow.py      # 收支记录
│   ├── investment_log.py # 理财操作
│   ├── product_tracker.py# 理财产品追踪
│   ├── simulation_lab.py # 模拟分析
│   ├── analytics.py      # 分析中心
│   ├── master_data.py    # 主数据维护
│   └── ocr_pending.py    # OCR 预留
├── pending_ocr/          # OCR 截图存储目录
│   ├── cashflow/
│   ├── investment/
│   └── products/
├── static/
│   └── style.css         # 自定义样式
└── data/
    └── sample_import.csv # 示例 CSV
```

## 🚀 快速开始

1. 安装依赖：

   ```bash
   pip install streamlit pandas plotly numpy
   ```

2. 初始化数据库：

   ```bash
   cd finance_app
   python db_init.py
   ```

3. 运行应用：

   ```bash
   streamlit run app.py
   ```

4. 在浏览器访问 `http://localhost:8501`，根据左侧导航使用各功能模块。

## 🧩 关键特性

- **主数据维护**：集中管理账户、分类、产品类型、风险等级等标准项，业务模块内支持“＋新增”快速写入。
- **收支与理财联动**：理财操作可自动生成对应现金流，分析中心提供月度一致性校验提示。
- **产品 1:N 指标**：理财产品主档配合时序指标记录，支持收益曲线可视化。
- **模拟分析实验室**：基于历史指标估算预期收益与风险，确认后可直接生成买入操作并更新持仓。
- **OCR 上传预留**：收支、理财、产品模块均提供截图上传，文件保存在 `pending_ocr/` 并记录至 `ocr_pending` 表，为未来识别功能留好接口。
- **全离线运行**：所有数据均存储在本地 SQLite 数据库，无外部网络依赖。

## 📦 数据导入导出

- 各模块支持 CSV 数据导入（示例参见 `data/sample_import.csv`）。
- 分析中心提供多表导出功能，一键生成 CSV 备份。

## 📚 开发说明

- 模块化设计，`modules/` 目录中的文件可独立扩展或替换。
- 若需重置数据库，可在应用侧边栏进入“系统设置”，点击“重新初始化数据库”按钮。
- OCR 功能目前仅保存截图，后续可在 `ocr_pending` 表基础上实现自动识别与填表。

欢迎在此基础上继续扩展投资策略、自动化分析等高级能力。
