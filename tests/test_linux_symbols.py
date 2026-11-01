import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from unittest.mock import Mock

import pytest


script = Path(__file__).resolve().parent.parent / '.github' / 'scripts' / 'check_linux_symbols.py'
spec = importlib.util.spec_from_file_location('check_linux_symbols', script)
symbols = importlib.util.module_from_spec(spec)
spec.loader.exec_module(symbols)


@pytest.mark.parametrize('section', ['.debug_info', '.debug_line', '.zdebug_info', '.gdb_index', '.symtab'])
def test_rejects_elf_debug_sections(section, monkeypatch):
    monkeypatch.setattr(symbols.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout=f'  [20] {section} PROGBITS 000000 000000\n', stderr='',
    )))
    with pytest.raises(RuntimeError, match='debug sections'):
        symbols.check_elf('binary', 'test library')


def test_accepts_runtime_symbols_and_debuglink(monkeypatch):
    monkeypatch.setattr(symbols.subprocess, 'run', Mock(return_value=subprocess.CompletedProcess(
        args=[], returncode=0, stdout='  [ 5] .dynsym DYNSYM\n  [20] .gnu_debuglink PROGBITS\n', stderr='',
    )))
    symbols.check_elf('binary', 'test library')


def test_checks_embedded_elf_files(monkeypatch):
    class FakeArchive:
        def __init__(self, executable):
            self.toc = {'libpython.so': (0, 0, 0, 0, 'b'), 'data': (0, 0, 0, 0, 'x')}

        def extract(self, name):
            return b'\x7fELFtest' if name == 'libpython.so' else b'not an ELF'

    reader = ModuleType('PyInstaller.archive.readers')
    reader.CArchiveReader = FakeArchive
    monkeypatch.setitem(sys.modules, 'PyInstaller', ModuleType('PyInstaller'))
    monkeypatch.setitem(sys.modules, 'PyInstaller.archive', ModuleType('PyInstaller.archive'))
    monkeypatch.setitem(sys.modules, 'PyInstaller.archive.readers', reader)
    check = Mock()
    monkeypatch.setattr(symbols, 'check_elf', check)
    symbols.main('test-executable')
    assert [call.args[1] for call in check.call_args_list] == ['test-executable', 'libpython.so']
