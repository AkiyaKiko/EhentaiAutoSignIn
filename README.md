# E-Hentai Auto Sign In

一个用于自动签到 [E-Hentai](https://e-hentai.org) 的 Python 脚本。

请使用青龙面板运行，如需在物理机上运行，则需要自己配置环境变量和通知模块（本项目中的 `notify.py` 引用自[青龙面板](https://github.com/whyour/qinglong)项目，如有需要请自行前往更新）。

## 功能

- 自动访问 E-Hentai 的新闻页面并检查签到状态。
- 支持通过环境变量配置代理、Cookie 和 User-Agent。
- 使用 [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) 解析 HTML。
- 支持通过通知模块发送签到结果。

## 环境变量

以下环境变量可用于配置脚本：

- `E_PROXY`：HTTP/HTTPS 代理地址（可选）。例如：```http://127.0.0.1:8080```
- `E_COOKIE`：用于访问 E-Hentai 的 Cookie（必需）。例如：```ipb_member_id=123zxc;ipb_pass_hash=123abc```
- `E_USER_AGENT`：自定义的 User-Agent（可选）。

#### **|** 如何获取E-Hentai Cookie<br>
`F12` 打开 “开发者控制台”<br>
切换到 `Console` Tab，输入 `document.cookie`<br>
只复制 `ipb_member_id` 和 `ipb_pass_hash` 的内容到青龙面板的环境变量中（如不使用青龙面板参考下文使用方法），Cookie 格式参考上文

## 使用方法
1. 青龙面板用户，订阅管理中拉取本仓库（可以设置定时更新仓库），自动任务默认为每天凌晨0点01分运行签到（可以在面板手动更改，或者 fork 本项目并自行修改 Python 文件头部注释块）。<br>
2. Linux 物理机用户：
   - **设置环境变量**：
     1. 打开终端，使用以下命令导入环境变量：
        ```bash
        export E_PROXY="http://127.0.0.1:8080" # 可选
        export E_COOKIE="ipb_member_id=123zxc;ipb_pass_hash=123abc" # 必需
        export E_USER_AGENT="自定义的 User-Agent" # 可选
        ```
     2. 如果需要让环境变量在每次启动时自动加载，可以将上述命令添加到 `~/.bashrc` 或 `~/.zshrc` 文件中：
        ```bash
        echo 'export E_PROXY="http://127.0.0.1:8080"' >> ~/.bashrc
        echo 'export E_COOKIE="ipb_member_id=123zxc;ipb_pass_hash=123abc"' >> ~/.bashrc
        echo 'export E_USER_AGENT="自定义的 User-Agent"' >> ~/.bashrc
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
        <br>

3. Windows 物理机用户：
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