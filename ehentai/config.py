"""读取本地配置、保存 Cookie 和解析签到时间。"""
import json
import os
from pathlib import Path
import re
import tempfile

# 无论从哪个目录启动，都使用项目目录中的 .env。
ENV_PATH = Path(__file__).resolve().parent.parent / '.env'
DEFAULT_SCHEDULE = ('00:30', '12:30')


def read_env(path=ENV_PATH):
    """读取项目的 .env；支持未引用值、单引号和 JSON 风格的双引号。"""
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
    """读取每天执行的本地时间，缺省时每天执行两次。"""
    value = read_env().get('E_SCHEDULE', os.getenv('E_SCHEDULE', ''))
    if not value.strip():
        return DEFAULT_SCHEDULE

    times = [item.strip() for item in value.split(',')]
    for item in times:
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d', item):
            raise ValueError('E_SCHEDULE 格式无效，请使用逗号分隔的 24 小时制时间，例如 00:30,12:30。')
    if len(times) != len(set(times)):
        raise ValueError('E_SCHEDULE 不能包含重复的时间。')
    return tuple(times)
