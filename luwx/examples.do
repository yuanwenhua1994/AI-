* luwx 5.0.0：一次提问、一条代码、一个结果。
* 先安装并配置Stata内Python。每位学生使用自己的密钥。
* 仓库文件发布后首次安装：net install luwx, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx) replace
* 旧版先which检查；PERSONAL旧文件会遮挡PLUS，可用本包install.do覆盖并重启。
* luweixiao为兼容转发别名；已有本机API设置可沿用，建议以后使用luwx。
version 18
set more off

* 密钥会留在do-file/log中；替换后不要公开或转发本文件。
* luwx config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)

* 配置好自己的API后，逐段运行以下例子。
* luwx bcuse是什么意思？

sysuse auto, clear
* check只审查，不执行；run实际执行并记录输出。
* luwx check regress price mpg weight, vce(robust)
* luwx run regress price mpg weight, vce(robust)
* luwx explain mpg的系数和置信区间怎么理解？
* luwx run estat vif

* 完整记录多变量统计，便于结果对应。
* luwx run summarize price mpg weight foreign
* luwx explain foreign的均值为什么表示比例？

* 自己先运行普通Stata命令也可explain，但只能读取当前r()/e()。
* regress price mpg weight, vce(robust)
* luwx explain

* 面板先声明结构，再估计。id/year/y/x换为实际变量。
* luwx run xtset id year
* luwx run xtreg y x, fe

* 生存数据：time/event/x换为自己数据中的时间、事件和解释变量。
* stset会按原Stata规则更新声明和生存辅助变量。
* luwx run stset time, failure(event)
* luwx run stcox x
* luwx explain 这个风险比应该如何理解？

* 可选资料搜索：不需要API；先自行安装要用的命令，不自动安装。
* ssc install lianxh
* ssc install insheetjson
* ssc install libjson
* luwx find DID
* luwx find lianxh 控制变量
* ssc install songbl
* luwx find songbl 面板
* 返回的是资料标题/链接；点击自行阅读，不代表AI已经读过全文。
