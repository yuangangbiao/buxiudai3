# -*- coding: utf-8 -*-
"""
MySQL局域网连接配置脚本
运行此脚本允许局域网访问MySQL
"""
import os

def get_db_password():
    """从环境变量获取数据库密码，如果未设置则提示用户输入"""
    password = os.getenv('MYSQL_PASSWORD', '')
    if not password:
        print("[警告] MYSQL_PASSWORD 环境变量未设置，请手动替换SQL中的密码占位符")
        return '<YOUR_PASSWORD>'
    return password

def setup_mysql_lan_access():
    print("=" * 50)
    print("MySQL 局域网连接配置")
    print("=" * 50)

    db_password = get_db_password()

    # MySQL配置文件路径
    myini = r"C:\ProgramData\MySQL\MySQL Server 8.0\my.ini"

    if not os.path.exists(myini):
        myini = r"C:\ProgramData\MySQL\MySQL Server 5.7\my.ini"

    print(f"找到MySQL配置: {myini}")

    # 读取配置
    with open(myini, 'r', encoding='utf-8') as f:
        content = f.read()

    # 检查是否已绑定所有地址
    if "bind-address=0.0.0.0" in content or "bind-address=*" in content:
        print("[OK] MySQL已配置允许外部连接")
    else:
        print("[修改] 正在修改MySQL配置...")
        # 修改bind-address
        if "[mysqld]" in content:
            lines = content.split("\n")
            new_lines = []
            for line in lines:
                if line.strip().startswith("bind-address="):
                    new_lines.append("bind-address=0.0.0.0")
                    print(f"  修改: {line.strip()} -> bind-address=0.0.0.0")
                else:
                    new_lines.append(line)
            content = "\n".join(new_lines)

            # 添加用户权限（如果不存在）
            # 这需要在MySQL命令行中执行

        with open(myini, 'w', encoding='utf-8') as f:
            f.write(content)

        print("[完成] MySQL配置已修改")

    print("\n接下来需要执行以下SQL来创建远程用户：")
    print("-" * 50)
    print(f"""
-- 创建允许局域网访问的用户
CREATE USER 'root'@'%' IDENTIFIED BY '{db_password}';
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;

-- 或者修改现有用户的host限制
ALTER USER 'root'@'localhost' CREATE USER('root'@'%' IDENTIFIED BY '{db_password}');
GRANT ALL PRIVILEGES ON *.* TO 'root'@'%' WITH GRANT OPTION;
FLUSH PRIVILEGES;
    """)

    print("\n需要我执行这些SQL命令吗？(需要重启MySQL服务)")

    return True

if __name__ == "__main__":
    setup_mysql_lan_access()
