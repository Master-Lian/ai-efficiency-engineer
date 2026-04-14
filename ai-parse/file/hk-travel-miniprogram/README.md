# 香港旅游 Agent - 微信小程序版

## 功能
- 香港景点地图（地图点位 + 中文名称）
- 美食/打卡地/游玩/文化分类筛选
- 按天数与预算自动推荐行程
- 生成并复制小红书搜索链接
- 简单对话式 Agent 建议

## 目录
- `app.js` / `app.json` / `app.wxss`
- `pages/index/` 首页逻辑与 UI
- `data/spots.js` 景点数据

## 使用方式
1. 打开微信开发者工具
2. 选择导入项目：`ai-parse/file/hk-travel-miniprogram`
3. 将 `project.config.json` 中的 `appid` 改成你自己的小程序 AppID
4. 编译运行

## 说明
- 小程序环境通常不能直接打开外部小红书网页，当前实现为“复制链接”方案，便于用户粘贴到浏览器或其他工具打开。
