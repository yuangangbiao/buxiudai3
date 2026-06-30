import sys
try:
    import playwright
    print("PLAYWRIGHT_OK", playwright.__version__)
except Exception as e:
    print("PLAYWRIGHT_ERR", e)
    sys.exit(1)

try:
    from playwright.sync_api import sync_playwright
    print("SYNC_OK")
except Exception as e:
    print("SYNC_ERR", e)
    sys.exit(1)
