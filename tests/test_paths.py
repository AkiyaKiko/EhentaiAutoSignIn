from pathlib import Path
import sys

from ehentai import config


def test_source_uses_project_directory(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    assert config.application_dir() == Path(config.__file__).resolve().parent.parent


def test_executable_uses_its_own_directory(monkeypatch, tmp_path):
    executable = tmp_path / 'sample-release' / 'EhentaiAutoSignIn.exe'
    monkeypatch.setattr(sys, 'frozen', True, raising=False)
    monkeypatch.setattr(sys, 'executable', str(executable))
    assert config.application_dir() == executable.resolve().parent
