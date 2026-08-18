"""
Full project inventory for cleanup - lists everything in root and every
subfolder of app/, so we can see exactly what's live vs. what's a
completed one-off that belongs in archive/.
"""
import os

ROOT_EXCLUDE_DIRS = {"venv", "__pycache__", ".git", "archive", "node_modules"}

def list_dir(path, label):
    print(f"\n=== {label} ===")
    if not os.path.exists(path):
        print("  (does not exist)")
        return
    items = sorted(os.listdir(path))
    for item in items:
        full = os.path.join(path, item)
        if os.path.isdir(full):
            print(f"  [DIR]  {item}/")
        else:
            size = os.path.getsize(full)
            print(f"  {item}  ({size:,} bytes)")

print("=== ROOT ===")
for item in sorted(os.listdir(".")):
    if item in ROOT_EXCLUDE_DIRS or item.startswith("."):
        continue
    full = os.path.join(".", item)
    if os.path.isdir(full):
        print(f"  [DIR]  {item}/")
    else:
        size = os.path.getsize(full)
        print(f"  {item}  ({size:,} bytes)")

list_dir("app/features", "app/features")
list_dir("app/models_ml/spread", "app/models_ml/spread")
list_dir("app/models_ml/total", "app/models_ml/total")
list_dir("app/models_ml/moneyline", "app/models_ml/moneyline")
list_dir("app/pipeline", "app/pipeline")
list_dir("archive", "archive (top level only)")