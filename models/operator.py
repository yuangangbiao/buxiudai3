# -*- coding: utf-8 -*-
"""
操作员管理模型 - DAO层
"""

from datetime import datetime
from models.database import get_connection
from utils.password_hasher import hash_password, verify_password, generate_random_password


class OperatorDAO:
    """操作员数据访问对象"""

    TABLE_NAME = 'operators'

    @staticmethod
    def get_all():
        """获取所有操作员"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, operator_id, name, role, status, created_at, last_login, wechat_userid
                FROM operators ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_id(operator_id):
        """根据ID获取操作员"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, operator_id, name, role, status, created_at, last_login, wechat_userid
                FROM operators WHERE operator_id=%s
            """, (operator_id,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_by_wechat_userid(wechat_userid):
        """根据企业微信用户ID查找操作员"""
        if not wechat_userid:
            return None
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, operator_id, name, role, status, created_at, last_login, wechat_userid
                FROM operators WHERE wechat_userid=%s
            """, (wechat_userid,))
            row = cursor.fetchone()
            cursor.close()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def login(operator_id, password):
        """登录验证"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, operator_id, name, role, status, password, password_salt
                FROM operators WHERE operator_id=%s AND status='正常'
            """, (operator_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                return None

            row = dict(row)
            stored_password = row['password']
            stored_salt = row['password_salt']

            if stored_salt is None:
                if stored_password == password:
                    conn2 = get_connection()
                    cursor2 = conn2.cursor()
                    pwd_hash, salt = hash_password(password)
                    cursor2.execute("""
                        UPDATE operators SET password=%s, password_salt=%s WHERE operator_id=%s
                    """, (pwd_hash, salt, operator_id))
                    conn2.commit()
                    cursor2.close()
                    conn2.close()
                    return {'id': row['id'], 'operator_id': row['operator_id'], 'name': row['name'],
                            'role': row['role'], 'status': row['status']}
            else:
                if verify_password(password, stored_password, stored_salt):
                    conn2 = get_connection()
                    cursor2 = conn2.cursor()
                    cursor2.execute("""
                        UPDATE operators SET last_login=%s WHERE operator_id=%s
                    """, (datetime.now().isoformat(), operator_id))
                    conn2.commit()
                    cursor2.close()
                    conn2.close()
                    return {'id': row['id'], 'operator_id': row['operator_id'], 'name': row['name'],
                            'role': row['role'], 'status': row['status']}

            return None
        finally:
            conn.close()

    @staticmethod
    def add(data):
        """添加操作员"""
        password = data.get('password', generate_random_password())
        pwd_hash, salt = hash_password(password)

        conn = get_connection()
        try:
            cursor = conn.cursor()
            if 'wechat_userid' in data and data['wechat_userid']:
                cursor.execute("""
                    INSERT INTO operators (operator_id, name, role, password, password_salt, status, wechat_userid)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    data['operator_id'],
                    data['name'],
                    data.get('role', '操作员'),
                    pwd_hash,
                    salt,
                    data.get('status', '正常'),
                    data['wechat_userid']
                ))
            else:
                cursor.execute("""
                    INSERT INTO operators (operator_id, name, role, password, password_salt, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    data['operator_id'],
                    data['name'],
                    data.get('role', '操作员'),
                    pwd_hash,
                    salt,
                    data.get('status', '正常')
                ))
            conn.commit()
            cursor.close()
            return True
        finally:
            conn.close()

    @staticmethod
    def update(operator_id, data):
        """更新操作员"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            fields = []
            values = []
            if 'name' in data:
                fields.append('name=%s')
                values.append(data['name'])
            if 'role' in data:
                fields.append('role=%s')
                values.append(data['role'])
            if 'password' in data:
                pwd_hash, salt = hash_password(data['password'])
                fields.append('password=%s')
                values.append(pwd_hash)
                fields.append('password_salt=%s')
                values.append(salt)
            if 'status' in data:
                fields.append('status=%s')
                values.append(data['status'])
            if 'wechat_userid' in data:
                fields.append('wechat_userid=%s')
                values.append(data['wechat_userid'])

            fields.append('updated_at=%s')
            values.append(datetime.now().isoformat())
            values.append(operator_id)

            cursor.execute(f"""
                UPDATE operators SET {','.join(fields)} WHERE operator_id=%s
            """, values)
            conn.commit()
            cursor.close()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete(operator_id):
        """删除操作员（不删除管理员）"""
        if operator_id == 'admin':
            return False
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM operators WHERE operator_id=%s AND operator_id!='admin'", (operator_id,))
            conn.commit()
            cursor.close()
            return True
        finally:
            conn.close()

    @staticmethod
    def change_password(operator_id, old_password, new_password):
        """修改密码"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT password, password_salt FROM operators WHERE operator_id=%s
            """, (operator_id,))
            row = cursor.fetchone()
            cursor.close()
            conn.close()

            if not row:
                return False

            row = dict(row)
            stored_password = row['password']
            stored_salt = row['password_salt']

            if stored_salt is None:
                if stored_password != old_password:
                    return False
            else:
                if not verify_password(old_password, stored_password, stored_salt):
                    return False

            pwd_hash, salt = hash_password(new_password)
            conn2 = get_connection()
            try:
                cursor2 = conn2.cursor()
                cursor2.execute("""
                    UPDATE operators SET password=%s, password_salt=%s, updated_at=%s WHERE operator_id=%s
                """, (pwd_hash, salt, datetime.now().isoformat(), operator_id))
                conn2.commit()
                cursor2.close()
                return True
            finally:
                conn2.close()
        finally:
            conn.close()


class OperatorLogDAO:
    """操作日志数据访问对象"""

    TABLE_NAME = 'operator_logs'

    @staticmethod
    def add(operator_id, operator_name, action, target_type='', target_id='', details=''):
        """记录操作日志"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO operator_logs (operator_id, operator_name, action, target_type, target_id, details)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (operator_id, operator_name, action, target_type, target_id, details))
            conn.commit()
            cursor.close()
        finally:
            conn.close()

    @staticmethod
    def get_logs(limit=100):
        """获取最近的操作日志"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM operator_logs ORDER BY created_at DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def get_by_operator(operator_id, limit=50):
        """获取指定操作员的日志"""
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM operator_logs WHERE operator_id=%s ORDER BY created_at DESC LIMIT %s
            """, (operator_id, limit))
            rows = cursor.fetchall()
            cursor.close()
            return [dict(r) for r in rows]
        finally:
            conn.close()
