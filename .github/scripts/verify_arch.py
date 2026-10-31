"""检查构建用 Python 的操作系统和架构与发布包名称一致。"""
import platform
import sys
import sysconfig


def main(target):
    platform_name, architecture = target.split('-', 1)
    expected_system = {'windows': 'win32', 'linux': 'linux', 'macos': 'darwin'}[platform_name]
    if sys.platform != expected_system:
        raise SystemExit(f'预期系统 {expected_system}，实际系统 {sys.platform}')

    if platform_name == 'windows':
        actual = {'win-amd64': 'x64', 'win-arm64': 'arm64'}.get(sysconfig.get_platform().lower())
    else:
        actual = {'x86_64': 'x64', 'amd64': 'x64', 'aarch64': 'arm64',
                  'arm64': 'arm64'}.get(platform.machine().lower())
    if actual != architecture:
        raise SystemExit(f'预期架构 {architecture}，实际架构 {actual or platform.machine()}')
    print(f'构建目标已验证: {target}')


if __name__ == '__main__':
    main(sys.argv[1])
