{smcl}
{* *! luwx 5.0.0 04oct2026}{...}
{title:luwx — 在Stata中直接提问和分析}

{pstd}Stata 18，需配置Stata内的64位Python。安装见包内INSTALL.md。
问句和整条代码不用额外引号；Stata本来要求的字符串、文件路径引号仍照常使用。

{pstd}仓库文件发布后，首次在线安装：{cmd:net install luwx, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx) replace}。
旧版先which luwx；PERSONAL旧文件会遮挡PLUS，可用本包install.do覆盖原PERSONAL并重启。

{title:用法}

{p 8 12 2}{cmd:luwx} {it:自然语言问题}{p_end}
{p 8 12 2}{cmd:luwx check} {it:原始Stata代码}{p_end}
{p 8 12 2}{cmd:luwx run} {it:一条支持的Stata命令}{p_end}
{p 8 12 2}{cmd:luwx explain} [{it:关于最近结果的问题}]{p_end}
{p 8 12 2}{cmd:luwx find} [{cmd:lianxh}|{cmd:songbl}] {it:关键词}{p_end}
{p 8 12 2}{cmd:luwx config}, {opt key(自己的密钥)} {opt baseurl(url)} {opt model(模型ID)} {opt protocol(openai|anthropic|gemini)} [{opt auth(none)}]{p_end}

{pstd}空luwx显示简短用法。config不带选项显示当前设置且隐藏密钥；带选项保存一个当前API设置。
每位学生使用自己的密钥。不要分发个人配置；输入的config命令可能留在do-file或日志中。

{title:示例}

{phang}{cmd:luwx config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)}{p_end}
{phang}{cmd:luwx bcuse是什么意思？}{p_end}
{phang}{cmd:sysuse auto, clear}{p_end}
{phang}{cmd:luwx check regress price mpg weight, vce(robust)}{p_end}
{phang}{cmd:luwx run regress price mpg weight, vce(robust)}{p_end}
{phang}{cmd:luwx explain mpg的系数和置信区间怎么理解？}{p_end}
{phang}{cmd:luwx find DID}{p_end}
{phang}{cmd:luwx find songbl 面板}{p_end}

{pstd}find默认lianxh，只调用已安装的原命令显示资料标题和链接，不需API，也不把结果发送给AI或自动读取全文。
搜索后恢复当前数据和统计结果。只填关键词，不接受逗号选项；多关键词规则以原帮助为准。
依赖需自行安装：lianxh、insheetjson、libjson；songbl为另一可选来源。songbl可能显示原作者更新提示。
上游服务或网络失败时明确报错并恢复数据/结果，可改用另一来源。
详见{help lianxh}、{help songbl_cn}。

{title:边界}

{pstd}check仅静态审查，不执行、不保证运行成功。run在本机执行单条支持的统计命令，记录并原样显示Stata输出一次，再给AI短评；AI不能代替研究设计或证明因果。
其他命令先在Stata运行，再explain。

{pstd}run完整支持清单如下。描述与检验：describe、codebook、summarize、tabulate、tabstat、count、correlate、pwcorr、ttest、prtest、xtsum、xtdescribe。
常规回归：regress、logit、logistic、probit、poisson、nbreg、xtreg；支持desc/sum/summ/tab/corr/reg这些简称。

{pstd}数据声明：stset、xtset、tsset。生存分析：stcox、streg、stsum、stdescribe，sts仅支持list/test。
IV/固定效应：ivregress（2sls/gmm/liml）、xtivreg、areg，以及预先已安装的ivreg2、reghdfe、ivreghdfe。

{pstd}后估计：margins、test、testparm、lincom、nlcom；estat仅支持vif、hettest、ovtest、endogenous、overid、firststage、phtest、concordance、ic、summarize。

{pstd}声明命令会更新面板/时间设置或按Stata规则生成生存辅助变量（如_d/_st/_t/_t0）。后估计需相应原模型，并受Stata原有适用限制；post可替换当前e()，不代表另估了一个回归。
run不自动安装依赖，不执行图形、预测/残差/固定效应变量生成、文件或估计保存。

{pstd}普通Stata命令之后explain只能读取当前r()/e()，不能恢复完整屏幕或所有旧结果。
多变量summarize通常只保留最后一个变量的统计量，建议run以完整记录。
API回复为空或失败时仍保留本机已完成结果，可稍后explain。默认不打印内部JSON。

{pstd}数据或API变化自动隔离对话，记忆容量有限。调用API会发送本轮问题、代码、相关数据结构和统计结果。

{pstd}run正常返回时，r(analysis_rc)记录底层Stata命令执行状态，0表示命令执行成功。

{pstd}旧luweixiao保留为转发别名；luwx尚无API设置时沿用本机旧配置。
旧用户先which luwx和which luweixiao检查是否被PERSONAL旧文件遮挡，必要时用本包install.do覆盖并重启。

{pstd}完整说明与测试范围见README.md、INSTALL.md、examples.do和TEST_RESULTS.md。
源码与luwx-stata-v5.zip：{browse "https://github.com/yuanwenhua1994/AI-/tree/main/luwx":GitHub目录}。
