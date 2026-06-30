import py_compile, sys

files = [
    'mobile_api_ai/bots/app_bot.py',
    'mobile_api_ai/bots/group_bot.py',
]
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f'{f}: OK')
    except py_compile.PyCompileError as e:
        print(f'{f}: ERROR - {e}')
        sys.exit(1)
