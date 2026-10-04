# luwx 5.0：在 Stata 中直接提问和分析

需要 Stata 18 和 Stata 内可用的64位Python。下载 `luwx-stata-v5.zip`，解压后运行 `do install.do`；仓库文件发布后也可用下方在线命令。配置按 [INSTALL.md](INSTALL.md) 操作；每位学生使用自己的API密钥。

```stata
net install luwx, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx) replace
```

```stata
* 将“自己的密钥”换成你申请的API密钥，只需配置一次。
luwx config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)

* 直接问，不用给整句话加引号。
luwx bcuse是什么意思？

sysuse auto, clear
* 检查代码，不执行。
luwx check regress price mpg weight, vce(robust)
* 在本机执行：原样显示Stata结果一次，再给AI短评。
luwx run regress price mpg weight, vce(robust)
* 接着问刚才的结果。
luwx explain mpg的系数和置信区间怎么理解？
* 也可明确执行相应的后估计诊断。
luwx run estat vif
```

`check`只审查代码，不能保证代码能运行或研究设计正确。`run`接受一条支持的Stata命令，真实数值由本机计算；也支持面板/生存声明、IV、固定效应和指定后估计命令，详见 `help luwx`。例如先 `luwx run xtset id year`，再 `luwx run xtreg y x, fe`。其他指令先在Stata正常运行，再 `luwx explain`。AI解释不能证明因果关系。

声明命令会按Stata原有行为更新设置或辅助变量；后估计需要相应原模型，`post`可替换当前e()。插件不自动安装估计命令，也不生成预测变量、图形或保存分析文件。

普通Stata命令之后的 `explain`只能读取当前保留的r()/e()，不能恢复整屏或所有旧结果；多变量summarize通常只留下最后一个变量的统计量。需要完整对应时，优先使用 `run`。API回复为空或失败时保留本机结果，可稍后再 `explain`。

数据或API设置变化会自动隔离对话；记忆有容量限制。空 `luwx`显示简短用法；`luwx config`显示隐藏密钥的当前设置。支持OpenAI兼容、Anthropic、Gemini协议及 `auth(none)`本地兼容接口，地址和模型ID以服务商为准。

每次check或run从本轮代码与真实证据重新开始，避免旧回答带偏新的检查；explain和直接提问可以继续讨论最近结果。

需要查教程时，先按 [INSTALL.md](INSTALL.md) 安装可选检索命令，然后直接搜：

```stata
luwx find DID
luwx find lianxh 控制变量
luwx find songbl 面板
```

`find`默认连享会，只调用本机已安装的原命令显示标题和链接，不调用AI、不自动读取全文或发送搜索结果给模型；当前数据和统计结果会恢复。只输入关键词，不加逗号选项；不同来源的多关键词规则以原帮助为准。上游服务或网络失败会明确报错并恢复数据/结果，可改用另一来源。songbl可能显示原作者更新提示，由用户决定。原始资料：[连享会命令](https://github.com/arlionn/lianxh)、[songbl作者/SSC条目](https://ideas.repec.org/c/boc/bocode/s458919.html)。

问句和整条代码不用额外引号；Stata本来要求的文件路径或字符串引号仍照常使用。配置密钥会出现在你输入的do-file或日志中，不要分享这些文件或个人配置。分发学生只发送完整安装包。

旧 `luweixiao` 保留为转发别名，建议改用 `luwx`；已有本机API设置可沿用，不随安装包分发。旧用户先 `which luwx` 和 `which luweixiao` 检查位置；PERSONAL旧文件可能遮挡PLUS新安装，可用本包install.do覆盖并重启。源码与ZIP位于 [GitHub目录](https://github.com/yuanwenhua1994/AI-/tree/main/luwx)；实际测试范围见 `TEST_RESULTS.md`。
