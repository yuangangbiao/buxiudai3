"""
JWT_SECRET_KEY 生成工具
用法:
  py scripts/tools/generate_jwt_key.py          # 安全模式，不覆盖已有密钥
  py scripts/tools/generate_jwt_key.py --force  # 强制重新生成
"""
import os
import sys
import secrets
from pathlib import Path


def _find_env_file(start_path: Path) -> Path:
    for parent in [start_path] + list(start_path.parents):
        candidate = parent / '.env'
        if candidate.exists():
            return candidate
    return start_path / '.env'


def generate_jwt_key(force: bool = False) -> None:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent.parent
    env_path = _find_env_file(project_root)

    env_content = env_path.read_text(encoding='utf-8') if env_path.exists() else ''
    lines = env_content.splitlines()
    existing_key = ''
    key_line_index = -1

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('JWT_SECRET_KEY='):
            val = stripped.split('=', 1)[1].strip().strip('"').strip("'")
            if val:
                existing_key = val
                key_line_index = i
            else:
                key_line_index = i
            break

    if existing_key and not force:
        prefix = existing_key[:4]
        suffix = existing_key[-4:]
        print(f'JWT_SECRET_KEY 已存在（前4位: {prefix}... 后4位: ...{suffix}）')
        print('如需重新生成请使用 --force 参数')
        return

    new_key = secrets.token_hex(32)

    new_line = f'JWT_SECRET_KEY={new_key}'
    if key_line_index >= 0:
        lines[key_line_index] = new_line
    else:
        if lines and lines[-1].strip() != '':
            lines.append('')
        lines.append(new_line)

    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    if existing_key and force:
        print(f'JWT_SECRET_KEY 已强制重新生成并写入 {env_path}')
    else:
        print(f'JWT_SECRET_KEY 已生成并写入 {env_path}')


if __name__ == '__main__':
    force = '--force' in sys.argv
    generate_jwt_key(force)
