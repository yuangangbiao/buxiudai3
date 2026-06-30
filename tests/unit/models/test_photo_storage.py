# Phase 1: 覆盖 0% 模块 — photo_storage.py 单元测试
import pytest
import os
import io
import tempfile
from unittest.mock import patch, MagicMock, mock_open

from models.photo_storage import (
    _get_upload_dir,
    safe_filename,
    validate_magic,
    strip_exif,
    save,
    delete,
    ALLOWED_EXTENSIONS,
    MAGIC_BYTES,
)


class TestSafeFilename:
    def test_valid_extensions(self):
        """支持 jpg/jpeg/png 扩展名"""
        name = safe_filename('photo.jpg')
        assert name.endswith('.jpg')
        assert len(name) == 36  # 32 hex uuid + 4 char '.jpg'

        name2 = safe_filename('photo.jpeg')
        assert name2.endswith('.jpeg')

        name3 = safe_filename('photo.png')
        assert name3.endswith('.png')

    def test_lowercases_extension(self):
        """大写扩展名自动转小写"""
        name = safe_filename('photo.JPG')
        assert name.endswith('.jpg')

    def test_no_extension_raises(self):
        """无扩展名时报错"""
        with pytest.raises(ValueError, match='不支持的格式'):
            safe_filename('photo')

    def test_none_raises(self):
        """传入 None 报错"""
        with pytest.raises(ValueError, match='不支持的格式'):
            safe_filename(None)

    def test_disallowed_extension_raises(self):
        """不支持的扩展名报错"""
        with pytest.raises(ValueError, match='不支持的格式'):
            safe_filename('photo.gif')


class TestValidateMagic:
    def test_jpg_header_valid(self):
        """JPG 魔术字节匹配"""
        f = io.BytesIO(b'\xff\xd8\xff\xe0')
        assert validate_magic(f, '.jpg') is True

    def test_png_header_valid(self):
        """PNG 魔术字节匹配"""
        f = io.BytesIO(b'\x89PNG\r\n\x1a\n')
        assert validate_magic(f, '.png') is True

    def test_jpg_header_invalid(self):
        """JPG 魔术字节不匹配返回 False"""
        f = io.BytesIO(b'\x00\x00\xff\xe0')
        assert validate_magic(f, '.jpg') is False

    def test_unknown_ext_returns_true(self):
        """未在 MAGIC_BYTES 中注册的扩展名返回 True（跳过校验）"""
        f = io.BytesIO(b'anything')
        assert validate_magic(f, '.unknown') is True

    def test_restores_position(self):
        """校验后恢复文件指针位置"""
        data = b'\xff\xd8\xff\xe0extra'
        f = io.BytesIO(data)
        f.seek(2)  # 模拟在文件中间
        validate_magic(f, '.jpg')
        assert f.tell() == 2  # 恢复到调用前的位置


class TestStripExif:
    def test_strip_exif_pil_available(self):
        """PIL 可用时剥离 EXIF"""
        mock_img = MagicMock()
        mock_img.mode = 'RGB'
        mock_img.size = (100, 100)
        mock_img.getdata.return_value = [(255, 0, 0)] * 10000

        with patch('PIL.Image.open', return_value=mock_img) as mock_open:
            with patch('PIL.Image.new') as mock_new:
                mock_new.return_value.putdata = MagicMock()
                strip_exif('/fake/path.jpg')

        mock_open.assert_called_once_with('/fake/path.jpg')
        mock_img.getdata.assert_called_once()
        mock_new.assert_called_once_with('RGB', (100, 100))

    def test_strip_exif_pil_unavailable(self):
        """PIL 不可用时静默跳过"""
        # PIL 是外部模块，无法直接 patch Image 类；
        # 通过 patch builtins.__import__ 模拟 PIL 导入失败
        original_import = __builtins__['__import__']

        def mock_import(name, *args, **kwargs):
            if name == 'PIL':
                raise ImportError('No module named PIL')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=mock_import):
            # 不应抛出异常
            strip_exif('/fake/path.jpg')


class TestSave:
    def test_save_success(self, tmp_path):
        """正常保存流程"""
        content = b'\xff\xd8\xff\xe0testdata'
        fileobj = io.BytesIO(content)
        upload_dir = tmp_path / 'uploads' / 'quality'

        with patch('models.photo_storage._get_upload_dir', return_value=str(upload_dir)):
            with patch('models.photo_storage.strip_exif'):
                result = save(fileobj, 'test.jpg')

        assert '/static/uploads/quality/' in result
        # 验证文件已写入
        files = list(upload_dir.iterdir())
        assert len(files) == 1
        assert files[0].suffix == '.jpg'
        assert files[0].read_bytes() == content

    def test_save_disallowed_ext(self):
        """不支持的扩展名报错"""
        with pytest.raises(ValueError, match='仅支持 jpg/png'):
            save(io.BytesIO(b'data'), 'test.gif')

    def test_save_magic_mismatch(self):
        """魔术字节不匹配报错"""
        content = b'\x00\x00\xff\xe0fakejpeg'
        fileobj = io.BytesIO(content)
        with pytest.raises(ValueError, match='文件内容与扩展名不匹配'):
            save(fileobj, 'test.jpg')

    def test_save_exceeds_max_size(self, tmp_path):
        """超过 10MB 报错并删除文件"""
        upload_dir = tmp_path / 'uploads' / 'quality'
        # 模拟一个超过 10MB 的文件
        big_content = b'\xff\xd8' + b'A' * (10 * 1024 * 1024 + 1)

        with patch('models.photo_storage._get_upload_dir', return_value=str(upload_dir)):
            with patch('models.photo_storage.strip_exif'):
                fileobj = io.BytesIO(big_content)
                with pytest.raises(ValueError, match='超过 10MB'):
                    save(fileobj, 'test.jpg')

        # 验证文件已被删除
        assert not list(upload_dir.iterdir()) or not any(
            True for _ in upload_dir.iterdir()
        )


class TestDelete:
    def test_delete_existing_file(self, tmp_path):
        """删除存在的文件"""
        upload_dir = tmp_path / 'uploads' / 'quality'
        upload_dir.mkdir(parents=True)
        test_file = upload_dir / 'abc123.jpg'
        test_file.write_text('test')

        with patch('models.photo_storage._get_upload_dir', return_value=str(upload_dir)):
            delete('/static/uploads/quality/abc123.jpg')

        assert not test_file.exists()

    def test_delete_nonexistent_file(self, tmp_path):
        """删除不存在的文件不报错"""
        upload_dir = tmp_path / 'uploads' / 'quality'
        upload_dir.mkdir(parents=True)

        with patch('models.photo_storage._get_upload_dir', return_value=str(upload_dir)):
            # 不应抛出异常
            delete('/static/uploads/quality/nonexistent.jpg')

    def test_delete_empty_path(self):
        """空路径不执行删除"""
        # 不应抛出异常
        delete(None)
        delete('')


class TestGetUploadDir:
    """_get_upload_dir 单元测试"""

    def test_get_upload_dir_default(self):
        """默认路径（环境变量未设置时使用 os.path.join fallback）"""
        with patch('models.photo_storage.os.getenv') as mock_getenv:
            mock_getenv.side_effect = lambda key, default=None: default if key == 'PHOTO_STORAGE_PATH' else os.environ.get(key, default)
            result = _get_upload_dir()
        assert 'uploads' in result
        assert result.endswith('quality')

    def test_get_upload_dir_env(self):
        """设置了 PHOTO_STORAGE_PATH 环境变量"""
        test_path = 'Z:/custom/upload/path'
        with patch('models.photo_storage.os.getenv', return_value=test_path):
            result = _get_upload_dir()
        assert result == os.path.abspath(test_path)
