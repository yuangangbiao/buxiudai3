# -*- coding: utf-8 -*-
"""Run native coverage for models/operator.py after executing all test paths."""
import coverage
from unittest.mock import patch, MagicMock
from models.operator import OperatorDAO, OperatorLogDAO

cov = coverage.Coverage(source=["models"])
cov.start()

# ---- get_all ----
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchall.return_value = [{"id": 1, "operator_id": "001", "name": "a"}]
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.get_all()

# ---- get_by_id ----
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"id": 1, "operator_id": "001", "name": "a"}
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.get_by_id("001")
# not found
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = None
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.get_by_id("xxx")

# ---- get_by_wechat_userid ----
assert OperatorDAO.get_by_wechat_userid("") is None
assert OperatorDAO.get_by_wechat_userid(None) is None
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"id": 1, "wechat_userid": "wx001"}
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.get_by_wechat_userid("wx001")
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = None
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.get_by_wechat_userid("nonexistent")

# ---- login ----
# not found
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = None
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.login("001", "pwd")

# no salt, match
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
row = {"id": 1, "operator_id": "001", "name": "a", "role": "o", "status": "正常",
       "password": "plain", "password_salt": None}
cursor.fetchone.return_value = row
conn2 = MagicMock(); cursor2 = MagicMock(); conn2.cursor.return_value = cursor2
with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.login("001", "plain")

# no salt, mismatch
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = row
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.login("001", "wrong")

# with salt, correct
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
row2 = {"id": 1, "operator_id": "001", "name": "a", "role": "o", "status": "正常",
        "password": "hash", "password_salt": "salt"}
cursor.fetchone.return_value = row2
conn2 = MagicMock(); cursor2 = MagicMock(); conn2.cursor.return_value = cursor2
with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
     patch("models.operator.verify_password", return_value=True):
    OperatorDAO.login("001", "correct")

# with salt, wrong
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = row2
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.verify_password", return_value=False):
    OperatorDAO.login("001", "wrong")

# ---- add ----
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.add({"operator_id": "003", "name": "w", "wechat_userid": "wx003"})

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.add({"operator_id": "004", "name": "z"})

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.add({"operator_id": "005", "name": "q", "wechat_userid": ""})

# ---- update ----
for data in [{"name": "x"}, {"role": "管理员"}, {"status": "停用"},
             {"wechat_userid": "wx_new"}, {"name": "a", "role": "b", "status": "c", "wechat_userid": "d"}]:
    conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
    with patch("models.operator.get_connection", return_value=conn):
        OperatorDAO.update("001", data)

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.update("001", {"password": "new"})

# ---- delete ----
assert OperatorDAO.delete("admin") is False
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.delete("non_admin")

# ---- change_password ----
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = None
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.change_password("001", "old", "new")

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"password": "old", "password_salt": None}
conn2 = MagicMock(); cursor2 = MagicMock(); conn2.cursor.return_value = cursor2
with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.change_password("001", "old", "new")

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"password": "old", "password_salt": None}
with patch("models.operator.get_connection", return_value=conn):
    OperatorDAO.change_password("001", "wrong", "new")

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"password": "hash", "password_salt": "salt"}
conn2 = MagicMock(); cursor2 = MagicMock(); conn2.cursor.return_value = cursor2
with patch("models.operator.get_connection", side_effect=[conn, conn2]), \
     patch("models.operator.verify_password", return_value=True), \
     patch("models.operator.hash_password", return_value=("h", "s")):
    OperatorDAO.change_password("001", "old", "new")

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchone.return_value = {"password": "hash", "password_salt": "salt"}
with patch("models.operator.get_connection", return_value=conn), \
     patch("models.operator.verify_password", return_value=False):
    OperatorDAO.change_password("001", "wrong", "new")

# ---- OperatorLogDAO ----
conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
with patch("models.operator.get_connection", return_value=conn):
    OperatorLogDAO.add("001", "张三", "登录", "user", "001", "成功")

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchall.return_value = [{"id": 1, "action": "登录"}]
with patch("models.operator.get_connection", return_value=conn):
    OperatorLogDAO.get_logs()

conn = MagicMock(); cursor = MagicMock(); conn.cursor.return_value = cursor
cursor.fetchall.return_value = []
with patch("models.operator.get_connection", return_value=conn):
    OperatorLogDAO.get_by_operator("001")

cov.stop()
cov.save()
total = cov.report(["models/operator.py"], show_missing=True)
print(f"\n=== TOTAL: {total:.1f}% ===")
