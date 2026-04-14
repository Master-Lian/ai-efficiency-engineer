from pathlib import Path
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    base_dir = Path(__file__).resolve().parent
    basic_path = base_dir / "员工基本信息表.xlsx"
    perf_path = base_dir / "员工绩效表.xlsx"

    basic_df = pd.read_excel(basic_path).copy()
    perf_df = pd.read_excel(perf_path).copy()
    basic_df["入职时间"] = pd.to_datetime(basic_df["入职时间"])
    return basic_df, perf_df


def apply_screen_style() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background: radial-gradient(circle at top, #0b2447 0%, #06122b 45%, #030712 100%);
            color: #e6f1ff;
        }
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 1rem;
            max-width: 98%;
        }
        .kpi-card {
            background: rgba(17, 25, 40, 0.68);
            border: 1px solid rgba(112, 182, 255, 0.28);
            border-radius: 14px;
            padding: 12px 14px;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25);
        }
        .kpi-title {
            font-size: 13px;
            color: #9ecbff;
            margin-bottom: 6px;
        }
        .kpi-value {
            font-size: 28px;
            font-weight: 700;
            color: #ffffff;
            line-height: 1.2;
        }
        .header-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.6rem;
        }
        .screen-title {
            font-size: 34px;
            font-weight: 800;
            letter-spacing: 1px;
            color: #dbeafe;
        }
        .screen-time {
            font-size: 18px;
            color: #93c5fd;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(title: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-title">{title}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def build_dashboard() -> None:
    st.set_page_config(page_title="员工指标可视化大屏", layout="wide")
    apply_screen_style()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.markdown(
        f"""
        <div class="header-row">
            <div class="screen-title">员工指标可视化大屏</div>
            <div class="screen-time">数据时间：{now_str}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    basic_df, perf_df = load_data()

    st.sidebar.header("筛选条件")
    all_depts = sorted(basic_df["部门"].dropna().unique().tolist())
    selected_depts = st.sidebar.multiselect("选择部门", all_depts, default=all_depts)
    year_options = sorted(perf_df["年度"].dropna().unique().tolist())
    selected_year = st.sidebar.selectbox("选择年份", year_options, index=len(year_options) - 1)

    perf_year = perf_df[perf_df["年度"] == selected_year]
    quarter_options = sorted(perf_year["季度"].dropna().unique().tolist())
    selected_quarter = st.sidebar.selectbox("选择季度", quarter_options, index=len(quarter_options) - 1)

    basic_filtered = basic_df[basic_df["部门"].isin(selected_depts)].copy()
    perf_filtered = perf_df[perf_df["员工ID"].isin(basic_filtered["员工ID"])].copy()

    latest_perf = perf_filtered[
        (perf_filtered["年度"] == selected_year) & (perf_filtered["季度"] == selected_quarter)
    ].copy()
    merged_latest = pd.merge(basic_filtered, latest_perf, on="员工ID", how="left")

    total_employees = int(basic_filtered["员工ID"].nunique())
    total_departments = int(basic_filtered["部门"].nunique())
    avg_latest_perf = float(latest_perf["绩效评分"].mean()) if not latest_perf.empty else 0.0
    female_ratio = (
        float((basic_filtered["性别"] == "女").mean()) * 100 if not basic_filtered.empty else 0.0
    )
    high_perf_count = int((latest_perf["绩效评分"] >= 4.5).sum()) if not latest_perf.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("员工总数", f"{total_employees}")
    with c2:
        kpi_card("部门数量", f"{total_departments}")
    with c3:
        kpi_card(f"{selected_year}Q{selected_quarter}平均绩效", f"{avg_latest_perf:.2f}")
    with c4:
        kpi_card("高绩效人数 (>=4.5)", f"{high_perf_count}")

    c5, c6 = st.columns(2)
    with c5:
        kpi_card("女性员工占比", f"{female_ratio:.1f}%")
    with c6:
        kpi_card(
            "数据覆盖季度数",
            f"{perf_filtered[['年度', '季度']].drop_duplicates().shape[0]}",
        )

    left_col, right_col = st.columns(2)

    dept_count = (
        basic_filtered.groupby("部门", as_index=False)["员工ID"].count().rename(columns={"员工ID": "人数"})
    )
    fig_dept_count = px.bar(
        dept_count,
        x="部门",
        y="人数",
        title="各部门员工人数",
        text="人数",
        color="人数",
        color_continuous_scale="Tealgrn",
        template="plotly_dark",
    )
    fig_dept_count.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    left_col.plotly_chart(fig_dept_count, use_container_width=True)

    gender_count = basic_filtered.groupby("性别", as_index=False)["员工ID"].count()
    fig_gender = px.pie(
        gender_count,
        names="性别",
        values="员工ID",
        title="员工性别占比",
        hole=0.45,
        template="plotly_dark",
    )
    fig_gender.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    right_col.plotly_chart(fig_gender, use_container_width=True)

    line_col, bar_col = st.columns(2)

    trend_df = (
        perf_filtered.groupby(["年度", "季度"], as_index=False)["绩效评分"].mean().sort_values(["年度", "季度"])
    )
    trend_df["时间"] = trend_df["年度"].astype(str) + "Q" + trend_df["季度"].astype(str)
    fig_trend = px.line(
        trend_df,
        x="时间",
        y="绩效评分",
        title="季度平均绩效趋势",
        markers=True,
        template="plotly_dark",
    )
    fig_trend.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    line_col.plotly_chart(fig_trend, use_container_width=True)

    dept_perf = (
        merged_latest.groupby("部门", as_index=False)["绩效评分"].mean().sort_values("绩效评分", ascending=False)
    )
    fig_dept_perf = px.bar(
        dept_perf,
        x="部门",
        y="绩效评分",
        title=f"{selected_year}Q{selected_quarter} 各部门平均绩效",
        text_auto=".2f",
        color="绩效评分",
        color_continuous_scale="Viridis",
        template="plotly_dark",
    )
    fig_dept_perf.update_layout(margin=dict(l=10, r=10, t=50, b=10))
    bar_col.plotly_chart(fig_dept_perf, use_container_width=True)

    st.subheader(f"{selected_year}Q{selected_quarter} 员工绩效Top10")
    top10 = (
        merged_latest[["员工ID", "姓名", "部门", "绩效评分"]]
        .dropna(subset=["绩效评分"])
        .sort_values("绩效评分", ascending=False)
        .head(10)
    )
    fig_top10 = px.bar(
        top10,
        x="姓名",
        y="绩效评分",
        color="部门",
        text_auto=".2f",
        template="plotly_dark",
    )
    fig_top10.update_layout(margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig_top10, use_container_width=True)

    st.subheader("员工入职时间分布")
    hire_dist = (
        basic_filtered.assign(入职年月=basic_filtered["入职时间"].dt.to_period("M").astype(str))
        .groupby("入职年月", as_index=False)["员工ID"]
        .count()
        .rename(columns={"员工ID": "人数"})
    )
    fig_hire = px.line(
        hire_dist,
        x="入职年月",
        y="人数",
        markers=True,
        title="按月份统计的入职人数",
        template="plotly_dark",
    )
    fig_hire.update_layout(margin=dict(l=10, r=10, t=40, b=10))
    st.plotly_chart(fig_hire, use_container_width=True)

    st.subheader("员工明细（含最新季度绩效）")
    display_df = merged_latest.copy()
    display_df["入职时间"] = display_df["入职时间"].dt.strftime("%Y-%m-%d")
    st.dataframe(display_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    build_dashboard()
