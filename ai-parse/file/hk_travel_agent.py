from dataclasses import dataclass
from typing import List
from urllib.parse import quote
import sys

import pandas as pd
import plotly.express as px
import streamlit as st


@dataclass
class Spot:
    name: str
    category: str
    district: str
    lat: float
    lon: float
    cost_hkd: int
    duration_hours: float
    tags: str
    note: str


SPOTS: List[Spot] = [
    Spot("太平山顶", "打卡地", "中西区", 22.2759, 114.1455, 75, 2.0, "夜景,观景", "维港夜景首选，建议傍晚到达。"),
    Spot("星光大道", "打卡地", "油尖旺", 22.2937, 114.1745, 0, 1.0, "海景,漫步", "轻松散步打卡，适合拍天际线。"),
    Spot("中环摩天轮", "打卡地", "中西区", 22.2860, 114.1597, 20, 1.0, "海滨,拍照", "夜晚氛围更好，排队时间波动大。"),
    Spot("坚尼地城海旁", "打卡地", "中西区", 22.2867, 114.1270, 0, 1.5, "日落,机位", "热门日落机位，建议提前占位。"),
    Spot("石澳", "打卡地", "南区", 22.2193, 114.2510, 0, 3.0, "海边,文艺", "慢节奏海边路线，适合半日游。"),
    Spot("香港迪士尼乐园", "游玩", "离岛区", 22.3129, 114.0412, 639, 7.0, "亲子,情侣", "建议提前预约项目。"),
    Spot("海洋公园", "游玩", "南区", 22.2470, 114.1750, 498, 6.0, "亲子,刺激", "项目多，建议一整天安排。"),
    Spot("天坛大佛", "文化", "离岛区", 22.2539, 113.9049, 0, 2.5, "宗教,景观", "可与昂坪360同游。"),
    Spot("昂坪360", "游玩", "离岛区", 22.2559, 113.9076, 235, 2.0, "缆车,山景", "晴天视野更佳。"),
    Spot("黄大仙祠", "文化", "黄大仙区", 22.3419, 114.1934, 0, 1.2, "庙宇,祈福", "早间人流相对较少。"),
    Spot("庙街夜市", "美食", "油尖旺", 22.3067, 114.1717, 120, 2.0, "夜市,本地小吃", "以小吃和夜市氛围为主。"),
    Spot("兰桂坊", "美食", "中西区", 22.2810, 114.1550, 220, 2.5, "夜生活,酒吧", "夜间热闹，适合成年人。"),
    Spot("澳洲牛奶公司", "美食", "油尖旺", 22.3063, 114.1718, 80, 1.0, "茶餐厅,早餐", "经典茶餐厅，建议错峰。"),
    Spot("九记牛腩", "美食", "中西区", 22.2843, 114.1548, 110, 1.0, "牛腩面,排队", "热门店铺，排队时间较长。"),
    Spot("添好运", "美食", "深水埗", 22.3304, 114.1622, 90, 1.0, "点心,米其林", "人均友好，适合打卡。"),
]


def get_df() -> pd.DataFrame:
    return pd.DataFrame([s.__dict__ for s in SPOTS])


def xhs_search_link(keyword: str) -> str:
    return f"https://www.xiaohongshu.com/search_result?keyword={quote(keyword)}"


def build_plan(df: pd.DataFrame, days: int, budget: int, focus: str) -> pd.DataFrame:
    scoped = df.copy()
    if focus != "全部":
        scoped = scoped[scoped["category"] == focus]
    if scoped.empty:
        return scoped

    scored = scoped.copy()
    scored["score"] = (1 / (scored["cost_hkd"] + 1)) * 65 + (1 / scored["duration_hours"]) * 35
    scored = scored.sort_values("score", ascending=False)

    max_hours = days * 8
    used_budget, used_hours = 0, 0.0
    chosen = []
    for _, row in scored.iterrows():
        if used_budget + int(row["cost_hkd"]) > budget:
            continue
        if used_hours + float(row["duration_hours"]) > max_hours:
            continue
        chosen.append(row)
        used_budget += int(row["cost_hkd"])
        used_hours += float(row["duration_hours"])
        if len(chosen) >= days * 4:
            break

    if not chosen:
        return scored.head(min(3, len(scored)))
    return pd.DataFrame(chosen)


def agent_answer(query: str, df: pd.DataFrame) -> str:
    q = query.strip().lower()
    if not q:
        return "请输入你的需求，例如：3天预算1500，偏美食和打卡。"

    if "美食" in q:
        foods = df[df["category"] == "美食"]["name"].tolist()[:5]
        tips = "、".join(foods) if foods else "暂无"
        return (
            f"香港美食推荐：{tips}。"
            "建议晚餐安排在油尖旺或中环片区，步行可串联多个点位。"
        )

    if "打卡" in q or "拍照" in q:
        spots = df[df["category"] == "打卡地"]["name"].tolist()[:5]
        tips = "、".join(spots) if spots else "暂无"
        return f"热门打卡地：{tips}。建议傍晚先山顶后维港，夜景体验更好。"

    if "亲子" in q:
        return "亲子路线建议：迪士尼 + 海洋公园 + 昂坪360，至少安排2-3天。"

    if "预算" in q or "省钱" in q:
        return "省钱策略：优先免费景点（维港/星光大道/石澳），付费项目保留1-2个核心点。"

    return (
        "我可以帮你做这些：\n"
        "1) 按天数+预算生成行程\n"
        "2) 推荐美食与打卡路线\n"
        "3) 输出小红书搜索链接方便做攻略比对"
    )


def render_dashboard(df: pd.DataFrame) -> None:
    st.subheader("香港旅游地图")
    fig = px.scatter_map(
        df,
        lat="lat",
        lon="lon",
        color="category",
        size="duration_hours",
        text="name",
        hover_name="name",
        hover_data={"district": True, "cost_hkd": True, "duration_hours": True, "tags": True, "lat": False, "lon": False},
        zoom=10.1,
        map_style="carto-positron",
        height=560,
    )
    fig.update_traces(textposition="top center", textfont={"size": 12})
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="香港旅游 Agent", layout="wide")
    st.title("香港旅游 Agent")
    st.caption("为香港旅游提供：地图、美食/打卡推荐、预算行程和小红书攻略链接。")

    df = get_df()
    tab1, tab2, tab3 = st.tabs(["地图与数据", "行程生成", "Agent 问答"])

    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("景点总数", f"{df['name'].nunique()}")
        c2.metric("美食点位", f"{(df['category'] == '美食').sum()}")
        c3.metric("打卡地", f"{(df['category'] == '打卡地').sum()}")
        render_dashboard(df)
        st.dataframe(df[["name", "category", "district", "cost_hkd", "duration_hours", "tags", "note"]], use_container_width=True, hide_index=True)

    with tab2:
        col_a, col_b, col_c = st.columns(3)
        days = col_a.slider("游玩天数", 1, 7, 3, 1)
        budget = col_b.slider("门票预算(HKD)", 0, 5000, 1500, 50)
        focus = col_c.selectbox("偏好", ["全部", "美食", "打卡地", "游玩", "文化"])

        plan = build_plan(df, days=days, budget=budget, focus=focus)
        if plan.empty:
            st.warning("当前条件没有可用方案，请调整预算或偏好。")
        else:
            st.subheader("推荐行程清单")
            show = plan[["name", "category", "district", "cost_hkd", "duration_hours", "tags", "note"]].rename(
                columns={
                    "name": "地点",
                    "category": "类型",
                    "district": "区域",
                    "cost_hkd": "费用(HKD)",
                    "duration_hours": "时长(小时)",
                    "tags": "标签",
                    "note": "建议",
                }
            )
            st.dataframe(show, use_container_width=True, hide_index=True)
            st.success(
                f"预计总费用 HKD {int(plan['cost_hkd'].sum())}，总游玩时长 {plan['duration_hours'].sum():.1f} 小时。"
            )

            st.markdown("### 小红书攻略链接")
            for place in plan["name"].tolist():
                st.markdown(f"- [{place} 攻略]({xhs_search_link('香港 ' + place + ' 攻略')})")

    with tab3:
        st.subheader("和旅游 Agent 对话")
        user_query = st.text_area(
            "输入你的需求",
            value="我想要3天2晚，预算1500，重点吃美食和拍照打卡。",
            height=120,
        )
        if st.button("生成建议", type="primary"):
            answer = agent_answer(user_query, df)
            st.markdown("#### Agent 回复")
            st.write(answer)
            st.markdown("#### 相关小红书搜索")
            keywords = ["香港旅游", "香港美食", "香港打卡", "香港三天两晚攻略"]
            for kw in keywords:
                st.markdown(f"- [{kw}]({xhs_search_link(kw)})")


if __name__ == "__main__":
    # if "streamlit" not in " ".join(sys.argv).lower():
    #     print("请使用以下命令启动：streamlit run ai-parse/file/hk_travel_agent.py")
    # else:
    main()