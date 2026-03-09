import os
import sys

# Mock for tk
class MockVar:
    def __init__(self, val=""): self.val = val
    def get(self): return self.val
    def set(self, val): self.val = val

import tkinter as tk
tk.StringVar = MockVar
tk.BooleanVar = MockVar

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import app
from core.models import Profile

# Set up dummy environment
doc_path = r"C:\Users\skynk\Documents\Neverwinter Nights"
profile = Profile(
    id="test_id",
    playerName="Test<User>Name",
    cdKey="11111-22222-33333-44444-55555"
)

# instantiate app
root = tk.Tk()
manager_app = app.NWNManagerApp(root)
manager_app.doc_path_var.set(doc_path)

print("Preparing profile dir...")
profile_dir = manager_app._prepare_profile_dir(doc_path, profile)

print("Created profile dir:", profile_dir)

nwn_ini = os.path.join(profile_dir, "nwn.ini")
print("\n--- generated nwn.ini ---")
if os.path.exists(nwn_ini):
    with open(nwn_ini, "r", encoding="utf-8") as f:
        print(f.read())
else:
    print("nwn.ini not found!")

print("\n--- generated nwncdkey.ini ---")
with open(os.path.join(profile_dir, "nwncdkey.ini"), "r", encoding="utf-8") as f:
    print(f.read())
    
root.destroy()
