{smcl}
{* *! luweixiao 4.0.0 04oct2026}{...}
{title:luweixiao — 在Stata中直接提问和分析}

{pstd}Stata 18，需配置Stata内的64位Python。安装见包内INSTALL.md。
问句和整条代码不用额外引号；Stata本来要求的字符串、文件路径引号仍照常使用。

{pstd}仓库文件发布后，首次在线安装：{cmd:net install luweixiao, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luweixiao) replace}。
旧版先which luweixiao；PERSONAL旧文件会遮挡PLUS，可用本包install.do覆盖原PERSONAL并重启。

{title:用法}

{p 8 12 2}{cmd:luweixiao} {it:自然语言问题}{p_end}
{p 8 12 2}{cmd:luweixiao check} {it:原始Stata代码}{p_end}
{p 8 12 2}{cmd:luweixiao run} {it:一条支持的Stata统计命令}{p_end}
{p 8 12 2}{cmd:luweixiao explain} [{it:关于最近结果的问题}]{p_end}
{p 8 12 2}{cmd:luweixiao config}, {opt key(自己的密钥)} {opt baseurl(url)} {opt model(模型ID)} {opt protocol(openai|anthropic|gemini)} [{opt auth(none)}]{p_end}

{pstd}空luweixiao显示简短用法。config不带选项显示当前设置且隐藏密钥；带选项保存一个当前API设置。
每位学生使用自己的密钥。不要分发个人配置；输入的config命令可能留在do-file或日志中。

{title:示例}

{phang}{cmd:luweixiao config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)}{p_end}
{phang}{cmd:luweixiao bcuse是什么意思？}{p_end}
{phang}{cmd:sysuse auto, clear}{p_end}
{phang}{cmd:luweixiao check regress price mpg weight, vce(robust)}{p_end}
{phang}{cmd:luweixiao run regress price mpg weight, vce(robust)}{p_end}
{phang}{cmd:luweixiao explain mpg的系数和置信区间怎么理解？}{p_end}

{title:边界}

{pstd}check仅静态审查，不执行、不保证运行成功。run在本机执行单条支持的统计命令，记录并原样显示Stata输出一次，再给AI短评；AI不能代替研究设计或证明因果。
其他命令先在Stata运行，再explain。面板估计先正常xtset，再run xtreg。

{pstd}普通Stata命令之后explain只能读取当前r()/e()，不能恢复完整屏幕或所有旧结果。
多变量summarize通常只保留最后一个变量的统计量，建议run以完整记录。
API超时仍保留本机已完成结果，可稍后explain。默认不打印内部JSON。

{pstd}数据或API变化自动隔离对话，记忆容量有限。调用API会发送本轮问题、代码、相关数据结构和统计结果。

{pstd}run正常返回时，r(analysis_rc)记录底层Stata命令执行状态，0表示命令执行成功。

{pstd}完整说明与测试范围见README.md、INSTALL.md、examples.do和TEST_RESULTS.md。
源码与luweixiao-stata-v4.zip：{browse "https://github.com/yuanwenhua1994/AI-/tree/main/luweixiao":GitHub目录}。
