# E-Hentai Auto Sign In

[中文说明](README.md)

> **Using Qinglong Panel?** See the [legacy Qinglong deployment guide](README.qinglong.md) (Chinese). The legacy script is no longer maintained; standalone deployment is recommended.

Automatically visits the E-Hentai news page to sign in. Supports scheduled sign-ins, Cookie updates, and notifications. The executable does not require Python to be installed.

## Quick start

1. **Download the latest binary archive.** Go to the [latest GitHub release](https://github.com/AkiyaKiko/EhentaiAutoSignIn/releases/latest)
2. **Rename `.env.example` to `.env`.** Keep it in the same directory as the executable.
3. **Fill in `.env`.** Open it in a text editor and configure the values, for example:

   ```dotenv
   E_COOKIE='ipb_member_id=YOUR_MEMBER_ID; ipb_pass_hash=YOUR_PASS_HASH; event=111'
   E_PROXY=''
   E_USER_AGENT=''
   Notify=''
   E_SCHEDULE='00:30,12:30'
   ```

   - `E_COOKIE` is required. Copying the complete Cookie sent by your browser is recommended. It must include an `event` field, whose value can be any number. When the server updates supported Cookie fields, the program writes the changes back to `.env`.
   - `E_PROXY` is optional. HTTP, HTTPS, SOCKS4, and SOCKS5 are supported. For example, use `http://127.0.0.1:7890` for an HTTP proxy or `socks5h://127.0.0.1:1080` for SOCKS5. Addresses beginning with `socks4a://` or `socks5h://` resolve domain names through the proxy.
   - `E_USER_AGENT` is optional; an empty value uses the default.
   - `Notify` can be empty or `{}` to disable notifications. See the section below for configuration.
   - `E_SCHEDULE` is a comma-separated list of 24-hour times. If empty, it defaults to 00:30 and 12:30 every day, using the system's local time.

   Values in `.env` take precedence over matching system environment variables. Keep the program directory writable, and keep your Cookie and notification tokens private.
4. **Run the executable.** Open a terminal in the extracted directory and run:

   ```powershell
   # Windows PowerShell
   .\EhentaiAutoSignIn.exe
   ```

   ```bash
   # Linux / macOS
   ./EhentaiAutoSignIn
   ```

   On Linux / macOS, run `chmod +x EhentaiAutoSignIn` first if you encounter a permission error. Add `--once` to sign in immediately and exit.

The program signs in once at startup, then continues according to the configured schedule. Keep the process running for scheduled sign-ins, and restart it after changing the schedule. Updated Cookies and the default `logs` directory are stored alongside the executable.

Release archives do not contain `.env`, logs, or directory entries. File permissions and ZIP metadata are checked before publishing. The Linux release workflow also tests extraction as a regular user and as root in isolated directories, verifying that existing configuration, logs, and destination directory permissions and ownership remain unchanged.

## Notifications

`Notify` is a single-line JSON object. For example, to use Gotify:

```dotenv
Notify='{"GOTIFY_URL":"https://gotify.example.com","GOTIFY_TOKEN":"YOUR_APP_TOKEN","GOTIFY_PRIORITY":5}'
```

To use Gotify and Telegram together, put all fields on the same line:

```dotenv
Notify='{"GOTIFY_URL":"https://gotify.example.com","GOTIFY_TOKEN":"YOUR_APP_TOKEN","GOTIFY_PRIORITY":5,"TG_BOT_TOKEN":"YOUR_BOT_TOKEN","TG_USER_ID":"YOUR_USER_ID"}'
```

The program concurrently attempts to send each message to every channel whose required fields are nonempty. Complete configuration does not guarantee delivery. Channel output and thread errors mainly appear in the console, and some requests do not have a timeout. `E_PROXY` applies to sign-in requests; notification channels use their own settings or system proxies.

This project directly reuses the unmodified [`notify.py` maintained by the Qinglong repository](https://github.com/whyour/qinglong/blob/develop/sample/notify.py). See `push_config` and `add_notify_function()` in [notify.py](notify.py) for other channels and their activation requirements. The project's `Notify` value replaces that module's default channel configuration. Hitokoto is disabled by default; set `"HITOKOTO":true` to enable it, but a failed Hitokoto request may prevent that notification from being sent.

## Local logs

File logging is disabled by default. To enable it, add the following to `.env`:

```dotenv
LOG_ENABLED='true'
LOG_DIR='logs'
LOG_MAX_MB='5'
LOG_RETENTION_DAYS='30'
```

By default, logs are written to `logs/ehentai.log` in the program directory. Files rotate when they reach 5 MiB or when the first message is written after midnight, with up to 30 backups. Expired backups are cleaned at startup, during rotation, or on a later log write; restart the program after changing these settings. Console output remains enabled, and independent prints from `notify.py` are not written to the log file.

## TLS compatibility

In commit `c00c3d4`, the old Qinglong script added a TLS 1.2 fallback for a reported conflict between system OpenSSL and a Reality proxy with XTLS flow enabled: after three failed attempts with default TLS, it tried up to three more times with TLS forced to 1.2, waiting two seconds between attempts. The standalone version removes this fallback and uses the runtime's default TLS and certificate verification, with up to three attempts on failure. The old `autosignin.py` retains the original behavior.

## Running from source (optional)

Install Python 3.12 or later, then create and activate a virtual environment in the project directory:

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

Install the dependencies, rename `.env.example` to `.env`, fill it in as described above, and run:

```bash
python -m pip install .
python main.py
```

Source execution also supports `python main.py --once`. The old `autosignin.py` is retained for Qinglong Panel compatibility and is no longer maintained.
