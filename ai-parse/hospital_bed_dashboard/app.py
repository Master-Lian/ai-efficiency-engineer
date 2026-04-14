from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from flask import Flask, jsonify, render_template

app = Flask(__name__)


def get_bed_data() -> List[Dict]:
    """构造示例病床数据，可替换为数据库或接口数据源。"""
    return [
        {
            "hospital": "中心医院",
            "region": "东区",
            "department": "ICU",
            "total_beds": 80,
            "occupied_beds": 70,
        },
        {
            "hospital": "中心医院",
            "region": "东区",
            "department": "心内科",
            "total_beds": 120,
            "occupied_beds": 102,
        },
        {
            "hospital": "人民医院",
            "region": "西区",
            "department": "神经内科",
            "total_beds": 90,
            "occupied_beds": 62,
        },
        {
            "hospital": "人民医院",
            "region": "西区",
            "department": "骨科",
            "total_beds": 110,
            "occupied_beds": 84,
        },
        {
            "hospital": "妇幼保健院",
            "region": "南区",
            "department": "产科",
            "total_beds": 100,
            "occupied_beds": 73,
        },
        {
            "hospital": "妇幼保健院",
            "region": "南区",
            "department": "儿科",
            "total_beds": 95,
            "occupied_beds": 66,
        },
    ]


def aggregate_hospital_stats(data: List[Dict]) -> List[Dict]:
    """按医院聚合病床信息。"""
    merged: Dict[str, Dict] = {}
    for item in data:
        hospital = item["hospital"]
        if hospital not in merged:
            merged[hospital] = {"hospital": hospital, "total_beds": 0, "occupied_beds": 0}
        merged[hospital]["total_beds"] += item["total_beds"]
        merged[hospital]["occupied_beds"] += item["occupied_beds"]

    result = []
    for value in merged.values():
        free_beds = value["total_beds"] - value["occupied_beds"]
        occupancy_rate = round(value["occupied_beds"] / value["total_beds"] * 100, 1)
        result.append(
            {
                **value,
                "free_beds": free_beds,
                "occupancy_rate": occupancy_rate,
            }
        )
    return result


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dashboard")
def dashboard_data():
    raw_data = get_bed_data()
    hospital_stats = aggregate_hospital_stats(raw_data)

    total_beds = sum(item["total_beds"] for item in raw_data)
    occupied_beds = sum(item["occupied_beds"] for item in raw_data)
    free_beds = total_beds - occupied_beds
    overall_occupancy = round(occupied_beds / total_beds * 100, 1)

    region_distribution: Dict[str, int] = {}
    department_distribution: Dict[str, int] = {}
    department_usage: Dict[str, Dict[str, int]] = {}

    for item in raw_data:
        region_distribution[item["region"]] = region_distribution.get(item["region"], 0) + item["total_beds"]
        department_distribution[item["department"]] = department_distribution.get(item["department"], 0) + item["total_beds"]
        department_usage[item["department"]] = {
            "occupied": item["occupied_beds"],
            "free": item["total_beds"] - item["occupied_beds"],
        }

    payload = {
        "overview": {
            "total_beds": total_beds,
            "occupied_beds": occupied_beds,
            "free_beds": free_beds,
            "occupancy_rate": overall_occupancy,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "hospital_table": hospital_stats,
        "hospital_occupancy_chart": [
            {"name": item["hospital"], "value": item["occupancy_rate"]} for item in hospital_stats
        ],
        "free_bed_chart": [
            {"name": item["hospital"], "value": item["free_beds"]} for item in hospital_stats
        ],
        "department_usage_chart": [
            {"name": dept, "occupied": values["occupied"], "free": values["free"]}
            for dept, values in department_usage.items()
        ],
        "region_distribution_chart": [
            {"name": region, "value": beds} for region, beds in region_distribution.items()
        ],
        "department_distribution_chart": [
            {"name": dept, "value": beds} for dept, beds in department_distribution.items()
        ],
    }
    return jsonify(payload)


if __name__ == "__main__":
    app.run(debug=True)
