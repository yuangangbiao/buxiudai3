# -*- coding: utf-8 -*-
import os

myini = r"D:\mysql-8.0.46-winx64\my.ini"

with open(myini, 'r', encoding='utf-8') as f:
    content = f.read()

print("Before:", content[:300])

content = content.replace("bind-address=127.0.0.1", "bind-address=0.0.0.0")

with open(myini, 'w', encoding='utf-8') as f:
    f.write(content)

print("\nAfter:", content[:300])
print("\n[OK] MySQL bind-address changed to 0.0.0.0")
print("Now restart MySQL service for changes to take effect.")
