# 安装 luweixiao 4.0

## 本地安装

下载并解压完整ZIP，进入实际解压目录：

```stata
cd "D:/StataTools/luweixiao-v4"
do install.do
which luweixiao
python query
```

如果PERSONAL不可写，先建立自己的文件夹，再安装：

```stata
capture mkdir "C:/Users/你的用户名/Documents/stata-ado"
sysdir set PERSONAL "C:/Users/你的用户名/Documents/stata-ado"
do install.do
```

路径中的用户名需替换。`sysdir set`只影响当前会话，以后可再次设置或写入自己的profile.do。无需管理员权限。也可以从解压目录运行 `net install luweixiao, from("D:/StataTools/luweixiao-v4") replace`，前提是PLUS可写。

手工安装时，将6个文件一起复制到可写PERSONAL目录：luweixiao.ado、luweixiao.sthlp、luweixiao_api.py、luweixiao_bridge.py、luweixiao_settings.py、luweixiao_evidence.py。不要只复制ado；以本包install.do/pkg清单为准。

## 配置 Stata 内的 Python

`shell python --version`不代表Stata内Python已配置。若 `python query`显示未配置，先运行 `python search`，再选择自己电脑实际存在的64位解释器：

```stata
python set exec "C:/Users/你的用户名/AppData/Local/Programs/Python/Python312/python.exe", permanently
```

路径仅为示例。设置后重启Stata，再运行 `python query`。更新命令文件后也重启，以便加载新程序和模块。无需cURL、旧chatgpt插件或额外Python API SDK。

## 设置自己的 API

```stata
luweixiao config, key(自己的密钥) baseurl(https://discovery-api.intern-ai.org.cn/v1) model(glm-5.3) protocol(openai)
luweixiao config
luweixiao 用一句话解释summarize。
```

替换为本人申请的密钥。`config`不带选项只显示当前设置，并隐藏密钥；带选项保存一个当前设置。切换其他平台时填该平台实际地址、模型和协议 `openai`、`anthropic` 或 `gemini`。免密钥本地兼容服务可用 `auth(none)`。供应商私有接口不一定兼容。

配置和对话保存在PERSONAL/luweixiao_state，输入的config命令也可能留在do-file和日志里。教师发学生只发安装包，不分发自己的配置、日志、密钥或对话。调用API会发送本轮问题、代码、相关数据结构和结果；学生应使用适合上传的材料。

## 在线安装和更新

仓库文件发布后，首次安装且PLUS可写的学生可使用：

```stata
net install luweixiao, from(https://raw.githubusercontent.com/yuanwenhua1994/AI-/main/luweixiao) replace
which luweixiao
```

源码与完整 `luweixiao-stata-v4.zip` 的发布目标是 [GitHub目录](https://github.com/yuanwenhua1994/AI-/tree/main/luweixiao)。以成功推送后的文件为准。

旧用户先 `which luweixiao` 检查位置：PERSONAL中的旧版会遮挡PLUS新安装。若旧版在PERSONAL，解压本包、重跑install.do覆盖原PERSONAL并重启即可；不要混用不同版本的配套Python文件。报错先核对 `which luweixiao`、`python query`和自己的API权限/额度。API失败不删除 `run`已完成的本机结果，可修正设置后再 `luweixiao explain`。
