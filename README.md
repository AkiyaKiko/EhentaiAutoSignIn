# E-Hentai Auto Sign In

## 目录 | Table of Contents
- [中文说明](#中文说明)
- [English Version](#english-version)

## 中文说明

一个用于自动签到 [E-Hentai](https://e-hentai.org) 的 Python 脚本。

请使用青龙面板运行，如需在物理机上运行，则需要自己配置环境变量和通知模块（请前往[青龙面板](https://github.com/whyour/qinglong/blob/develop/sample/notify.py)项目自行下载 `notify.py` 文件）。

## 功能

- 自动访问 E-Hentai 的新闻页面并检查签到状态。
- 支持通过环境变量配置代理、Cookie 和 User-Agent。
- 使用 [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) 解析 HTML。
- 支持通过通知模块发送签到结果。

## 环境变量

以下环境变量可用于配置脚本：

- `E_PROXY`：HTTP/HTTPS 代理地址（可选）。例如：```http://127.0.0.1:8080```
- `E_COOKIE`：用于访问 E-Hentai 的 Cookie（必需）。```Cookie 建议全部复制进去```
- `E_USER_AGENT`：自定义的 User-Agent（可选）。

#### **|** 如何获取E-Hentai Cookie<br>
`F12` 打开 “开发者控制台”<br>
切换到 `Console` Tab，输入 `document.cookie`<br>
复制所有内容到青龙面板的环境变量中（如不使用青龙面板参考下文使用方法），Cookie 格式参考上文

## 使用和安装方法


### 依赖安装说明

**物理机用户：** 

**需要自己下载notify.py文件，请前往[青龙面板](https://github.com/whyour/qinglong/blob/develop/sample/notify.py)**

推荐使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理，或直接使用 pip 安装。

使用 uv 创建虚拟环境（本项目默认使用 Python 3.10）：
```pwsh
uv venv
```
使用 uv 安装依赖：
```pwsh
uv sync
```
**或者使用pip手动安装依赖：**

使用 pip 安装依赖：
```pwsh
pip install bs4 requests urllib3
```

**青龙面板用户：**
请在面板依赖管理中手动添加以下依赖：
```
bs4>=0.0.2
requests>=2.32.4
urllib3>=2.5.0
```

<br />

### 使用说明
**1. 青龙面板用户:**
   - 订阅管理中拉取本仓库（可以设置定时更新仓库）`https://github.com/AkiyaKiko/EhentaiAutoSignIn.git` 分支选择 `main` 分支，推荐每周更新一次。
   - 自动任务默认为每天凌晨0点01分运行签到，每6小时检测一次（可以在面板手动更改，或者 fork 本项目并自行修改 Python 文件头部注释块）。
   - 注意！一定要在创建订阅时设置文件后缀，填写 `py`，依赖文件可以填入 `notify.py`。否则可能会将仓库中的其他文件拉取到本地！

<br />

**2. Linux 物理机用户：**
   - **设置环境变量**：
     1. 打开终端，使用以下命令导入环境变量：
        ```bash
        export E_PROXY="你的代理" # 可选
        export E_COOKIE="你的 Cookie" # 必需
        export E_USER_AGENT="自定义的 User-Agent" # 可选
        ```
     2. 如果需要让环境变量在每次启动时自动加载，可以将上述命令添加到 `~/.bashrc` 或 `~/.zshrc` 文件中：
        ```bash
        echo 'export E_PROXY="你的代理"' >> ~/.bashrc
        echo 'export E_COOKIE="你的 Cookie"' >> ~/.bashrc
        echo 'export E_USER_AGENT="你的 User-Agent"' >> ~/.bashrc
        ```
        然后运行以下命令使更改生效：
        ```bash
        source ~/.bashrc
        ```
   - **设置定时规则**：
     1. 使用 `crontab -e` 编辑定时任务。
     2. 添加如下内容：
        ```
        0 8 * * * python3 /path/to/main.py
        ```
        上述示例表示每天早上 8 点运行脚本。
     3. 保存并退出后，可以使用以下命令查看定时任务是否已正确添加：
        ```bash
        crontab -l
        ```

<br />

**3. Windows 物理机用户：**
   - **设置环境变量**：
     1. 点击 `开始` 菜单，搜索 “环境变量”，选择 “编辑系统环境变量”。
     2. 在弹出的窗口中，点击 “环境变量” 按钮。
     3. 在 “系统变量” 或 “用户变量” 中，点击 “新建”，添加上述变量。
     4. 点击 “确定” 保存所有更改。
   - **设置定时任务**：
     1. 打开 `任务计划程序`，点击右侧的 “创建任务”。
     2. 在 “常规” 选项卡中，填写任务名称，例如 `E-Hentai SignIn`。
     3. 在 “触发器” 选项卡中，点击 “新建”，设置触发器为每天运行，时间为你希望的签到时间，例如每天早上 8 点。
     4. 在 “操作” 选项卡中，点击 “新建”，操作类型选择 “启动程序”，程序或脚本填写 `python`，添加参数填写脚本路径，例如：
        ```
        "C:\path\to\main.py"
        ```
     5. 点击 “确定” 保存任务。
     6. 确保任务计划程序服务正在运行，并测试任务是否正常执行。

## TODO

   1. 论坛水贴？
   2. *~~自动处理 Encounter?~~* Encounter 似乎有人机验证 :(

## 关于E-Hentai Cookie
如果你是青龙面板的玩家，经常挂一些自动签到等脚本的话，相信你一定很熟悉对 `Cookie` 的操作。

根据我的推断：`ipb_member_id` 和 `ipb_pass_hash` 字段几乎不会变，或者说很少改变。他们代表一个用户的唯一信息。如果你在使用一些第三方的 E-Hentai 的客户端时应该会发现它们都会要求你填写或者自动抓取这两个字段，因为它们决定了你在站点上的唯一身份。当然也是通过这两个字段来校验你是否有资格进入 Ex-Hentai 非公开站点。

`sk` 字段似乎代表这一个 `Session Key` 用来维持临时会话或短期鉴权，根据我的测试，这也是判断一个用户是否有资格进入 Ex 的标准之一。

`hath_perks` 是与 H@H 有关。

`nw` 应该与社区活动或者公告等有关系。

`event` 在每次会话的一段时间后会更改，也是最频繁的更改。我的猜测是用于维持不同的 Session？(~~毕竟是用 PHP 写的~~。:P)

---

## English Version

# E-Hentai Auto Sign In

A Python script for automatic sign-in to [E-Hentai](https://e-hentai.org).

Please use Qinglong Panel to run. If you want to run on a physical machine, you need to configure environment variables and notification module yourself (download `notify.py` from the [Qinglong Panel](https://github.com/whyour/qinglong/blob/develop/sample/notify.py) project).

## Features

- Automatically visit E-Hentai news page and check sign-in status.
- Support configuration of proxy, Cookie, and User-Agent via environment variables.
- Parse HTML using [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/).
- Send sign-in results via notification module.

## Environment Variables

The following environment variables can be used to configure the script:

- `E_PROXY`: HTTP/HTTPS proxy address (optional). Example: `http://127.0.0.1:8080`
- `E_COOKIE`: Cookie for accessing E-Hentai (required). *Copy all cookie content*
- `E_USER_AGENT`: Custom User-Agent (optional).

#### **|** How to get E-Hentai Cookie<br>
Open "Developer Console" with `F12`<br>
Switch to `Console` Tab, enter `document.cookie`<br>
Copy all content to Qinglong Panel's environment variable (or refer to usage below if not using Qinglong Panel). Cookie format as above.

## Usage & Installation

### Dependency Installation

**Physical Machine Users:**

**You need to download notify.py yourself from [Qinglong Panel](https://github.com/whyour/qinglong/blob/develop/sample/notify.py)**

Recommended to use [uv](https://github.com/astral-sh/uv) for dependency management, or install via pip.

Create virtual environment with uv (Python 3.10 recommended):
```pwsh
uv venv
```
Install dependencies with uv:
```pwsh
uv sync
```
**Or manually install dependencies with pip:**

Install dependencies with pip:
```pwsh
pip install bs4 requests urllib3
```

**Qinglong Panel Users:**
Manually add the following dependencies in panel:
```
bs4>=0.0.2
requests>=2.32.4
urllib3>=2.5.0
```

<br />

### Usage

**1. Qinglong Panel Users:**
   - Subscribe to this repo in subscription management (`https://github.com/AkiyaKiko/EhentaiAutoSignIn.git`), select `main` branch, recommended to update weekly.
   - Default scheduled task runs at 00:01 daily, checks every 6 hours (can be changed in panel or by editing Python file header).
   - Note! Set file suffix to `py` when creating subscription, and add `notify.py` as dependency file. Otherwise, other files may be pulled locally!

<br />

**2. Linux Physical Machine Users:**
   - **Set environment variables:**
     1. Open terminal, import variables:
        ```bash
        export E_PROXY="your proxy" # optional
        export E_COOKIE="your Cookie" # required
        export E_USER_AGENT="your User-Agent" # optional
        ```
     2. To auto-load on startup, add above to `~/.bashrc` or `~/.zshrc`:
        ```bash
        echo 'export E_PROXY="your proxy"' >> ~/.bashrc
        echo 'export E_COOKIE="your Cookie"' >> ~/.bashrc
        echo 'export E_USER_AGENT="your User-Agent"' >> ~/.bashrc
        ```
        Then apply changes:
        ```bash
        source ~/.bashrc
        ```
   - **Set schedule:**
     1. Edit scheduled tasks with `crontab -e`.
     2. Add:
        ```
        0 8 * * * python3 /path/to/main.py
        ```
        This runs script at 8am daily.
     3. Check tasks:
        ```bash
        crontab -l
        ```

<br />

**3. Windows Physical Machine Users:**
   - **Set environment variables:**
     1. Click `Start`, search "Environment Variables", select "Edit system environment variables".
     2. In popup, click "Environment Variables".
     3. In "System variables" or "User variables", click "New" to add above variables.
     4. Click "OK" to save.
   - **Set scheduled task:**
     1. Open `Task Scheduler`, click "Create Task".
     2. In "General", name the task, e.g. `E-Hentai SignIn`.
     3. In "Triggers", click "New", set to run daily at your preferred time, e.g. 8am.
     4. In "Actions", click "New", select "Start a program", program/script: `python`, add argument: script path, e.g.:
        ```
        "C:\path\to\main.py"
        ```
     5. Click "OK" to save.
     6. Ensure Task Scheduler service is running and test the task.

## TODO

   1. Forum post?
   2. *~~Auto handle Encounter?~~* Encounter seems to have human verification :(

## About E-Hentai Cookie
If you use Qinglong Panel and run auto sign-in scripts, you should be familiar with `Cookie` operations.

Based on my observation: `ipb_member_id` and `ipb_pass_hash` rarely change and represent unique user info. Many third-party E-Hentai clients require these fields, as they determine your identity and access to Ex-Hentai.

`sk` seems to be a Session Key for temporary authentication, also used to check Ex-Hentai access.

`hath_perks` relates to H@H.

`nw` may relate to community activity or announcements.

`event` changes frequently during sessions, likely for session maintenance (~~E-Hentai uses PHP~~ :P).