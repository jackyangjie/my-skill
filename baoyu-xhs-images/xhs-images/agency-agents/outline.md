---
strategy: b
name: 信息密集型
style: notion
style_reason: "Notion手绘线稿风格适合技术内容，显得专业且易读"
elements:
  background: solid-pastel
  decorations: [minimal-lines, icons]
  emphasis: highlight
  typography: clean-sans
layout: list
image_count: 5
---

## P1 封面
**Type**: cover
**Hook**: "The Agency：61个AI专家代理，开源免费"
**Visual**: 简洁标题设计，代理图标阵列，手绘线稿风格
**Layout**: sparse
**Prompt**: 小红书封面，notion风格，手绘线稿，浅色背景，标题"The Agency：61个AI专家代理"，副标题"开源免费 | 开发者必备"，周围有简单的机器人/代码图标装饰，极简设计，专业感

## P2 项目介绍
**Type**: info-card
**Message**: 
- 源自Reddit讨论，经过数月迭代
- 每个代理都有独特个性和专业领域
- 不是通用prompt，是完整的工作流程
**Visual**: 信息卡片，图标说明
**Layout**: dense
**Prompt**: 小红书内容图，notion风格，手绘线稿，三个信息卡片，分别画有：1) Reddit图标+对话气泡 2) 独特个性的AI代理头像 3) 工作流程图，浅灰色背景，蓝色和黑色线条，极简专业

## P3 9大领域
**Type**: list
**Message**: 
- 💻 Engineering: 8个代理
- 🎨 Design: 7个代理
- 📢 Marketing: 11个代理
- 📊 Product: 3个代理
- 🎬 PM: 5个代理
- 🧪 Testing: 8个代理
- 🛟 Support: 6个代理
- 🥽 Spatial: 6个代理
- 🎯 Specialized: 7个代理
**Visual**: 分类列表，数字突出
**Layout**: list
**Prompt**: 小红书内容图，notion风格，手绘线稿，9行分类列表，每行有emoji图标和数字，标题"9大领域 · 61个代理"，浅灰色背景，蓝色高亮数字，极简列表设计

## P4 使用方法
**Type**: flow
**Message**: 
1. git clone 仓库
2. cp -r agency-agents/* ~/.claude/agents/
3. 在Claude Code中激活代理
4. 开始专业协作
**Visual**: 步骤流程图
**Layout**: flow
**Prompt**: 小红书内容图，notion风格，手绘线稿，4步流程图，每步有数字圆圈和简单图标：1) 下载图标 2) 复制图标 3) 激活图标 4) 协作图标，箭头连接，浅灰色背景，蓝色和黑色线条

## P5 推荐
**Type**: recommendation
**Message**: 开源MIT协议，支持Claude/Cursor/Aider等工具，GitHub: msitarzewski/agency-agents
**Visual**: GitHub链接，工具图标
**Layout**: balanced
**Prompt**: 小红书结尾图，notion风格，手绘线稿，GitHub猫图标，下方有Claude/Cursor/Aider工具logo，文字"开源免费 · 立即体验"，浅灰色背景，蓝色高亮，极简设计
