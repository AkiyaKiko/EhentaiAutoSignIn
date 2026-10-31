import os
from pathlib import Path
import platform
import subprocess
import sys
import sysconfig

import pytest


SCRIPT = Path(__file__).resolve().parent.parent / '.github' / 'scripts' / 'verify_arch.py'


def current_target():
    if sys.platform == 'win32':
        architecture = {'win-amd64': 'x64', 'win-arm64': 'arm64'}.get(sysconfig.get_platform().lower())
        system = 'windows'
    else:
        architecture = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64',
                        'arm64': 'arm64'}.get(platform.machine().lower())
        system = {'linux': 'linux', 'darwin': 'macos'}.get(sys.platform)
    if not architecture or not system:
        pytest.skip('当前系统或架构不在发布矩阵中')
    return system, architecture


def run_arch_check(target):
    env = os.environ.copy()
    # 模拟英文 Windows 运行器中重定向后的 CP1252 标准输出。
    env['PYTHONUTF8'] = '0'
    env['PYTHONIOENCODING'] = 'cp1252'
    return subprocess.run([sys.executable, str(SCRIPT), target], env=env, capture_output=True)


def test_arch_check_succeeds_with_cp1252_output():
    system, architecture = current_target()
    result = run_arch_check(f'{system}-{architecture}')
    assert result.returncode == 0, result.stderr
    assert b'Build target verified' in result.stdout


def test_arch_check_reports_mismatch_with_cp1252_output():
    system, architecture = current_target()
    other = 'arm64' if architecture == 'x64' else 'x64'
    result = run_arch_check(f'{system}-{other}')
    assert result.returncode != 0
    assert b'Expected architecture' in result.stderr
    assert b'UnicodeEncodeError' not in result.stderr
