# -*- coding: utf-8 -*-
"""
直接查询数据库查看原始数据
"""
import sqlite3
import os

DB_PATH = r'd:\yuan\不锈钢网带跟单3.0\mobile_api_ai\wechat_container.db'

def main():
    print('=' * 60)
    print('直接查询数据库 - 原始数据')
    print('=' * 60)
    print()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 查询所有记录
    cursor.execute('SELECT * FROM data_packages ORDER BY created_at DESC LIMIT 10')
    rows = cursor.fetchall()

    print(f'总记录数: {len(rows)}\n')

    for i, row in enumerate(rows, 1):
        print(f'--- 记录 {i} ---')
        print(f'ID: {row["id"]}')
        print(f'Data Type: {row["data_type"]}')
        print(f'Title: {row["title"]}')
        print(f'Status: {row["status"]}')
        print(f'Content: {row["content"]}')
        print(f'Created: {row["created_at"]}')
        print()

    conn.close()

if __name__ == '__main__':
    main()
