from pathlib import Path
import sys

from ehentai import config


def test_source_uses_project_directory(monkeypatch):
    monkeypatch.delenv('EHENTAI_DATA_DIR', raising=False)
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert config.application_dir() == Path(config.__file__).resolve().parent.parent


def test_executable_uses_its_own_directory(monkeypatch, tmp_path):
    monkeypatch.delenv('EHENTAI_DATA_DIR', raising=False)
    executable = tmp_path / 'sample-release' / 'EhentaiAutoSignIn.exe'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    assert config.application_dir() == executable.resolve().parent


def test_explicit_data_directory_overrides_application_location(monkeypatch, tmp_path):
    data_dir = tmp_path / 'data'
    monkeypatch.setenv('EHENTAI_DATA_DIR', str(data_dir))
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    assert config.application_dir() == data_dir.resolve()
