"""
Utility: prints the exact field names for any cfbd response model, straight
from the client's own schema - no API call, no database write. Run this
BEFORE writing any new sync script to avoid field-name guessing.

Usage: python inspect_model.py <module_path> <ClassName>
Example: python inspect_model.py cfbd.models.team_ats TeamATS
"""
import sys
import importlib

module_path = sys.argv[1]
class_name = sys.argv[2]

module = importlib.import_module(module_path)
model_class = getattr(module, class_name)

schema = model_class.schema()
print(f"Fields for {class_name}:")
for field_name in schema["properties"]:
    print(f"  {field_name}")