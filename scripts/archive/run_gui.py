#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')

print("Starting inventory system...")
sys.stdout.flush()

try:
    from inventory_manager_complete import InventoryGUI
    print("InventoryGUI imported successfully")
    sys.stdout.flush()

    app = InventoryGUI()
    print("InventoryGUI created successfully")
    sys.stdout.flush()

    print("Starting mainloop...")
    sys.stdout.flush()

    app.mainloop()

    print("Mainloop ended")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()