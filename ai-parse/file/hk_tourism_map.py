from dataclasses import dataclass

import pandas as pd
import plotly.express as px
import streamlit as st


@dataclass
class Attraction:
    name: str
    category: str
    district: str
    lat: float
    lon: float
    ticket_hkd: int
    duration_hours: float
    best_time: str
    intro: str


ATTRACTIONS = [
    Attraction("太平山顶", "观景", "中西区", 22.2759, 114.1455, 75, 2.0, "傍晚至夜景", "香港经典夜景机位，可俯瞰维港。"),
    Attraction("维多利亚港", "观景", "油尖旺", 22.2933, 114.1694, 0, 1.5, "全天/夜晚", "香港地标海港，适合散步和拍照。"),
    Attraction("星光大道", "城市漫步", "油尖旺", 22.2937, 114.1745, 0, 1.0, "傍晚", "海滨步道，可看灯光秀和城市天际线。"),
    Attraction("香港迪士尼乐园", "亲子乐园", "离岛区", 22.3129, 114.0412, 639, 7.0, "全天", "适合亲子和情侣的一日游项目。"),
    Attraction("海洋公园", "亲子乐园", "南区", 22.2470, 114.1750, 498, 6.0, "全天", "动物展示+机动游戏，项目丰富。"),
    Attraction("尖沙咀钟楼", "地标", "油尖旺", 22.2948, 114.1694, 0, 0.7, "全天", "历史建筑地标，打卡成本低。"),
    Attraction("天坛大佛", "人文", "离岛区", 22.2539, 113.9049, 0, 3.0, "上午", "位于大屿山，可结合昂坪缆车。"),
    Attraction("昂坪360", "缆车", "离岛区", 22.2559, 113.9076, 235, 2.5, "上午", "缆车视野开阔，连接大佛景区。"),
    Attraction("黄大仙祠", "人文", "黄大仙区", 22.3419, 114.1934, 0, 1.2, "上午", "香港知名庙宇，香火旺盛。"),
    Attraction("庙街夜市", "美食夜市", "油尖旺", 22.3067, 114.1717, 0, 2.0, "夜晚", "地道夜市，美食和烟火气十足。"),
    Attraction("中环摩天轮", "城市漫步", "中西区", 22.2860, 114.1597, 20, 1.0, "傍晚", "海滨地标，适合短时打卡。"),
    Attraction("石澳", "海滨", "南区", 22.2193, 114.2510, 0, 3.0, "下午", "海边慢游路线，适合轻松拍照。"),
]


def get_df() -> pd.DataFrame:
    return pd.DataFrame([a.__dict__ for a in ATTRACTIONS])


def build_recommendation(df: pd.DataFrame, days: int, budget: int) -> pd.DataFrame:
    # 优先选择评分更“值回票价”的景点：免费/低价 + 代表性项目组合
    scored = df.copy()
    scored["budget_score"] = (1 / (scored["ticket_hkd"] + 1)) * 100
    scored["time_score"] = 1 / scored["duration_hours"]
    scored["score"] = scored["budget_score"] * 0.55 + scored["time_score"] * 45
    scored = scored.sort_values("score", ascending=False)

    max_hours = max(days, 1) * 8
    plan, used_budget, used_hours = [], 0, 0.0

    for _, row in scored.iterrows():
        if used_budget + int(row["ticket_hkd"]) > budget:
            continue
        if used_hours + float(row["duration_hours"]) > max_hours:
            continue
        plan.append(row)
        used_budget += int(row["ticket_hkd"])
        used_hours += float(row["duration_hours"])
        if len(plan) >= days * 4:
            break

    if not plan:
        return scored.head(min(3, len(scored)))
    return pd.DataFrame(plan)


def main() -> None:
    st.set_page_config(page_title="香港旅游地图", layout="wide")
    st.title("中国香港旅游地图与行程助手")
    st.caption("包含景点地图、筛选、预算推荐与简单行程规划。")

    df = get_df()

    st.sidebar.header("筛选条件")
    category_options = sorted(df["category"].unique().tolist())
    district_options = sorted(df["district"].unique().tolist())
    selected_categories = st.sidebar.multiselect("景点类别", category_options, default=category_options)
    selected_districts = st.sidebar.multiselect("行政区", district_options, default=district_options)
    max_ticket = st.sidebar.slider("单景点最高门票（HKD）", 0, 700, 700, 10)
    days = st.sidebar.slider("计划游玩天数", 1, 7, 3, 1)
    budget = st.sidebar.slider("总预算（门票，HKD）", 0, 3000, 1200, 50)

    filtered = df[
        df["category"].isin(selected_categories)
        & df["district"].isin(selected_districts)
        & (df["ticket_hkd"] <= max_ticket)
    ].copy()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("景点数量", f"{len(filtered)}")
    c2.metric("平均门票", f"HKD {filtered['ticket_hkd'].mean() if len(filtered) else 0:.0f}")
    c3.metric("平均游玩时长", f"{filtered['duration_hours'].mean() if len(filtered) else 0:.1f} 小时")
    c4.metric("覆盖区域", f"{filtered['district'].nunique() if len(filtered) else 0}")

    if filtered.empty:
        st.warning("当前筛选条件下没有景点，请调整左侧筛选。")
        return

    fig_map = px.scatter_map(
        filtered,
        lat="lat",
        lon="lon",
        color="category",
        size="duration_hours",
        text="name",
        hover_name="name",
        hover_data={
            "district": True,
            "ticket_hkd": True,
            "duration_hours": True,
            "best_time": True,
            "lat": False,
            "lon": False,
        },
        zoom=10.2,
        height=620,
        map_style="carto-darkmatter",
        title="香港景点分布地图（中文标注）",
    )
    fig_map.update_traces(
        textposition="top center",
        textfont={"size": 12, "color": "#FFFFFF"},
        marker={"opacity": 0.9},
    )
    fig_map.update_layout(margin=dict(l=8, r=8, t=50, b=8))
    st.plotly_chart(fig_map, use_container_width=True)

    left, right = st.columns(2)

    cat_stats = (
        filtered.groupby("category", as_index=False)["name"].count().rename(columns={"name": "数量"})
    )
    fig_cat = px.bar(cat_stats, x="category", y="数量", color="数量", title="景点类别分布", template="plotly_dark")
    left.plotly_chart(fig_cat, use_container_width=True)

    district_stats = (
        filtered.groupby("district", as_index=False)["name"].count().rename(columns={"name": "数量"})
    )
    fig_dist = px.pie(district_stats, names="district", values="数量", hole=0.4, title="行政区覆盖占比", template="plotly_dark")
    right.plotly_chart(fig_dist, use_container_width=True)

    st.subheader("智能行程建议（按预算和天数）")
    rec = build_recommendation(filtered, days=days, budget=budget)
    rec_show = rec[["name", "category", "district", "ticket_hkd", "duration_hours", "best_time", "intro"]].rename(
        columns={
            "name": "景点",
            "category": "类别",
            "district": "行政区",
            "ticket_hkd": "门票(HKD)",
            "duration_hours": "建议时长(小时)",
            "best_time": "推荐时段",
            "intro": "简介",
        }
    )
    st.dataframe(rec_show, use_container_width=True, hide_index=True)
    st.info(
        f"推荐景点 {len(rec_show)} 个，预计门票总计 HKD {int(rec['ticket_hkd'].sum()) if len(rec) else 0}，"
        f"总游玩时长 {rec['duration_hours'].sum() if len(rec) else 0:.1f} 小时。"
    )


if __name__ == "__main__":
    main()
