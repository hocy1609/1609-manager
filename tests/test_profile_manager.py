import unittest
from unittest.mock import MagicMock
import sys
import os

# Add parent directory to path to allow importing modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# We need to mock tkinter before importing profile_manager to avoid "TclError: no display name"
# in headless environments, though here we might have display. Better safe.
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.ttk'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

# Also mock ui_base and models if they import tk
# ui_base imports tkinter
sys.modules['ui_base'] = MagicMock()
sys.modules['dialogs'] = MagicMock()

# Now import ProfileManager
# Since we mocked dependencies, we might need to be careful if ProfileManager uses them at top level.
# ProfileManager imports:
# import tkinter as tk
# from tkinter import ttk, messagebox
# from ui_base import ...
# from models import ...
# from dialogs import ...

# We mocked them, so import should succeed.
# But we need to make sure ProfileManager class is available.
# Since we are mocking modules, we can't import the real class if it's in a file that does `from ui_base import COLORS`.
# The real profile_manager.py file will try to import COLORS from the mocked ui_base.
# The mocked ui_base should have COLORS.

mock_ui_base = MagicMock()
mock_ui_base.COLORS = {"bg_sidebar": "black", "fg_dim": "gray", "success": "green", "accent": "blue", "fg_text": "white", "danger": "red"}
sys.modules['ui_base'] = mock_ui_base

from core.profile_manager import ProfileManager

class TestProfileManager(unittest.TestCase):
    def setUp(self):
        self.mock_app = MagicMock()
        self.mock_app.profiles = []
        self.mock_app.view_map = []
        self.mock_app.lb = MagicMock()
        # Mock size for .lb.size()
        self.mock_app.lb.size.return_value = 0
        
        self.pm = ProfileManager(self.mock_app)

    def test_get_unique_categories_empty(self):
        self.mock_app.profiles = []
        cats = self.pm.get_unique_categories()
        # Expect "General" as fallback if empty or just standard behavior
        # Looking at code: if not res: res = ["General"]
        self.assertEqual(cats, ["General"])

    def test_get_unique_categories_basic(self):
        self.mock_app.profiles = [
            {"name": "P1", "category": "Mages"},
            {"name": "P2", "category": "Fighters"}
        ]
        cats = self.pm.get_unique_categories()
        # Logic: sorted(list(cats)). If General in res, move to front. If not, don't insert it unless empty?
        # Code:
        # res = sorted(list(cats))
        # if "General" in res: ... insert 0
        # elif not res: ...
        # return res
        
        # NOTE: If "General" is NOT in profiles, get_unique_categories returns strict list of categories found?
        # Let's check the code:
        # for p in profiles: cats.add(...)
        # res = sorted(...)
        # if "General" in res: ...
        # else: ... nothing happens?
        # So ["Fighters", "Mages"]
        
        self.assertEqual(cats, ["Fighters", "Mages"])

    def test_get_unique_categories_with_general(self):
        self.mock_app.profiles = [
            {"name": "P1", "category": "Mages"},
            {"name": "P2", "category": "General"},
            {"name": "P3", "category": "Rogues"}
        ]
        cats = self.pm.get_unique_categories()
        self.assertEqual(cats, ["General", "Mages", "Rogues"])

    def test_get_unique_categories_all_general(self):
        self.mock_app.profiles = [
            {"name": "P1", "category": "General"},
            {"name": "P2", "category": "General"}
        ]
        cats = self.pm.get_unique_categories()
        self.assertEqual(cats, ["General"])

if __name__ == '__main__':
    unittest.main()
