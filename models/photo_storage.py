# -*- coding: utf-8 -*-
"""
照片存储抽象层 — 支持本地 / OSS 切换
"""
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger('photo_storage')

ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
MAGIC_BYTES = {
    '.jpg': b'\xff\xd8',
    '.jpeg': b'\xff\xd8',
    '.png': b'\x89PNG\r\n\x1a\n',
}
MAX_SIZE = 10 * 1024 * 1024  # 10MB


def _get_upload_dir():
    base = os.getenv('PHOTO_STORAGE_PATH',
                     os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai', 'static', 'uploads', 'quality'))
    return os.path.abspath(base)


def safe_filename(original_name):
    ext = os.path.splitext(original_name or '')[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'不支持的格式: {ext}')
    return f'{uuid.uuid4().hex}{ext}'


def validate_magic(fileobj, ext):
    """魔术字节校验"""
    expected = MAGIC_BYTES.get(ext)
    if not expected:
        return True
    pos = fileobj.tell()
    header = fileobj.read(len(expected))
    fileobj.seek(pos)
    return header[:len(expected)] == expected


def strip_exif(filepath):
    """剥离 EXIF 元数据"""
    try:
        from PIL import Image
        img = Image.open(filepath)
        data = list(img.getdata())
        clean = Image.new(img.mode, img.size)
        clean.putdata(data)
        clean.save(filepath)
    except ImportError:
        logger.warning('PIL未安装，跳过EXIF剥离')


def save(fileobj, original_name):
    """保存照片，返回公开路径"""
    ext = os.path.splitext(original_name or '')[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f'仅支持 jpg/png，收到: {ext}')

    if not validate_magic(fileobj, ext):
        raise ValueError('文件内容与扩展名不匹配')

    filename = safe_filename(original_name)
    upload_dir = _get_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)

    filepath = os.path.join(upload_dir, filename)
    fileobj.seek(0)
    with open(filepath, 'wb') as f:
        f.write(fileobj.read())

    if os.path.getsize(filepath) > MAX_SIZE:
        os.remove(filepath)
        raise ValueError('文件超过 10MB')

    strip_exif(filepath)

    rel = f'/static/uploads/quality/{filename}'
    logger.info('照片已保存: %s', rel)
    return rel


def delete(path):
    """删除照片（孤儿文件清理）"""
    if not path:
        return
    filename = os.path.basename(path)
    filepath = os.path.join(_get_upload_dir(), filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        logger.info('照片已删除: %s', filename)
