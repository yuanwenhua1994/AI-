# 安装 luwx 5.0

## 本地安装

下载并解压完整ZIP，进入实际解压目录：

```stata
cd "D:/StataTools/luwx-v5"
do install.do
which luwx
python query
```

如果PERSONAL不可写，先建立自己的文件夹，再安装：

```stata
capture mkdir "C:/Users/你的用户名/Documents/stata-ado"
sysdir set PERSONAL "C:/Users/你的用户名/Documents/stata-ado"
do install.do
```

路径中的用户名需替换。`sysdir set`只影响当前会话，以后可再次设置或写入自己的profile.do。无需管理员权限。也可以从解压目录运行 `net install luwx, from("D:/StataTools/luwx-v5") replace`，前提是PLUS可写。

手工安装时，将8个文件一起复制到可写PERSONAL目录：luwx.ado、luwx.sthlp、luwx_api.py、luwx_bridge.py、luwx_settings.py、luwx_evidence.py、luweixiao.ado、luweixiao.sthlp。以本包install.do/pkg清单为准；不要只复制ado，也不要混用不同版本的文件。

## 配置 Stata 内的 Python

`shell python --version`不代表Stata内Python已配置。若 `python query`显示未配置，先运行 `python search`，再选择自己电脑实际存在的64位解释器：

```stata
python set exec "C:/Users/你的用户名/AppData/Local/Programs/Python/Python312/python.exe", permanently
```

路径仅为示例。设置后重启Stata，再运行 `python query`。更新命令文件后也重启，以便加载新程序和模块。无需cURL、旧chatgpt插件或额外Python API SDK。

## 设置自己的 API

```stata
luwx config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)
luwx config
luwx 用一句话解释summarize。
```

替换为本人申请的密钥。`config`不带选项只显示当前设置，并隐藏密钥；带选项保存一个当前设置。切换其他平台时填该平台实际地址、模型和协议 `openai`、`anthropic` 或 `gemini`。免密钥本地兼容服务可用 `auth(none)`。供应商私有接口不一定兼容。

配置和对话保存在PERSONAL/luwx_state，输入的config命令也可能留在do-file和日志里。教师发学生只发安装包，不分发自己的配置、日志、密钥或对话。调用API会发送本轮问题、代码、相关数据结构和结果；学生应使用适合上传的材料。

## 可选：搜索教程和资料

只需要AI问答或分析，可以跳过此步骤。需要`luwx find`时，自行选择安装；插件不会替学生安装依赖：

```stata
* 连享会检索及其索引读取依赖。
ssc install lianxh
ssc install insheetjson
ssc install libjson
luwx find DID

* 可选的另一来源。
ssc install songbl
luwx find songbl 面板
```

资料列表由原命令显示，点击链接自行阅读；不会自动读取全文或发送给AI。上游服务或网络失败会明确报错并恢复数据/结果，可改用另一来源。songbl可能提示更新，按作者说明自行决定。缓存权限报错时检查PLUS是否可写。更多原用法见 `help lianxh`、`help songbl_cn`，以及[连享会作者仓库](https://github.com/arlionn/lianxh)和[songbl SSC条目](https://ideas.repec.org/c/boc/bocode/s458919.html)。

## 在线安装和更新

首次安装且PLUS可写的学生可使用：

```stata
net install luwx, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx) replace
which luwx
```

如果上述命令返回r(603)且GitHub网页可打开，先确认Stata内Python已配置，再在Stata执行这个备用在线安装命令：

```stata
python: exec(__import__("urllib.request", fromlist=["urlopen"]).urlopen("https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luwx/install_online.py", timeout=30).read().decode("utf-8"))
```

它用Python下载本仓库文件、核对清单哈希，再交给本机Stata安装；不改网络设置，不包含API密钥。安装后重启Stata；以后更新可重新执行相同安装命令。若PLUS不可写，可先建自己的目录并设置`sysdir set PLUS "C:/Users/你的用户名/Documents/stata-plus"`；PERSONAL也需可写，见本地安装部分。目录设置仅影响当前会话，后续需保留自己的路径设置。

源码与完整 `luwx-stata-v5.zip` 位于 [GitHub目录](https://github.com/yuanwenhua1994/AI-/tree/main/luwx)。

旧命令`luweixiao`作为转发别名继续可用，推荐以后写`luwx`。若luwx尚无API设置，会迁移本机已有luweixiao配置；旧对话和分析记录不迁移。学生仍须使用自己的密钥，不复制教师状态目录。

旧用户先 `which luwx`、`which luweixiao` 检查位置：PERSONAL旧文件会遮挡PLUS新安装。解压本包、重跑install.do覆盖原PERSONAL并重启即可。报错先核对 `which luwx`、`python query`和自己的API权限/额度。API失败不删除 `run`已完成的本机结果，可修正设置后再 `luwx explain`。
