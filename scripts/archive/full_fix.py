# -*- coding: utf-8 -*-
"""完整修改database.py，移除SQLite支持"""

with open('models/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修改导入部分
content = content.replace('import sqlite3\n', '')
content = content.replace('from config import DB_PATH, DB_TYPE, MYSQL_CONFIG', 'from config import MYSQL_CONFIG')

# 2. 修改注释
content = content.replace('"""\n数据库连接与初始化\n"""', '"""\n数据库连接与初始化 - 仅支持MySQL\n"""')

# 3. 移除动态数据库类型检测代码
content = content.replace('# 动态数据库类型检测 - 用于处理MySQL连接失败时的降级\n_current_db_type = DB_TYPE\n\ndef _get_current_db_type():\n    """获取当前实际使用的数据库类型"""\n    return _current_db_type\n\n', '')

# 4. 修改_create_connection函数
content = content.replace('def _create_connection(db_path):\n    """创建数据库连接"""\n    if DB_TYPE == "mysql":\n        ', 'def _create_connection():\n    """创建MySQL数据库连接"""\n    ')
content = content.replace('raise Exception("[DB] pymysql模块未安装，请安装pymysql或修改DB_TYPE为sqlite")', 'raise Exception("[DB] pymysql模块未安装，请安装pymysql")')

# 5. 移除SQLite分支（_create_connection函数中的）
content = content.replace('        raise Exception("[DB] 连接池返回空连接")\n    else:\n        conn = sqlite3.connect(db_path, timeout=30)\n        conn.row_factory = sqlite3.Row\n        conn.execute("PRAGMA foreign_keys = ON")\n        return conn\n\n\ndef get_connection():', '        raise Exception("[DB] 连接池返回空连接")\n\n\ndef get_connection():')

# 6. 修改get_connection调用
content = content.replace('    return _create_connection(DB_PATH)', '    return _create_connection()')

# 7. 修改_migrate_tables函数
content = content.replace('    current_db_type = _get_current_db_type()\n    if current_db_type == "mysql":\n        # MySQL表结构升级', '    # MySQL表结构升级')

# 8. 移除_migrate_tables中的SQLite分支
import re
content = re.sub(r'\n    else:\n        # SQLite表结构升级[\s\S]*?(?=\n    conn\.commit\(\))', '', content)

# 9. 修改init_db函数中的数据库类型判断
content = content.replace('    current_db_type = _get_current_db_type()\n    if current_db_type == "mysql":\n        c.execute(', '    c.execute(')

# 10. 移除init_db中的SQLite分支（只保留MySQL表创建语句）
content = re.sub(r'\n    else:\n        c\.execute\("""[\s\S]*?"""\n        \)\n\n', '\n', content)
content = re.sub(r'\n    else:\n        c\.execute\(\'\'\'[\s\S]*?\'\'\'\n        \)\n\n', '\n', content)

# 11. 修复可能的重复空行
content = re.sub(r'\n{3,}', '\n\n', content)

# 写入文件
with open('models/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('database.py修改完成')
