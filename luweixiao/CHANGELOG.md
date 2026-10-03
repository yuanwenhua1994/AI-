# 更新记录

## 4.0.0 — 2026-10-04

- 重写为直接提问、check、run、explain和单个API配置；整句和整条代码无需额外引号，保留Stata原有字符串/路径语法。
- check仅审查代码；run明确执行单条支持的统计命令，保留真实输出并给短评；explain继续讨论最近结果。普通Stata后的r()/e()读取不能恢复完整屏幕。
- 原样显示Stata结果一次，不默认输出内部JSON。API失败仍保留本机结果；数据/API变化自动隔离有限对话记忆。
- 移除旧版课程、工作流、写作、agent及session/profile等界面，学生只需配置自己的API。安装包不含教师配置或密钥。
- 保留OpenAI兼容、Anthropic、Gemini协议及免密钥本地兼容接口。已准备[GitHub源码/ZIP发布目录](https://github.com/yuanwenhua1994/AI-/tree/main/luweixiao)，发布后在线安装地址为https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luweixiao；实际测试范围见TEST_RESULTS.md。
- 更新前检查which：PERSONAL旧文件会遮挡PLUS；旧用户可用本包install.do覆盖原PERSONAL并重启。
