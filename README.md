# E-Hentai Auto Sign In

[English Version](README.en.md)

> **仍在使用青龙面板？** 请查看[旧版青龙面板部署教程](README.qinglong.md)。旧版脚本不再维护，建议迁移至单机部署。

自动访问 E-Hentai 新闻页面，支持定时签到、Cookie 更新和消息通知。可执行文件无需安装 Python。

## 快速开始

1. **下载最新的二进制压缩包。** 前往 [GitHub Releases 最新版本](https://github.com/AkiyaKiko/EhentaiAutoSignIn/releases/latest)
2. **将 `.env.example` 重命名为 `.env`。** 保持它与可执行文件在同一个目录中。
3. **填写 `.env` 配置。** 使用文本编辑器打开 `.env`，按照其中的注释填写，例如：

   ```dotenv
   E_COOKIE='ipb_member_id=会员ID; ipb_pass_hash=密码哈希; event=111'
   E_PROXY=''
   E_USER_AGENT=''
   Notify=''
   E_SCHEDULE='00:30,06:30,12:30,18:30'
   ```

   - `E_COOKIE` 必填，建议复制浏览器发送的完整 Cookie；必须包含 `event` 字段，值可以是任意数字。服务端更新受支持的 Cookie 时，程序会自动写回 `.env`。
   - `E_PROXY` 可留空，支持 HTTP、HTTPS、SOCKS4 和 SOCKS5；带 `socks4a://` 或 `socks5h://` 的地址通过代理解析域名。具体样例见 `.env` 注释。
   - `E_USER_AGENT` 可留空，留空时使用默认值。
   - `Notify` 可留空或填 `{}` 关闭通知；配置方法见下文。
   - `E_SCHEDULE` 为逗号分隔的 24 小时时间，可任意设置数量，例如 `00:30,6:30,11:11,12:30,18:30`。时间必须从早到晚排列，重复时间会自动去重；留空时默认每天 00:30、06:30、12:30 和 18:30，按系统本地时间运行。

   `.env` 中的配置优先于同名系统环境变量。请保持程序目录可写，并妥善保管 Cookie 和通知 Token。
4. **执行可执行文件。** 在解压目录打开终端，运行：

   ```powershell
   # Windows PowerShell
   .\EhentaiAutoSignIn.exe
   ```

   ```bash
   # Linux / macOS
   ./EhentaiAutoSignIn
   ```

   Linux / macOS 如遇执行权限问题，可先运行 `chmod +x EhentaiAutoSignIn`。添加 `--once` 可立即签到一次并退出。

程序启动后立即签到一次，然后按配置时间继续执行。定时模式需要保持进程运行；修改定时配置后需重启。Cookie 更新和默认的 `logs` 目录位于可执行文件所在目录。

配置或签到发生无法继续的错误时，程序会输出错误并以非零状态退出；开启文件日志后也会记录启动和运行错误。如果配置的日志目录不可用，程序会尝试将错误写入默认的 `logs` 目录。

发布包不包含 `.env`、日志或目录条目；文件权限和 ZIP 元数据会在发布前校验。Linux 发布流程会在隔离目录中验证普通用户及 root 解压，确保目标目录和已有配置、日志的权限与属主不变。

## Docker 部署

镜像支持 Linux amd64 和 arm64。以下以 Linux 为例，先在包含 `.env.example` 的目录中准备配置：

```bash
mkdir -p data
cp .env.example data/.env
# 编辑 data/.env，填写 Cookie 等配置
```

使用 Docker 启动：

```bash
docker run -d --name ehentai-signin \
  --user "$(id -u):$(id -g)" \
  -e TZ=Asia/Shanghai \
  -v "$(pwd)/data:/data" \
  ghcr.io/akiyakiko/ehentaiautosignin:latest
docker logs -f ehentai-signin
```

或者，在同一目录创建 `compose.yaml`，使用 Docker Compose 启动：

```yaml
services:
  ehentai-signin:
    image: ghcr.io/akiyakiko/ehentaiautosignin:latest
    restart: unless-stopped
    user: "1000:1000"
    environment:
      TZ: Asia/Shanghai
    volumes:
      - ./data:/data
```

将 `user` 修改为 `id -u` 和 `id -g` 输出的宿主机用户及组 ID，然后执行：

```bash
docker compose up -d
docker compose logs -f
```

`restart: unless-stopped` 会在 Docker 服务启动时自动启动容器；请确保 Docker 服务已设置为开机启动。手动停止的容器不会自动启动。

`TZ` 决定定时签到使用的时区，不设置时容器默认使用 UTC。挂载整个 `data` 目录以保存 Cookie 更新和默认日志，确保该目录对容器用户可写；单独挂载 `.env` 文件无法支持原子更新。容器内代理地址 `127.0.0.1` 指向容器自身。也可将 `latest` 替换为版本标签，例如 `v1.2.3`。

## 消息通知

`Notify` 是单行 JSON 对象。例如，使用 Gotify：

```dotenv
Notify='{"GOTIFY_URL":"https://gotify.example.com","GOTIFY_TOKEN":"应用Token","GOTIFY_PRIORITY":5}'
```

要同时使用 Gotify 和 Telegram，可将所有字段写在同一行：

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

## 从源码运行（可选）

安装 Python 3.12 或更高版本，在项目目录创建并激活虚拟环境：

```powershell
# Windows PowerShell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

然后安装依赖，将 `.env.example` 重命名为 `.env` 并按上面的说明填写，最后运行：

```bash
python -m pip install .
python main.py
```

源码运行同样支持 `python main.py --once`。旧版 `autosignin.py` 仅保留青龙面板兼容用途，后续不再维护。
