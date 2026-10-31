# E-Hentai Auto Sign In

使用 Python 3.12 或更高版本在单机自动访问 E-Hentai 新闻页面，支持定时签到、Cookie 更新和消息通知。

旧版 `autosignin.py` 仅保留青龙面板兼容用途，后续不再维护；请迁移到 `main.py` 和本地 `.env`。

## 下载可执行文件

从 GitHub Releases 下载适合系统和架构的压缩包，解压后将 `.env.example` 复制为同目录的 `.env` 并填写配置。运行压缩包中的 `EhentaiAutoSignIn.exe`（Windows）或 `./EhentaiAutoSignIn`（Linux / macOS）；附加 `--once` 可立即签到一次并退出。Linux / macOS 如遇执行权限问题，可先运行 `chmod +x EhentaiAutoSignIn`。

可执行文件无需安装 Python，运行期间请保持终端开启；Cookie 更新和默认的 `logs` 目录位于可执行文件所在目录，请确保该目录可写。Windows、Linux 和 macOS 分别提供 x64、ARM64 版本。Linux 构建基于 Ubuntu 22.04。

发布包只包含程序、说明、配置示例、通知模块和许可证，不包含 `.env`、日志或目录条目；文件权限和 ZIP 元数据会在发布前校验。Linux 发布流程还会在隔离目录中验证普通用户及 root 解压，确保目标目录和已有配置、日志的权限与属主不变。建议先解压到独立目录，再按需更新程序。

## 安装和配置

安装 Python 3.12 或更高版本，在项目目录创建并激活虚拟环境：

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Linux / macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

激活虚拟环境后，在项目目录安装项目及其依赖：

```bash
python -m pip install .
```

将 `.env.example` 复制为 `.env`，填写自己的配置：

```dotenv
E_COOKIE='ipb_member_id=会员ID; ipb_pass_hash=密码哈希; event=111'
E_PROXY='http://127.0.0.1:7890'
E_USER_AGENT='浏览器的 User-Agent'
Notify='{"GOTIFY_URL":"https://gotify.example.com","GOTIFY_TOKEN":"应用Token","GOTIFY_PRIORITY":5}'
E_SCHEDULE='00:30,12:30'
```

- `E_COOKIE` 必填，建议复制浏览器发送的完整 Cookie；其中必须包含 `event` 字段，值可以是任意数字。服务端更新受支持的 Cookie 时，程序会自动写回程序目录的 `.env`。
- `E_PROXY` 可留空，支持 `http://`、`https://`、`socks4://`、`socks4a://`、`socks5://` 和 `socks5h://`。其中 `socks4a` 和 `socks5h` 通过代理解析域名；配置示例见 `.env.example`。
- `E_USER_AGENT` 可留空，留空时使用默认值。
- `Notify` 可留空或填 `{}` 关闭通知；推送配置见下文。
- `E_SCHEDULE` 为逗号分隔的 24 小时时间，留空时默认每天 00:30 和 12:30，按系统本地时间运行。

`.env` 中的配置优先于同名系统环境变量；请保持程序目录可写，并妥善保管 Cookie 和通知 Token。

## 运行

```bash
python main.py
```

程序启动后立即签到一次，然后按配置时间继续执行。定时模式需要进程持续运行；修改定时配置后需重启。可通过系统服务或任务计划程序在开机时启动进程，按 `Ctrl+C` 停止。

如需立即签到一次并退出：

```bash
python main.py --once
```

## 消息通知

`Notify` 是单行 JSON 对象。Gotify 示例见上方；要同时使用 Gotify 和 Telegram，可将所有字段写在同一行：

```dotenv
Notify='{"GOTIFY_URL":"https://gotify.example.com","GOTIFY_TOKEN":"应用Token","GOTIFY_PRIORITY":5,"TG_BOT_TOKEN":"机器人Token","TG_USER_ID":"用户ID"}'
```

程序会并发尝试发送到所有必要字段非空的渠道；配置完整不代表一定能发送成功。渠道结果和线程异常主要显示在控制台，部分请求没有超时。`E_PROXY` 用于签到请求，通知渠道使用自身配置或系统代理。

本项目直接复用[青龙面板仓库维护的 `notify.py`](https://github.com/whyour/qinglong/blob/develop/sample/notify.py)，未作修改。其他渠道的字段及启用条件可查看 [notify.py](notify.py) 中的 `push_config` 和 `add_notify_function()`。项目传入的 `Notify` 会替代该模块的默认渠道配置；一言默认关闭，设置 `"HITOKOTO":true` 可开启，但一言请求失败可能导致本次通知不发送。

## 本地日志

文件日志默认关闭。需要时在 `.env` 中添加：

```dotenv
LOG_ENABLED='true'
LOG_DIR='logs'
LOG_MAX_MB='5'
LOG_RETENTION_DAYS='30'
```

默认输出到程序目录的 `logs/ehentai.log`，单个文件达到 5 MiB 或跨日后写入时轮转，最多保留 30 个备份。过期备份在启动、轮转或后续写日志时清理；修改配置后需重启。控制台输出保留，`notify.py` 的独立打印不会写入日志文件。

## TLS 兼容性

旧版青龙脚本在提交 `c00c3d4` 中，为处理 Reality 代理启用 XTLS flow 时与系统 OpenSSL 的冲突，加入了 TLS 1.2 回退：默认 TLS 请求失败 3 次后，再强制 TLS 1.2 尝试 3 次，每次重试间隔 2 秒。单机版已移除回退，使用运行环境的默认 TLS 和证书验证，失败时最多尝试 3 次；旧版 `autosignin.py` 仍保留原逻辑。

## English

Create and activate a Python 3.12+ virtual environment, run `python -m pip install .` in the project directory, copy `.env.example` to `.env`, and configure `E_COOKIE` including a numeric `event` field. Run `python main.py` to sign in immediately and continue on the configured schedule, or add `--once` to run once and exit. Proxy, notification, and optional file logging settings are documented in `.env.example`.
