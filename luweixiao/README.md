# luweixiao 4.0：在 Stata 中直接提问和分析

需要 Stata 18 和 Stata 内可用的64位Python。下载 `luweixiao-stata-v4.zip`，解压后运行 `do install.do`；仓库文件发布后也可用下方在线命令。配置按 [INSTALL.md](INSTALL.md) 操作；每位学生使用自己的API密钥。

```stata
net install luweixiao, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luweixiao) replace
```

```stata
* 将“自己的密钥”换成你申请的API密钥，只需配置一次。
luweixiao config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)

* 直接问，不用给整句话加引号。
luweixiao bcuse是什么意思？

sysuse auto, clear
* 检查代码，不执行。
luweixiao check regress price mpg weight, vce(robust)
* 在本机执行：原样显示Stata结果一次，再给AI短评。
luweixiao run regress price mpg weight, vce(robust)
* 接着问刚才的结果。
luweixiao explain mpg的系数和置信区间怎么理解？
```

`check`只审查代码，不能保证代码能运行或研究设计正确。`run`接受一条支持的统计命令，真实数值由本机Stata计算；其他命令先在Stata正常运行，再用 `luweixiao explain`。例如先 `xtset id year`，再 `luweixiao run xtreg y x, fe`。AI解释不能证明因果关系。

普通Stata命令之后的 `explain`只能读取当前保留的r()/e()，不能恢复整屏或所有旧结果；多变量summarize通常只留下最后一个变量的统计量。需要完整对应时，优先使用 `run`。API超时也保留本机结果，可稍后再 `explain`。

数据或API设置变化会自动隔离对话；记忆有容量限制。空 `luweixiao`显示简短用法；`luweixiao config`显示隐藏密钥的当前设置。支持OpenAI兼容、Anthropic、Gemini协议及 `auth(none)`本地兼容接口，地址和模型ID以服务商为准。

问句和整条代码不用额外引号；Stata本来要求的文件路径或字符串引号仍照常使用。配置密钥会出现在你输入的do-file或日志中，不要分享这些文件或个人配置。分发学生只发送完整安装包。

旧用户先 `which luweixiao`：PERSONAL旧版会遮挡PLUS新安装，可用本包install.do覆盖原PERSONAL并重启。源码与ZIP位于 [GitHub目录](https://github.com/yuanwenhua1994/AI-/tree/main/luweixiao)；实际测试范围见 `TEST_RESULTS.md`。
