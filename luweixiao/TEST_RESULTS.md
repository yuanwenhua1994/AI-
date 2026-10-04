# luwx 5.0 测试范围

2026-10-04；Windows、Stata 18 MP、64位Python 3.12。使用独立Stata引擎、课堂数据和生成数据，不替换老师当前编辑的数据。

- 39项真实Stata集成检查、39项设置/配置迁移检查、18项独立来源检查通过。覆盖无整行引号输入、准确数值、完整输出一次、错误及空白API回复后保留结果、旧名与迁移、查资料后继续追问。
- 新功能4组通过：用户完整stset、生存统计与模型；7种IV/FE命令和9种规格；12项后估计含margins/nlcom,post；44项文件/修改/重放等范围拦截。已安装的ivreg2/reghdfe/ivreghdfe均用真实Stata核对。
- 原功能5组兼容检查、6条实际ado生存/后估计调用通过；原生截尾反例证实有效进入者在行政截止右删失，延迟进入不因晚于origin自动排除。依据[Stata stset手册](https://www.stata.com/manuals/ststset.pdf)。
- 本地net install和install.do通过，8个运行文件可独立安装，不含个人设置；离线examples.do通过。另保留luweixiao兼容安装入口。
- 本机Stata原生GitHub HTTPS安装返回r(603)；备用Python安装入口已实际通过HTTPS下载公开文件、核对SHA256清单并交给真实Stata安装。独立PLUS中8个运行文件与源文本一致（允许Windows换行转换），未复制配置，summarize真实结果保留。安装入口另有13项边界检查通过。

## 真实服务

Intern接口`https://discovery-api.intern-ai.org.cn/v1`、模型`glm-5.3`：实际调用check、完整stset、stcox和旧名explain。生成数据声明240个体、163个失败；x的风险比约1.119，95%区间[0.930,1.345]，p约0.233。另实测静态截尾解释，以及p=0.060在5%水平不显著。接口曾限流，测试等待后完成；产品不自动重复执行统计命令。

实测中模型曾误述截尾规则、猜变量含义、把0.060说成低于0.05；已补强提示并让新check/run不引用旧答案，再核验相关解释。测试不代表任意模型的所有解释都正确，应继续核对Stata输出、变量定义与方法。

find的13项原生命令替身检查验证转发及数据/r/e恢复。原作者lianxh实际返回6条生存分析教程；songbl本次Stata下载返回r(601)，数据与结果恢复，因此未宣称songbl真实联网检索通过。标题/链接不代表读取全文，也不会发送给AI。

API适配器保留OpenAI兼容、Anthropic Messages、Gemini generateContent处理；原生Anthropic/Gemini本轮未用真实账户调用，不保证服务商私有协议或任意模型兼容。

## 边界

check为静态审查；run由Stata计算，不证明研究设计成立。explain读取保存的真实输出或当前r/e，不恢复全部旧屏幕。超过120000字符或大矩阵明确裁剪。后估计依赖适用模型，错误不会混入旧估计。学生无需PyStata或额外API SDK；测试宿主关闭异步输出。在线安装方法见INSTALL.md。接口依据：[SFI](https://www.stata.com/python/api18/SFIToolkit.html)、[net安装](https://www.stata.com/manuals/rnet.pdf)。
