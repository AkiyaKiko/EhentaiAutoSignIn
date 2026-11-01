from pathlib import Path
import re
import subprocess
import sys
import tempfile


def check_elf(path, name):
    """确保 ELF 不含 DWARF 调试段或静态符号表；动态符号仍供运行时使用。"""
    result = subprocess.run(['readelf', '--wide', '--section-headers', str(path)],
                            check=True, capture_output=True, text=True)
    sections = re.findall(r'\.(?:z?debug_[A-Za-z0-9_]+|gdb_index|symtab)\b', result.stdout)
    if sections:
        raise RuntimeError(f'{name} contains debug sections or a static symbol table: {", ".join(sorted(set(sections)))}')


def main(executable):
    # onefile 中的共享库位于内嵌归档，检查外层 ELF 还不足以确认它们已剥离。
    from PyInstaller.archive.readers import CArchiveReader

    executable = Path(executable)
    check_elf(executable, str(executable))
    archive = CArchiveReader(str(executable))
    count = 0
    with tempfile.TemporaryDirectory(prefix='ehentai-elf-check-') as directory:
        extracted = Path(directory) / 'binary'
        for name, entry in archive.toc.items():
            if entry[-1] != 'b':
                continue
            data = archive.extract(name)
            if data.startswith(b'\x7fELF'):
                extracted.write_bytes(data)
                check_elf(extracted, name)
                count += 1
    if not count:
        raise RuntimeError('No embedded ELF libraries found in the PyInstaller archive')
    print(f'Checked executable and {count} bundled ELF files for debug sections and static symbols')


if __name__ == '__main__':
    main(sys.argv[1])
