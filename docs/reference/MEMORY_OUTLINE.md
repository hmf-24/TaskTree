---
source: 工作文档
author: HMF
created: 2026-04-10
description: "Claude Code 记忆系统设计大纲，三层记忆架构 Auto/Session/Team"
tags:
  - Status/Done
  - Type/Work/SOP
  - Area/Lab
  - Tech/AI_Model
---

# Claude Code 记忆系统设计 - 大纲

## 一、存储架构
1.1 长期记忆目录结构
1.2 Team 记忆目录结构

## 二、记忆类型
2.1 四种记忆类型 (user/feedback/project/reference)
2.2 不保存的内容
2.3 frontmatter 格式

## 三、加载机制
3.1 入口文件加载 (MEMORY.md)
3.2 记忆检索 (findRelevantMemories)
3.3 动态加载 (增量加载)

## 四、提取机制
4.1 触发时机
4.2 子代理执行
4.3 提取 Prompt 设计

## 五、会话记忆
5.1 会话摘要
5.2 自动压缩

## 六、TaskTree 迁移建议