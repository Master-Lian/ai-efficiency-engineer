# 医院病床可视化大屏（Flask + ECharts）

## 功能说明

本项目用于展示病床运营核心指标，覆盖以下需求：

1. 占用率：各医院及科室病床使用率表图
2. 空闲病床数：实时显示空闲病床数量及分布
3. 病床分布图：不同科室和区域的病床分布情况

> 说明：页面不使用地图，总图表数量控制为 4 个（满足不超过 5 个的要求）。

## 图标建议（控制为 4 个）

建议使用 Font Awesome，图标统一风格、视觉清晰：

1. `fa-bed`：病床总数
2. `fa-user-injured`：已占用病床
3. `fa-bed-pulse`：空闲病床
4. `fa-chart-line`：整体占用率

## 大屏呈现布局

大屏采用「顶部指标卡 + 主体表图」结构：

- 顶部（第一行）：4 个指标卡（图标 + 核心数字）
- 主体左侧：各医院占用率表（占两行）
- 主体右侧上方：
  - 各医院病床使用率柱状图
  - 空闲病床医院分布环形图
- 主体右侧下方：
  - 科室病床占用与空闲堆叠柱图
  - 区域病床分布横向柱图

## 目录结构

```text
hospital_bed_dashboard/
├─ app.py
├─ requirements.txt
├─ templates/
│  └─ index.html
└─ static/
   ├─ css/
   │  └─ dashboard.css
   └─ js/
      └─ dashboard.js
```

## 启动方式

```bash
cd ai-parse/hospital_bed_dashboard
pip install -r requirements.txt
python app.py
```

启动后访问：`http://127.0.0.1:5000`

## 行业规范说明

- 前后端分层：`Flask API` 与 `ECharts 渲染`解耦
- 数据聚合独立函数，便于替换为数据库或实时接口
- 命名清晰、结构可扩展，便于后续新增指标（如周转率、平均住院日）
