async function fetchDashboardData() {
  const response = await fetch("/api/dashboard");
  if (!response.ok) {
    throw new Error("获取大屏数据失败");
  }
  return response.json();
}

function renderOverview(overview) {
  document.getElementById("totalBeds").textContent = overview.total_beds;
  document.getElementById("occupiedBeds").textContent = overview.occupied_beds;
  document.getElementById("freeBeds").textContent = overview.free_beds;
  document.getElementById("occupancyRate").textContent = `${overview.occupancy_rate}%`;
  document.getElementById("updatedAt").textContent = `更新时间：${overview.updated_at}`;
}

function renderHospitalTable(rows) {
  const tbody = document.getElementById("hospitalTableBody");
  tbody.innerHTML = rows
    .map(
      (row) => `
      <tr>
        <td>${row.hospital}</td>
        <td>${row.total_beds}</td>
        <td>${row.occupied_beds}</td>
        <td>${row.free_beds}</td>
        <td>${row.occupancy_rate}%</td>
      </tr>
    `,
    )
    .join("");
}

function createHospitalOccupancyChart(data) {
  const chart = echarts.init(document.getElementById("hospitalOccupancyChart"));
  chart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "category", data: data.map((item) => item.name) },
    yAxis: { type: "value", min: 0, max: 100, axisLabel: { formatter: "{value}%" } },
    series: [
      {
        name: "占用率",
        type: "bar",
        data: data.map((item) => item.value),
        itemStyle: { color: "#4fb3ff" },
        label: { show: true, position: "top", formatter: "{c}%" },
      },
    ],
  });
  return chart;
}

function createFreeBedChart(data) {
  const chart = echarts.init(document.getElementById("freeBedChart"));
  chart.setOption({
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { color: "#d6e8ff" } },
    series: [
      {
        name: "空闲病床",
        type: "pie",
        radius: ["42%", "72%"],
        data,
        label: { formatter: "{b}\n{c} 张" },
      },
    ],
  });
  return chart;
}

function createDepartmentUsageChart(data) {
  const chart = echarts.init(document.getElementById("departmentUsageChart"));
  chart.setOption({
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    legend: { textStyle: { color: "#d6e8ff" } },
    xAxis: { type: "category", data: data.map((item) => item.name) },
    yAxis: { type: "value" },
    series: [
      {
        name: "已占用",
        type: "bar",
        stack: "beds",
        data: data.map((item) => item.occupied),
        itemStyle: { color: "#3ddc97" },
      },
      {
        name: "空闲",
        type: "bar",
        stack: "beds",
        data: data.map((item) => item.free),
        itemStyle: { color: "#ffc857" },
      },
    ],
  });
  return chart;
}

function createRegionDistributionChart(data) {
  const chart = echarts.init(document.getElementById("regionDistributionChart"));
  chart.setOption({
    tooltip: { trigger: "axis" },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: data.map((item) => item.name) },
    series: [
      {
        name: "病床数量",
        type: "bar",
        data: data.map((item) => item.value),
        itemStyle: { color: "#9d7fff" },
        label: { show: true, position: "right" },
      },
    ],
  });
  return chart;
}

async function initDashboard() {
  try {
    const data = await fetchDashboardData();
    renderOverview(data.overview);
    renderHospitalTable(data.hospital_table);

    const charts = [
      createHospitalOccupancyChart(data.hospital_occupancy_chart),
      createFreeBedChart(data.free_bed_chart),
      createDepartmentUsageChart(data.department_usage_chart),
      createRegionDistributionChart(data.region_distribution_chart),
    ];

    // 统一监听窗口变化，确保大屏在不同分辨率下都能自适应
    window.addEventListener("resize", () => {
      charts.forEach((chart) => chart.resize());
    });
  } catch (error) {
    console.error(error);
    alert("数据加载失败，请检查后端服务是否正常启动。");
  }
}

initDashboard();
