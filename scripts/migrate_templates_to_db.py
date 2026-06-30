"""M0 迁移脚本: 把 MESSAGE_TEMPLATES_DEFAULT 41 条 builtin 写入 container_center.message_templates

幂等性: 再次跑只 UPDATE 不 INSERT (M4 要求)
- 先 DELETE 7 条 test_qa_xxx 残留 (A0.2 要求)
- INSERT 41 条, is_builtin=1, is_active=1
- 再跑只 UPDATE is_builtin/is_active, 不 INSERT
"""
import os
import sys
import json
import pymysql
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'mobile_api_ai'))
from template_engine import MESSAGE_TEMPLATES_DEFAULT

DB_CFG = {
    'host': os.getenv('MYSQL_HOST', '127.0.0.1'),
    'port': int(os.getenv('MYSQL_PORT', '3306')),
    'user': os.getenv('MYSQL_USER', 'root'),
    'password': os.getenv('MYSQL_PASSWORD', ''),
    'database': os.getenv('CONTAINER_MYSQL_DATABASE', 'container_center'),
    'charset': 'utf8mb4',
}


def main():
    conn = pymysql.connect(**DB_CFG)
    cur = conn.cursor()

    # 0. 备份 + 清 test_qa_xxx 残留 (A0.2)
    cur.execute("SHOW TABLES LIKE '_bak_message_templates_%'")
    if not cur.fetchone():
        cur.execute("""CREATE TABLE _bak_message_templates_20260612 AS
                       SELECT * FROM message_templates WHERE id LIKE 'test_qa_%%'""")
        n_bak = cur.rowcount
        conn.commit()
        print(f'[A0.2] 备份 test_qa_xxx: {n_bak} 条 → _bak_message_templates_20260612')
    cur.execute("DELETE FROM message_templates WHERE id LIKE 'test_qa_%%'")
    n_del = cur.rowcount
    conn.commit()
    print(f'[A0.2] DELETE test_qa_xxx 残留: {n_del} 条')

    # 1. INSERT 或 UPDATE 41 条 builtin (M0 + M4 幂等)
    inserted = updated = 0
    for tpl in MESSAGE_TEMPLATES_DEFAULT:
        cur.execute("SELECT id, is_builtin FROM message_templates WHERE id=%s", (tpl['id'],))
        row = cur.fetchone()
        channels_json = json.dumps(tpl.get('channels', ['wechat_group']), ensure_ascii=False)
        if row is None:
            cur.execute("""INSERT INTO message_templates
                (id, name, category, title, content, channels, msg_type, is_builtin, is_active, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 1, 1, 1)""",
                (tpl['id'], tpl['name'], tpl['category'],
                 tpl.get('title', ''), tpl['content'],
                 channels_json, 'markdown'))
            inserted += 1
        else:
            cur.execute("""UPDATE message_templates
                SET is_builtin=1, is_active=1
                WHERE id=%s""", (tpl['id'],))
            updated += 1
    conn.commit()
    print(f'[M0] INSERT {inserted} 条, UPDATE {updated} 条 (期望合计 41)')

    # 2. 端到端验证
    cur.execute("SELECT COUNT(*) FROM message_templates WHERE is_builtin=1")
    n_builtin = cur.fetchone()[0]
    cur.execute("SELECT id FROM message_templates WHERE is_builtin=1 ORDER BY id")
    ids = [r[0] for r in cur.fetchall()]

    # 期望 ids vs 实际 ids 对比
    expected_ids = {t['id'] for t in MESSAGE_TEMPLATES_DEFAULT}
    actual_ids = set(ids)
    missing = expected_ids - actual_ids
    extra = actual_ids - expected_ids

    print(f'[M0 验证] DB is_builtin=1 总数: {n_builtin} (期望 41)')
    if n_builtin != 41:
        print(f'[M0 验证] ❌ 数量不符')
    if missing:
        print(f'[M0 验证] ❌ 缺失: {sorted(missing)}')
    if extra:
        print(f'[M0 验证] ⚠️ 多余: {sorted(extra)}')
    if n_builtin == 41 and not missing and not extra:
        print(f'[M0 验证] ✅ 41/41 全部命中')

    cur.close()
    conn.close()
    return 0 if (n_builtin == 41 and not missing) else 1


if __name__ == '__main__':
    sys.exit(main())
