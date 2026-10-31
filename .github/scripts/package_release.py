"""创建并验证 GitHub Actions 使用的安全发布包。"""
import os
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DOCUMENTS = ('README.md', '.env.example', 'LICENSE', 'notify.py')
PLATFORMS = {
    'windows-x64', 'windows-arm64', 'linux-x64', 'linux-arm64',
    'macos-x64', 'macos-arm64',
}


def expected_members(platform_name):
    """只允许六个已配置的平台及固定的顶层普通文件。"""
    if platform_name not in PLATFORMS:
        raise ValueError(f'不支持的发布平台：{platform_name}')
    exe_name = 'EhentaiAutoSignIn.exe' if platform_name.startswith('windows-') else 'EhentaiAutoSignIn'
    return {exe_name: 0o755, **{name: 0o644 for name in DOCUMENTS}}


def create_archive(root, target, platform_name):
    """显式写入文件类型和权限，不记录目录、符号链接或构建机器的属主。"""
    root, target = Path(root), Path(target)
    expected = expected_members(platform_name)
    exe_name = next(iter(expected))
    sources = {name: root / ('dist' if name == exe_name else '') / name for name in expected}
    for source in sources.values():
        if source.is_symlink() or not source.is_file():
            raise ValueError(f'发布文件必须是普通文件：{source}')
    archive = target / f'EhentaiAutoSignIn-{platform_name}.zip'
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive, 'w') as bundle:
        for name, mode in expected.items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3  # Unix 文件类型及权限，所有平台保持一致。
            info.external_attr = (stat.S_IFREG | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            with sources[name].open('rb') as source, bundle.open(info, 'w') as destination:
                shutil.copyfileobj(source, destination)
    return archive


def verify_archive(archive, platform_name):
    """发布前检查精确文件清单、权限、额外元数据和 ZIP 完整性。"""
    expected = expected_members(platform_name)
    with zipfile.ZipFile(archive) as bundle:
        members = bundle.infolist()
        names = [member.filename for member in members]
        if len(names) != len(expected) or set(names) != set(expected):
            raise ValueError(f'发布包文件清单不正确：{names}')
        for member in members:
            mode = member.external_attr >> 16
            if member.create_system != 3 or not stat.S_ISREG(mode):
                raise ValueError(f'发布包条目不是 Unix 普通文件：{member.filename}')
            if stat.S_IMODE(mode) != expected[member.filename]:
                raise ValueError(f'发布包权限不正确：{member.filename}')
            if member.extra:
                raise ValueError(f'发布包包含额外元数据：{member.filename}')
            # 本地文件头也可携带独立于中央目录的 UID/GID 元数据。
            bundle.fp.seek(member.header_offset)
            local_header = bundle.fp.read(30)
            if len(local_header) != 30:
                raise ValueError(f'发布包本地文件头不完整：{member.filename}')
            fields = struct.unpack('<4s5H3I2H', local_header)
            if fields[0] != b'PK\x03\x04' or fields[-1] != 0:
                raise ValueError(f'发布包本地文件头包含额外元数据或格式错误：{member.filename}')
        corrupt = bundle.testzip()
        if corrupt is not None:
            raise ValueError(f'发布包校验失败：{corrupt}')


def verify_extraction(archive, platform_name):
    """在隔离目录中使用 unzip 检查目录元数据和现有运行数据。"""
    verify_archive(archive, platform_name)
    if os.name != 'posix':
        return False
    archive = Path(archive).resolve()
    with tempfile.TemporaryDirectory(prefix='ehentai-release-check-') as directory:
        destination = Path(directory) / 'extract'
        destination.mkdir(mode=0o700)
        config = destination / '.env'
        config.write_bytes(b'existing configuration\n')
        logs = destination / 'logs'
        logs.mkdir(mode=0o700)
        log = logs / 'ehentai.log'
        log.write_bytes(b'existing log\n')
        protected = (destination, config, logs, log)
        def metadata(path):
            info = path.stat()
            return stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid
        before = [metadata(path) for path in protected]
        subprocess.run(
            ['unzip', '-o', '-qq', str(archive), '-d', str(destination)],
            check=True, preexec_fn=lambda: os.umask(0o022),
        )
        if [metadata(path) for path in protected] != before:
            raise ValueError('解压改变了目标目录或已有运行数据的权限或属主')
        if config.read_bytes() != b'existing configuration\n' or log.read_bytes() != b'existing log\n':
            raise ValueError('解压覆盖了已有配置或日志')
        for name, mode in expected_members(platform_name).items():
            path = destination / name
            if path.is_symlink() or not path.is_file() or stat.S_IMODE(path.stat().st_mode) != mode:
                raise ValueError(f'解压后的文件权限或类型不正确：{name}')
    return True


def smoke_test(executable):
    """从其他工作目录启动，确认程序读取可执行文件旁的 .env。"""
    with tempfile.TemporaryDirectory() as directory:
        directory = Path(directory)
        program_dir = directory / 'program'
        program_dir.mkdir()
        program = program_dir / executable.name
        shutil.copy2(executable, program)
        # 无需访问网络：无效时间应在读取相邻 .env 后立即报错。
        (program_dir / '.env').write_text("E_COOKIE='event=111'\nE_SCHEDULE='invalid'\n", encoding='utf-8')
        env = os.environ.copy()
        env['LOG_ENABLED'] = 'false'
        result = subprocess.run([str(program)], cwd=directory, env=env, capture_output=True, timeout=60)
        if result.returncode == 0 or b'E_SCHEDULE' not in result.stderr:
            raise RuntimeError(f'可执行文件启动或配置路径检查失败：{result.stderr!r}')


def main():
    if len(sys.argv) == 4 and sys.argv[1] == '--verify':
        archive, platform_name = Path(sys.argv[2]), sys.argv[3]
    elif len(sys.argv) == 2:
        platform_name = sys.argv[1]
        exe_name = next(iter(expected_members(platform_name)))
        smoke_test(ROOT / 'dist' / exe_name)
        archive = create_archive(ROOT, ROOT / 'release', platform_name)
    else:
        raise SystemExit('用法: package_release.py <platform> 或 --verify <archive> <platform>')
    verify_archive(archive, platform_name)
    print(f'发布包内容和权限检查通过：{archive}')
    if verify_extraction(archive, platform_name):
        print('隔离解压检查通过：目标目录权限、属主和已有配置及日志未改变。')


if __name__ == '__main__':
    main()
