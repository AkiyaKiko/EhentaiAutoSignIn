"""读取本地配置、保存 Cookie 和解析签到时间。"""
import json
import os
from pathlib import Path
import re
import sys
import tempfile


def application_dir():
    """优先使用指定的数据目录，否则使用源码或可执行文件所在目录。"""
    data_dir = os.getenv('EHENTAI_DATA_DIR', '').strip()
    if data_dir:
        return Path(data_dir).expanduser().resolve()
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


ENV_PATH = application_dir() / '.env'
DEFAULT_SCHEDULE = ('00:30', '06:30', '12:30', '18:30')


def read_env(path=ENV_PATH, *, keys=None):
    """读取 .env；指定 keys 时只解析所需配置，供日志提前初始化。"""
    values = {}
    if not path.exists():
        return values
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].lstrip()
        key, separator, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if keys is not None and key not in keys:
            continue
        if not separator or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
            raise ValueError(f'.env 第 {number} 行格式无效')
        if value.startswith('"'):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f'.env 第 {number} 行的双引号值无效') from exc
            if not isinstance(value, str):
                raise ValueError(f'.env 第 {number} 行必须是字符串')
        elif value.startswith("'"):
            if not value.endswith("'") or len(value) < 2:
                raise ValueError(f'.env 第 {number} 行的单引号未闭合')
            value = value[1:-1]
        values[key] = value
    return values


def save_cookie(cookie, path=ENV_PATH):
    """原子替换 .env 中的 E_COOKIE，同时保留其他配置和注释。"""
    lines = path.read_text(encoding='utf-8-sig').splitlines(keepends=True) if path.exists() else []
    replacement = 'E_COOKIE=' + json.dumps(cookie, ensure_ascii=False) + '\n'
    found = False
    for index, line in enumerate(lines):
        if re.match(r'^\s*(?:export\s+)?E_COOKIE\s*=', line):
            lines[index] = replacement
            found = True
    if not found:
        if lines and not lines[-1].endswith(('\n', '\r')):
            lines[-1] += '\n'
        lines.append(replacement)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, delete=False) as output:
            temporary = Path(output.name)
            output.writelines(lines)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def scheduled_times():
    """读取每天执行的本地时间，缺省时每天执行四次。"""
    value = read_env().get('E_SCHEDULE', os.getenv('E_SCHEDULE', ''))
    if not value.strip():
        return DEFAULT_SCHEDULE

    times = []
    seen = set()
    for item in value.split(','):
        item = item.strip()
        if not re.fullmatch(r'(?:[0-9]|[01][0-9]|2[0-3]):[0-5][0-9]', item):
            raise ValueError('E_SCHEDULE 格式无效，请使用逗号分隔的 24 小时制时间，例如 00:30,6:30。')
        hour, minute = item.split(':')
        normalized = f'{int(hour):02d}:{minute}'
        if normalized in seen:
            continue
        if times and normalized < times[-1]:
            raise ValueError('E_SCHEDULE 时间必须按从早到晚的顺序排列。')
        seen.add(normalized)
        times.append(normalized)
    return tuple(times)
