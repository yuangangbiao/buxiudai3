# -*- coding: utf-8 -*-
import os
import sys
import json

def test_config_path():
    print("Testing config file path...")
    
    # 检查运行环境
    if hasattr(sys, '_MEIPASS'):
        print(f"Running in PyInstaller EXE: {sys._MEIPASS}")
        app_dir = os.path.dirname(sys.executable)
    else:
        print(f"Running in Python")
        app_dir = os.path.dirname(__file__)
    
    print(f"App directory: {app_dir}")
    print(f"Current working directory: {os.getcwd()}")
    
    config_file = os.path.join(app_dir, "inventory_config.json")
    print(f"Config file path: {config_file}")
    print(f"Config file exists: {os.path.exists(config_file)}")
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                db_host = config.get("database", {}).get("host", "NOT FOUND")
                print(f"Database host from config: {db_host}")
        except Exception as e:
            print(f"Error reading config: {e}")

if __name__ == "__main__":
    test_config_path()
    input("Press Enter to exit...")