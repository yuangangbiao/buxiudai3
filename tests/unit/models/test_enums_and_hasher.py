# -*- coding: utf-8 -*-
"""批量覆盖: models/enums.py + utils/password_hasher.py + core/error_codes.py"""
import pytest


# ============================================================
# models/enums.py: 所有枚举类
# ============================================================
ENUM_CLASSES = [
    ('OrderStatus', ['PENDING', 'CONFIRMED', 'IN_PRODUCTION', 'COMPLETED', 'CANCELLED']),
    ('ProductionStatus', ['PENDING', 'SCHEDULED', 'DISPATCHED', 'IN_PROGRESS', 'REPORTED', 'QC_PASSED', 'COMPLETED', 'CANCELLED']),
    ('ProcessStatus', ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'SKIPPED']),
    ('QualityResult', ['PENDING', 'PASSED', 'FAILED', 'REJECTED']),
    ('InventoryChange', ['IN', 'OUT', 'ADJUSTMENT', 'RETURN']),
    ('Priority', ['LOW', 'NORMAL', 'HIGH', 'URGENT']),
    ('SyncStatus', ['PENDING', 'SYNCING', 'SYNCED', 'FAILED']),
]


class TestAllEnums:
    @pytest.mark.parametrize("cls_name,expected_vals", ENUM_CLASSES)
    def test_values(self, cls_name, expected_vals):
        """每个枚举的 values() 返回所有值"""
        import models.enums as e
        cls = getattr(e, cls_name)
        vals = cls.values()
        assert isinstance(vals, list)
        for v in expected_vals:
            assert v in vals
        assert len(vals) == len(expected_vals)

    @pytest.mark.parametrize("cls_name,_", ENUM_CLASSES)
    def test_from_string_valid(self, cls_name, _):
        """from_string 有效值返回枚举实例"""
        import models.enums as e
        cls = getattr(e, cls_name)
        vals = cls.values()
        result = cls.from_string(vals[0])
        assert result is not None
        assert result.value == vals[0]

    @pytest.mark.parametrize("cls_name,_", ENUM_CLASSES)
    def test_from_string_none(self, cls_name, _):
        """from_string('') 返回 None"""
        import models.enums as e
        cls = getattr(e, cls_name)
        assert cls.from_string('') is None
        assert cls.from_string(None) is None

    @pytest.mark.parametrize("cls_name,_", ENUM_CLASSES)
    def test_from_string_invalid(self, cls_name, _):
        """from_string 无效值返回 None"""
        import models.enums as e
        cls = getattr(e, cls_name)
        assert cls.from_string('INVALID_VALUE_12345') is None

    @pytest.mark.parametrize("cls_name,_", ENUM_CLASSES)
    def test_from_string_case_insensitive(self, cls_name, _):
        """from_string 大小写不敏感"""
        import models.enums as e
        cls = getattr(e, cls_name)
        vals = cls.values()
        result = cls.from_string(vals[0].lower())
        assert result is not None

    @pytest.mark.parametrize("cls_name,expected_vals", ENUM_CLASSES)
    def test_member_access(self, cls_name, expected_vals):
        """枚举成员按名称访问"""
        import models.enums as e
        cls = getattr(e, cls_name)
        for val in expected_vals:
            member = getattr(cls, val)
            assert member.value == val


# ============================================================
# utils/password_hasher.py
# ============================================================
class TestHashPassword:
    def test_hash_with_salt(self):
        from utils.password_hasher import hash_password
        h, salt = hash_password("mypassword", "mysalt1234567890")
        assert isinstance(h, str)
        assert len(h) == 64  # sha256 hex
        assert salt == "mysalt1234567890"

    def test_hash_without_salt(self):
        from utils.password_hasher import hash_password
        h, salt = hash_password("mypassword")
        assert isinstance(h, str)
        assert isinstance(salt, str)
        assert len(salt) == 32  # token_hex(16)

    def test_same_password_same_salt_same_hash(self):
        from utils.password_hasher import hash_password
        h1, _ = hash_password("pw", "salt")
        h2, _ = hash_password("pw", "salt")
        assert h1 == h2

    def test_different_salt_different_hash(self):
        from utils.password_hasher import hash_password
        h1, _ = hash_password("pw", "salt1")
        h2, _ = hash_password("pw", "salt2")
        assert h1 != h2


class TestVerifyPassword:
    def test_verify_correct(self):
        from utils.password_hasher import hash_password, verify_password
        h, salt = hash_password("correct", "s")
        assert verify_password("correct", h, salt) is True

    def test_verify_wrong(self):
        from utils.password_hasher import hash_password, verify_password
        h, salt = hash_password("correct", "s")
        assert verify_password("wrong", h, salt) is False

    def test_verify_exception_returns_false(self):
        from utils.password_hasher import verify_password
        # None hash should trigger exception → False
        assert verify_password("pw", None, "salt") is False


class TestGenerateRandomPassword:
    def test_generates_valid_password(self):
        from utils.password_hasher import generate_random_password
        pw = generate_random_password(12)
        assert len(pw) == 12
        assert any(c.islower() for c in pw)
        assert any(c.isupper() for c in pw)
        assert any(c.isdigit() for c in pw)
        assert any(c in "!@#$%^&*" for c in pw)

    def test_default_length(self):
        from utils.password_hasher import generate_random_password
        pw = generate_random_password()
        assert len(pw) == 12


class TestIsPasswordStrong:
    def test_strong_password(self):
        from utils.password_hasher import is_password_strong
        ok, msg = is_password_strong("Abc12345")
        assert ok is True

    def test_too_short(self):
        from utils.password_hasher import is_password_strong
        ok, msg = is_password_strong("Ab1!")
        assert ok is False
        assert "8位" in msg

    def test_no_lowercase(self):
        from utils.password_hasher import is_password_strong
        ok, msg = is_password_strong("ABC12345")
        assert ok is False
        assert "小写" in msg

    def test_no_uppercase(self):
        from utils.password_hasher import is_password_strong
        ok, msg = is_password_strong("abc12345")
        assert ok is False
        assert "大写" in msg

    def test_no_digit(self):
        from utils.password_hasher import is_password_strong
        ok, msg = is_password_strong("Abcdefgh")
        assert ok is False
        assert "数字" in msg


# ============================================================
# core/error_codes.py: 至少测试 ErrorCode 类
# ============================================================
class TestLegacyErrorCode:
    def test_errors_dict_has_keys(self):
        from core.error_codes import ERRORS
        assert "ORDER_NOT_FOUND" in ERRORS
        assert "DATABASE_ERROR" in ERRORS
        ec = ERRORS["ORDER_NOT_FOUND"]
        assert ec.code == "E1001"
        assert ec.http_status == 404

    def test_error_domain_constants(self):
        from core.error_codes import ErrorDomain
        assert ErrorDomain.ORDER == "order"
        assert ErrorDomain.PRODUCTION == "production"
        assert ErrorDomain.AUTH == "auth"
