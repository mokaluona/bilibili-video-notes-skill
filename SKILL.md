---
name: bilibili-video-notes
description: "从 B 站教育/讲课视频生成带截图的 DOCX 学习笔记(三档:精读/过一遍/总结)。下载视频+字幕→抽帧→OCR去重→AI视觉打分→提取图中内容→融合生成DOCX。"
tags: [bilibili, video, notes, OCR, vision, subtitles, docx]
triggers:
  - bilibili视频笔记
  - 视频笔记
  - 从视频做笔记
  - video notes
---

# Bilibili Video Notes

**本项目指令的唯一真源是 [`AGENTS.md`](AGENTS.md)，内容以它为准。**

上面 frontmatter 的触发词是本文件唯一还要留着的东西（Kimi 靠它认这个 skill）；
正文不在这里重复 —— 流程、目录规范、关键规则全部看 `AGENTS.md`。

本机层（自己机器上的路径、运行目录、密钥位置）看本目录下 git 忽略的 `local.<agent>.md`；
没有就照 `local.example.md` 抄一份。
