const { spots } = require("../../data/spots");

function toXhsLink(keyword) {
  return `https://www.xiaohongshu.com/search_result?keyword=${encodeURIComponent(keyword)}`;
}

function buildPlan(list, days, budget, focus) {
  const scoped = focus === "全部" ? list : list.filter((s) => s.category === focus);
  const sorted = scoped
    .map((s) => ({
      ...s,
      score: (1 / (s.cost + 1)) * 65 + (1 / s.hours) * 35,
    }))
    .sort((a, b) => b.score - a.score);

  const maxHours = days * 8;
  let usedBudget = 0;
  let usedHours = 0;
  const plan = [];

  for (const item of sorted) {
    if (usedBudget + item.cost > budget) continue;
    if (usedHours + item.hours > maxHours) continue;
    plan.push(item);
    usedBudget += item.cost;
    usedHours += item.hours;
    if (plan.length >= days * 4) break;
  }
  return plan.length ? plan : sorted.slice(0, 3);
}

Page({
  data: {
    categories: ["全部", "美食", "打卡地", "游玩", "文化"],
    categoryIndex: 0,
    days: 3,
    budget: 1500,
    allSpots: spots,
    filteredSpots: spots,
    planSpots: [],
    markers: [],
    totalCost: 0,
    totalHours: 0,
    agentInput: "我想3天2晚，预算1500，重点吃美食和打卡。",
    agentReply: "",
    mapScale: 11
  },

  onLoad() {
    this.refreshAll();
  },

  getCurrentCategory() {
    return this.data.categories[this.data.categoryIndex];
  },

  refreshAll() {
    const focus = this.getCurrentCategory();
    const filtered = focus === "全部" ? this.data.allSpots : this.data.allSpots.filter((s) => s.category === focus);
    const plan = buildPlan(filtered, Number(this.data.days), Number(this.data.budget), focus);
    const markers = filtered.map((s) => ({
      id: s.id,
      latitude: s.lat,
      longitude: s.lng,
      title: s.name,
      width: 24,
      height: 24,
      callout: {
        content: s.name,
        color: "#ffffff",
        bgColor: "#123a74",
        borderRadius: 4,
        padding: 4,
        display: "BYCLICK"
      }
    }));

    const totalCost = plan.reduce((sum, x) => sum + x.cost, 0);
    const totalHours = plan.reduce((sum, x) => sum + x.hours, 0);

    this.setData({
      filteredSpots: filtered,
      planSpots: plan.map((x) => ({ ...x, xhsLink: toXhsLink(`香港 ${x.name} 攻略`) })),
      markers,
      totalCost,
      totalHours: totalHours.toFixed(1)
    });
  },

  onCategoryChange(e) {
    this.setData({ categoryIndex: Number(e.detail.value) });
    this.refreshAll();
  },

  onDaysChange(e) {
    this.setData({ days: Number(e.detail.value) });
    this.refreshAll();
  },

  onBudgetChange(e) {
    this.setData({ budget: Number(e.detail.value) });
    this.refreshAll();
  },

  onCopyLink(e) {
    const link = e.currentTarget.dataset.link;
    wx.setClipboardData({
      data: link,
      success: () => {
        wx.showToast({ title: "链接已复制", icon: "success" });
      }
    });
  },

  onAgentInput(e) {
    this.setData({ agentInput: e.detail.value });
  },

  onAskAgent() {
    const q = (this.data.agentInput || "").toLowerCase();
    let reply = "我可以帮你按预算和偏好生成行程，并给你对应小红书搜索链接。";

    if (q.includes("美食")) {
      reply = "美食建议：庙街夜市 + 澳洲牛奶公司 + 九记牛腩 + 添好运。晚餐优先安排在油尖旺和中环。";
    } else if (q.includes("打卡") || q.includes("拍照")) {
      reply = "打卡建议：太平山顶、星光大道、维港、坚尼地城海旁。傍晚开始路线体验更好。";
    } else if (q.includes("亲子")) {
      reply = "亲子建议：迪士尼 + 海洋公园 + 昂坪360，建议至少2-3天。";
    } else if (q.includes("预算") || q.includes("省钱")) {
      reply = "省钱建议：优先免费景点（维港、星光大道、天坛大佛），保留1-2个付费核心点。";
    }
    this.setData({ agentReply: reply });
  }
});
