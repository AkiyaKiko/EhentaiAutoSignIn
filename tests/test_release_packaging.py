import importlib.util
import os
from pathlib import Path
import stat
import subprocess
import sys
import zipfile

import pytest


script = Path(__file__).resolve().parent.parent / '.github' / 'scripts' / 'package_release.py'
spec = importlib.util.spec_from_file_location('package_release', script)
packaging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packaging)


@pytest.fixture
def package_root(tmp_path):
    (tmp_path / 'dist').mkdir()
    for exe in ('EhentaiAutoSignIn.exe', 'EhentaiAutoSignIn'):
        (tmp_path / 'dist' / exe).write_bytes(b'executable')
    for name in packaging.DOCUMENTS:
        (tmp_path / name).write_bytes(b'public file')
    (tmp_path / '.env').write_bytes(b'secret')
    (tmp_path / 'logs').mkdir()
    (tmp_path / 'logs' / 'ehentai.log').write_bytes(b'private log')
    return tmp_path


@pytest.fixture
def untrusted_zip(tmp_path):
    archive = tmp_path / 'release.zip'

    def create(modify):
        items = []
        for name, mode in packaging.expected_members('linux-x64').items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            items.append(info)
        modify(items)
        with zipfile.ZipFile(archive, 'w') as bundle:
            for item in items:
                bundle.writestr(item, b'data')
        return archive

    return create


@pytest.mark.parametrize('target', sorted(packaging.PLATFORMS))
def test_all_platforms_have_exact_files_and_normalized_permissions(package_root, target):
    archive = packaging.create_archive(package_root, package_root / 'release', target)
    packaging.verify_archive(archive, target)
    with zipfile.ZipFile(archive) as bundle:
        assert set(bundle.namelist()) == set(packaging.expected_members(target))
        for member in bundle.infolist():
            assert member.create_system == 3
            assert member.extra == b''
            assert stat.S_ISREG(member.external_attr >> 16)
            assert stat.S_IMODE(member.external_attr >> 16) == packaging.expected_members(target)[member.filename]


def test_rejects_unsupported_platform_and_non_regular_source(package_root):
    with pytest.raises(ValueError):
        packaging.create_archive(package_root, package_root / 'release', '../linux-x64')
    binary = package_root / 'dist' / 'EhentaiAutoSignIn'
    binary.unlink()
    binary.mkdir()
    with pytest.raises(ValueError, match='普通文件'):
        packaging.create_archive(package_root, package_root / 'release', 'linux-x64')


@pytest.mark.parametrize('name', ['./', '../outside', '/absolute', 'nested/file', '.env', 'logs/'])
def test_rejects_directory_and_unexpected_paths(untrusted_zip, name):
    archive = untrusted_zip(lambda items: setattr(items[0], 'filename', name))
    with pytest.raises(ValueError):
        packaging.verify_archive(archive, 'linux-x64')


def set_mode(info, mode):
    info.external_attr = mode << 16


@pytest.mark.parametrize('mutate', [
    lambda items: set_mode(items[0], stat.S_IFLNK | 0o777),
    lambda items: set_mode(items[0], stat.S_IFDIR | 0o755),
    lambda items: set_mode(items[0], stat.S_IFREG | 0o4755),
    lambda items: set_mode(items[1], stat.S_IFREG | 0o666),
    lambda items: setattr(items[0], 'extra', b'ux\x00\x00'),
    lambda items: setattr(items[0], 'create_system', 0),
], ids=['symlink', 'directory', 'setuid', 'writable', 'extra-metadata', 'non-unix'])
def test_rejects_links_unsafe_modes_and_extra_metadata(untrusted_zip, mutate):
    archive = untrusted_zip(mutate)
    with pytest.raises(ValueError):
        packaging.verify_archive(archive, 'linux-x64')


def test_rejects_extra_metadata_in_local_header(tmp_path):
    archive = tmp_path / 'release.zip'
    with zipfile.ZipFile(archive, 'w') as bundle:
        for name, mode in packaging.expected_members('linux-x64').items():
            info = zipfile.ZipInfo(name)
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | mode) << 16
            if name == 'EhentaiAutoSignIn':
                info.extra = b'ux\x00\x00'
            with bundle.open(info, 'w') as destination:
                destination.write(b'data')
            # 构造中央目录没有 extra、本地文件头却有 extra 的归档。
            info.extra = b''
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.getinfo('EhentaiAutoSignIn').extra == b''
    with pytest.raises(ValueError, match='本地文件头'):
        packaging.verify_archive(archive, 'linux-x64')


def test_rejects_duplicate_files(untrusted_zip):
    def duplicate(items):
        items[1].filename = items[0].filename
    with pytest.warns(UserWarning, match='Duplicate name'):
        archive = untrusted_zip(duplicate)
    with pytest.raises(ValueError):
        packaging.verify_archive(archive, 'linux-x64')


def test_archive_verification_uses_utf8_with_non_ascii_path(package_root):
    archive = packaging.create_archive(package_root, package_root / '发布', 'windows-x64')
    env = os.environ.copy()
    # 与工作流一致，即使系统默认代码页不是 UTF-8 也能打印路径。
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    result = subprocess.run(
        [sys.executable, str(script), '--verify', str(archive), 'windows-x64'],
        env=env, capture_output=True,
    )
    assert result.returncode == 0, result.stderr.decode('utf-8', errors='replace')
    assert '发布' in result.stdout.decode('utf-8')


@pytest.mark.skipif(os.name != 'posix', reason='POSIX 解压验证需要 Linux 或 macOS')
def test_extraction_preserves_directory_and_runtime_data(package_root):
    archive = packaging.create_archive(package_root, package_root / 'release', 'linux-x64')
    assert packaging.verify_extraction(archive, 'linux-x64') is True
