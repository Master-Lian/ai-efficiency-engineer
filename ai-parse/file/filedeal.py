from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def merge_basic_with_q4_performance() -> Path:
    base_dir = Path(__file__).resolve().parent
    basic_info_path = base_dir / "员工基本信息表.xlsx"
    performance_path = base_dir / "员工绩效表.xlsx"
    output_path = base_dir / "员工基本信息_2024Q4绩效.csv"

    basic_df = pd.read_excel(basic_info_path).copy()
    performance_df = pd.read_excel(performance_path).copy()

    basic_df["入职时间"] = pd.to_datetime(basic_df["入职时间"]).dt.strftime("%Y-%m-%d")

    q4_df = performance_df[
        (performance_df["年度"] == 2024) & (performance_df["季度"] == 4)
    ][["员工ID", "绩效评分"]].copy()
    q4_df = q4_df.rename(columns={"绩效评分": "2024Q4绩效评分"})

    merged_df = pd.merge(basic_df, q4_df, on="员工ID", how="left")
    try:
        merged_df.to_csv(output_path, index=False, encoding="utf-8-sig")
        return output_path
    except PermissionError:
        fallback_path = base_dir / "员工基本信息_2024Q4绩效_new.csv"
        merged_df.to_csv(fallback_path, index=False, encoding="utf-8-sig")
        return fallback_path


def plot_employee_entry_dates() -> Path:
    base_dir = Path(__file__).resolve().parent
    basic_info_path = base_dir / "员工基本信息表.xlsx"
    chart_path = base_dir / "员工入职时间折线图.png"

    basic_df = pd.read_excel(basic_info_path).copy()
    basic_df["入职时间"] = pd.to_datetime(basic_df["入职时间"])
    plot_df = basic_df.sort_values("入职时间").reset_index(drop=True)

    # Windows 常见中文字体，避免图表中文乱码
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
    plt.rcParams["axes.unicode_minus"] = False

    plt.figure(figsize=(12, 6))
    plt.plot(plot_df["姓名"], plot_df["入职时间"], marker="o", linewidth=2)
    plt.title("每个员工入职时间折线图")
    plt.xlabel("员工姓名")
    plt.ylabel("入职时间")
    plt.xticks(rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(chart_path, dpi=150)
    plt.close()
    return chart_path


if __name__ == "__main__":
    saved_path = merge_basic_with_q4_performance()
    print(f"已生成合并文件：{saved_path}")
    chart_file = plot_employee_entry_dates()
    print(f"已生成图表文件：{chart_file}")
