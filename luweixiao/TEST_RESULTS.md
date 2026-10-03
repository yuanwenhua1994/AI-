# luweixiao 4.0 测试范围

2026-10-04；Windows、Stata 18 MP、64位Python 3.12。使用独立Stata引擎和课堂数据，不替换老师正在编辑的数据。

- 34项实际Stata集成检查通过：无引号中文提问和含逗号代码、配置保存/显示/修复、check不执行及保留原r()、run真实回归与一次表格显示、系数/r(table)精确对应、完整四变量摘要、连续追问、真实r(111)错误、拒绝旧结果、数据变化隔离对话、API失败保留计算并可续问、未配置API也能记录本机输出等。
- 独立证据测试5组通过：因子变量/if/in/权重/稳健回归的e(b)/e(V)与直接命令一致，完整describe/summarize/tabstat文本、logistic来源、已有命名日志保持开启、临时日志清理、r()保护。38类不支持输入被拒绝，包括describe replace及缩写、tabulate generate、shell/文件/宏/块，以及regress if/in省略模型后的旧结果重放。
- 单一API配置模块24项测试通过；独立来源与失败路径审查9项测试通过。带内部Stata字符串引号的 `run count if make=="BMW 320i"` 已实测N=1，无需给整条代码再加引号。
- 本地net install与install.do复制安装均通过。6个运行文件能离开源目录使用，未分发个人配置；未配置API时的本机摘要/回归仍保存真实结果。examples.do离线部分运行通过。

## 真实API

使用老师已有的Intern接口 `https://discovery-api.intern-ai.org.cn/v1` 和 `glm-5.3`，分别测试check、run及explain：正确指出mpgg变量不存在；实际回归N=74；连续追问对应mpg系数约21.85、p约0.787、95%区间约[-139.19,182.90]，说明区间包含0。真实回答会随模型而变化，提示词已要求不将未执行诊断当作已知原因。

API适配器与v3.1逐字节相同，原29项协议模拟测试已有通过记录。支持OpenAI Chat Completions兼容、Anthropic Messages和Gemini generateContent；原生Anthropic/Gemini未用真实账户调用，不能保证每个服务商的私有接口或模型都兼容。

## 能力边界

check是模型静态审查，不能保证Stata接受代码或研究设计正确。run实际计算且保留输出；运行成功不证明因果识别。explain读取本次已记录结果或当前r/e，不恢复整个Results窗口；多变量sum的旧r通常只有最后一列。文本超过120000字符及大矩阵会明确裁剪。未核实变量定义、数据来源和识别条件时，仍需作者补充。

测试宿主PyStata关闭异步输出，以避免它与SFI同时读取输出缓冲区；学生在Stata中无需PyStata或额外API SDK。[Stata SFI说明](https://www.stata.com/python/api18/SFIToolkit.html)与[net安装说明](https://www.stata.com/manuals/rnet.pdf)用于接口核对。
