"""
Craft Manager for NWN Manager.

This module handles all crafting-related operations including:
- Potion crafting automation
- Macro recording and playback
- Craft UI helpers
"""

import os
import time
import json
import threading
import tkinter as tk
from tkinter import messagebox, filedialog
import re

from ui.ui_base import COLORS


class CraftManager:
    """
    Manages crafting operations for NWN Manager.
    
    Takes a reference to the main app to access its state and UI elements.
    """
    
    def __init__(self, app):
        """
        Initialize the CraftManager.
        
        Args:
            app: Reference to the NWNManagerApp instance
        """
        self.app = app

    def initialize_state(self):
        """Initialize craft-related state on the app (idempotent)."""
        if getattr(self.app, "_craft_state_initialized", False):
            return

        import tkinter as tk
        from app import CraftState

        self.app.craft_state = CraftState(
            running=False,
            vars={
                "open_sequence": tk.StringVar(value="F11"),
                "delay_open": tk.DoubleVar(value=4.0), # Increased delay for initial menu open
                "potion_limit": tk.IntVar(value=100),
                # Fixed delays internally: 0.2s
            },
            log_path=tk.StringVar(value=""),
            log_position=0,
            real_count=0,
            potions_count=0,
            thread=None,
            session_progress={}, 
            partial_line="",
        )
        
        # Session tracking
        self.app.craft_state.session_start_time = 0
        self.app.craft_state.original_queue = []

        # Log monitoring for potion counting
        default_log = os.path.join(
            os.path.expanduser("~"),
            "Documents",
            "Neverwinter Nights",
            "logs",
            "nwclientLog1.txt",
        )
        if os.path.exists(default_log):
            self.app.craft_state.log_path.set(default_log)

        self.load_favorites()
        self.app._craft_state_initialized = True
        self.load_presets()

    def load_presets(self):
        """Load presets from file."""
        self.presets = {}
        try:
            path = os.path.join(self.app.data_dir, "craft_presets.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.presets = json.load(f)
        except Exception as e:
            print(f"Error loading presets: {e}")

    def save_presets(self):
        """Save presets to file."""
        try:
            path = os.path.join(self.app.data_dir, "craft_presets.json")
            with open(path, "w") as f:
                json.dump(self.presets, f)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def save_current_to_preset(self, slot_idx):
        """Save current queue to preset slot (1-5)."""
        queue = self._build_craft_queue()
        # Format: list of [name, seq, count]
        # We only need seq and count to restore
        preset_data = []
        for name, seq, count in queue:
            preset_data.append({"seq": seq, "count": count})
            
        self.presets[str(slot_idx)] = preset_data
        self.save_presets()
        print(f"[Craft] Saved preset to slot {slot_idx}")
        messagebox.showinfo("Preset Saved", f"Preset saved to slot {slot_idx}!", parent=self.app.root)

    def apply_preset(self, slot_idx):
        """Load preset from slot and apply to UI."""
        idx = str(slot_idx)
        if idx not in self.presets:
            messagebox.showwarning("Preset Empty", f"Slot {slot_idx} is empty.", parent=self.app.root)
            return
            
        data = self.presets[idx]
        self._reset_queue()
        
        # Apply values
        # data is list of dicts {"seq": "...", "count": 123}
        for item in data:
            seq = item.get("seq")
            count = item.get("count", 0)
            
            if seq in self.craft_queue:
                name, var_bool, var_int, lbl = self.craft_queue[seq]
                var_int.set(count)
                # Logic to inspect count and set bool/style is in _on_quantity_change
                # but setting var_int triggers trace? 
                # Tkinter trace might trigger. Let's ensure consistency manually just in case.
                # Actually trace handles it.
                
        print(f"[Craft] Applied preset {slot_idx}")

    def load_favorites(self):
        """Load favorite potions from file."""
        self.favorites = set()
        try:
            path = os.path.join(self.app.data_dir, "craft_favorites.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    self.favorites = set(json.load(f))
        except Exception as e:
            print(f"Error loading favorites: {e}")

    def save_favorites(self):
        """Save favorite potions to file."""
        try:
            path = os.path.join(self.app.data_dir, "craft_favorites.json")
            with open(path, "w") as f:
                json.dump(list(self.favorites), f)
        except Exception as e:
            print(f"Error saving favorites: {e}")

    def toggle_favorite(self, seq, parent_frame):
        """Toggle favorite status and refresh list."""
        if seq in self.favorites:
            self.favorites.remove(seq)
        else:
            self.favorites.add(seq)
        self.save_favorites()
        self._populate_craft_list(parent_frame)
    
    def _validate_float(self, action, value_if_allowed, prior_value, text, validation_type, trigger_type, widget_name):
        """Validate float input."""
        if action == "1": # Insert
            if value_if_allowed == "":
                return True
            try:
                float(value_if_allowed)
                return True
            except ValueError:
                return False
        return True

    def _craft_row(self, parent, row, label, var):
        """Create a settings row in grid."""
        import tkinter as tk
        
        # Register validation wrapper
        vcmd = (parent.register(self._validate_float), '%d', '%P', '%s', '%S', '%v', '%V', '%W')
        
        tk.Label(parent, text=label, bg=COLORS["bg_root"], fg=COLORS["fg_dim"], anchor="w").grid(
            row=row, column=0, sticky="w", pady=2
        )
        tk.Entry(
            parent, textvariable=var, width=25, bg=COLORS["bg_input"], 
            fg=COLORS["fg_text"], relief="flat", insertbackground=COLORS["fg_text"],
            validate="key", validatecommand=vcmd
        ).grid(row=row, column=1, sticky="w", padx=(10, 0), pady=2)
    
    def _populate_craft_list(self, parent_frame):
        """Populate potion list with checkboxes and quantity sliders."""
        import tkinter as tk
        from ui.ui_base import ModernButton
        
        # Clear existing
        for widget in parent_frame.winfo_children():
            widget.destroy()
            
        self.craft_queue = {}  # sequence -> (name, var_bool, var_int, lbl)
        
        # Sort recipes: Favorites first, then Alphabetical
        sorted_recipes = sorted(
            self.app.potion_recipes,
            key=lambda x: (0 if x[1] in self.favorites else 1, x[0])
        )
        
        for name, seq in sorted_recipes:
            row = tk.Frame(parent_frame, bg=COLORS["bg_input"])
            row.pack(fill="x", padx=5, pady=2)
            
            # Favorite Button (Heart)
            is_fav = seq in self.favorites
            heart_char = "♥" if is_fav else "♡"
            heart_color = COLORS["danger"] if is_fav else COLORS["fg_dim"]
            
            btn_fav = tk.Button(
                row, text=heart_char, bg=COLORS["bg_input"], fg=heart_color,
                bd=0, activebackground=COLORS["bg_input"], activeforeground=COLORS["danger"],
                font=("Segoe UI", 12), width=3, cursor="hand2",
                command=lambda s=seq, p=parent_frame: self.toggle_favorite(s, p)
            )
            btn_fav.pack(side="left")
            
            # Checkbox (Hidden, managed by slider)
            var_bool = tk.BooleanVar(value=False)
            
            # Name
            lbl = tk.Label(
                row, text=name, bg=COLORS["bg_input"], fg=COLORS["fg_text"],
                font=("Segoe UI", 10), anchor="w"
            )
            lbl.pack(side="left", fill="x", expand=True, padx=(5, 0))
            
            # Quantity Slider (Scale) 0-99 & Entry
            var_int = tk.IntVar(value=0)
            
            # 1. Slider (Pack Right)
            scale = tk.Scale(
                row, from_=0, to=999, orient="horizontal", variable=var_int,
                bg=COLORS["bg_input"], fg=COLORS["fg_text"], troughcolor=COLORS["bg_root"],
                activebackground=COLORS["accent"],
                highlightthickness=0, length=150, showvalue=False, # Hide value on slider, use Entry
            )
            scale.pack(side="right", padx=(5, 10))
            
            # 2. Entry (Pack Right, to the left of slider)
            entry = tk.Entry(
                row, textvariable=var_int, width=4,
                bg=COLORS["bg_input"], fg=COLORS["fg_text"],
                insertbackground=COLORS["fg_text"], relief="flat",
                justify="center"
            )
            entry.pack(side="right", padx=(0, 0))
            
            # Monitor changes (trace) to auto-toggle
            var_int.trace_add("write", lambda *_: self._on_quantity_change(seq))
            
            # Save refs
            self.craft_queue[seq] = (name, var_bool, var_int, lbl)
            
            # Bind click on label/row to toggle 1/0
            def toggle(e, vi=var_int):
                if vi.get() > 0:
                    vi.set(0)
                else:
                    vi.set(1)
                
            lbl.bind("<Button-1>", toggle)

    def _on_quantity_change(self, seq):
        """Handle quantity change (slider or entry)."""
        try:
            name, var_bool, var_int, lbl = self.craft_queue[seq]
            try:
                val = var_int.get()
            except:
                val = 0
            
            if val > 0 and not var_bool.get():
                var_bool.set(True)
                self._update_label_style(lbl, True)
            elif val == 0 and var_bool.get():
                var_bool.set(False)
                self._update_label_style(lbl, False)
        except Exception:
            pass

    def _on_queue_change(self, seq):
        """Handle checkbox change."""
        name, var_bool, var_int, lbl = self.craft_queue[seq]
        
        if var_bool.get():
            if var_int.get() == 0:
                var_int.set(1) # Default to 1 if checked
            self._update_label_style(lbl, True)
        else:
            var_int.set(0) # Reset to 0 if unchecked
            self._update_label_style(lbl, False)
            
    def _update_label_style(self, lbl, active):
        if active:
            lbl.config(fg=COLORS["accent"], font=("Segoe UI", 10, "bold"))
        else:
            lbl.config(fg=COLORS["fg_text"], font=("Segoe UI", 10))

    def _reset_queue(self):
        """Reset all selections."""
        for name, var_bool, var_int, lbl in self.craft_queue.values():
            var_bool.set(False)
            var_int.set(0)
            lbl.config(fg=COLORS["fg_text"], font=("Segoe UI", 10))

    def _build_craft_queue(self):
        """Build list of (name, sequence, count) from UI."""
        queue = []
        print(f"[Craft] Building queue from {len(self.craft_queue)} items...")
        for seq, (name, var_bool, var_int, lbl) in self.craft_queue.items():
            val = var_int.get()
            if val > 0:
                print(f"[Craft] Add: {name} ({seq}) x{val}")
                queue.append((name, seq, val))
            else:
                # Debug why not added if user claims it's visible
                # Only print if var_bool is True to avoid spam
                if var_bool.get():
                     print(f"[Craft] SKIP: {name} ({seq}) - Val {val}, Bool {var_bool.get()}")
        
        print(f"[Craft] Queue built: {len(queue)} items")
        return queue
    
    def craft_start(self, resume=False):
        """Start crafting process."""
        if self.app.craft_state.running:
            return

        try:
            # Delays
            delay_open = max(0.15, self.app.craft_state.vars["delay_open"].get())
            delay_fixed = 0.2
            open_seq_str = self.app.craft_state.vars["open_sequence"].get()
            log_path = self.app.craft_state.log_path.get()
            queue = self._build_craft_queue()
            
        except Exception as e:
            self.app.log_error("craft_start_read", f"Error reading settings: {e}")
            messagebox.showerror("Error", f"Could not read settings: {e}", parent=self.app.root)
            return

        if not queue:
            self.app.craft_status_lbl.config(text="Queue Empty! Add potions.", fg=COLORS["warning"])
            messagebox.showwarning("Queue Empty", "Select potions to craft!", parent=self.app.root)
            return
            
        self.app.craft_state.running = True
        
        if not resume:
            self.app.craft_state.potions_count = 0 
            self.app.craft_state.session_progress = {} 
            self.app.craft_state.real_count = 0
            self.app.craft_state.partial_line = ""
            
        self.app.craft_btn_start.configure(state="disabled")
        self.app.craft_btn_stop.configure(state="normal")
        if hasattr(self.app, 'craft_btn_resume'):
             self.app.craft_btn_resume.configure(state="disabled")
             
        self.app.craft_status_lbl.config(text="Status: Preparing... (3s)", fg=COLORS["success"])
        if hasattr(self.app, "craft_progress"):
            self.app.craft_progress["value"] = 0
        if hasattr(self.app, "craft_details_log"):
            self.app.craft_details_log.configure(state="normal")
            self.app.craft_details_log.delete("1.0", "end")
            self.app.craft_details_log.configure(state="disabled")
        
        # Pause Global Hotkeys to prevent conflicts (e.g. "4" triggering a spell)
        if hasattr(self.app, 'multi_hotkey_manager'):
            self.app.multi_hotkey_manager.pause()

        self.app.craft_state.thread = threading.Thread(
            target=self._craft_loop, 
            args=(queue, delay_open, delay_fixed, open_seq_str, log_path),
            daemon=True
        )
        self.app.craft_state.thread.start()
    
    def craft_resume(self):
        """Resume crafting."""
        # Calculate remaining
        total_remaining = 0
        for seq, (name, var_bool, var_int, lbl) in self.craft_queue.items():
            done = self.app.craft_state.session_progress.get(seq, 0)
            current_requested = var_int.get()
            
            if done > 0:
                new_val = max(0, current_requested - done)
                var_int.set(new_val)
                if new_val == 0:
                     var_bool.set(False)
                     self._update_label_style(lbl, False)
                else:
                     var_bool.set(True)
                     self._update_label_style(lbl, True)
                total_remaining += new_val
            else:
                if var_bool.get() and var_int.get() > 0:
                     total_remaining += var_int.get()

        self.app.craft_state.session_progress = {}
        if total_remaining > 0:
            self.craft_start(resume=False)
        else:
             messagebox.showinfo("Resume", "Nothing left to craft!", parent=self.app.root)
    
    def craft_stop(self):
        """Stop crafting process."""
        print("[Craft] Stop requested")
        self.app.craft_state.running = False
        self.app.craft_status_lbl.config(text="Stopping...", fg=COLORS["warning"])
    
    def _craft_loop(self, queue, delay_open, delay_fixed, open_seq_str, log_path):
        """Main craft loop with smart retry logic."""
        from utils.win_automation import press_key_by_name
        
        # Initialize
        total_requested = sum(c for _, _, c in queue)
        open_keys = [k.strip() for k in open_seq_str.split(",") if k.strip()]
        
        # Initial Countdown
        for i in range(3, 0, -1):
            if not self.app.craft_state.running: return
            self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(
                text=f"Switch to NWN! {n}...", fg=COLORS["warning"]))
            time.sleep(1)
            
        # Init log reading
        self._init_log_reading(log_path)
        
        # Open Menu First Time
        if not self._ensure_menu_open(open_keys, delay_open):
            self.app.craft_state.running = False
            self.app.root.after(0, self._craft_reset_ui, total_requested)
            return

        self.app.craft_state.session_start_time = time.time()
        self.app.craft_state.attempts = 0 # Track total attempts including retries
        
        try:
            for name, seq, count in queue:
                if not self.app.craft_state.running: break
                
                remaining = count
                consecutive_failures = 0
                
                while remaining > 0 and self.app.craft_state.running:
                    self.app.craft_state.attempts += 1
                    
                    # Update UI Status
                    real = self.app.craft_state.real_count
                    self.app.root.after(0, lambda n=name, r=remaining, d=real: self.app.craft_status_lbl.config(
                        text=f"Crafting: {n}\nRemaining: {r}\nVerified: {d}", fg=COLORS["success"]))
                    
                    # 1. Snapshot Log
                    start_pos = self._get_log_pos()
                    
                    # 2. Execute Craft Sequence
                    self._execute_sequence(seq, delay_fixed)
                    
                    # 3. Verify Success
                    # Wait up to 3 seconds for log entry (lag buffer)
                    if self._wait_for_log_success(name, timeout=3.0, start_pos=start_pos, log_path=log_path):
                        # SUCCESS
                        remaining -= 1
                        consecutive_failures = 0
                        self.app.craft_state.real_count += 1
                        
                        # Update session progress
                        current = self.app.craft_state.session_progress.get(seq, 0)
                        self.app.craft_state.session_progress[seq] = current + 1
                        
                        # Update Progress Bar
                        total_done = self.app.craft_state.real_count
                        pct = (total_done / total_requested) * 100 if total_requested else 0
                        self.app.root.after(0, lambda p=pct: self.app.craft_progress.configure(value=p))
                        
                    else:
                        # FAILURE (Lag / Menu Closed / Wrong State)
                        consecutive_failures += 1
                        print(f"[Craft] Failure #{consecutive_failures} for {name}")
                        
                        self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
                            text=f"Lag/Miss detected! Retrying... ({consecutive_failures})", fg=COLORS["danger"]))
                        
                        # Stop if too many failures
                        if consecutive_failures >= 5:
                            print("[Craft] Too many failures. Aborting.")
                            self.app.craft_state.running = False
                            break
                            
                        # EMERGENCY RESET
                        # If we failed, likely menu is closed or stuck in submenu.
                        # Force reset to root menu.
                        self._perform_emergency_reset(open_keys, delay_open)
                        
                    # Pause between attempts
                    time.sleep(delay_fixed)

        except Exception as e:
            self.app.log_error("craft_loop", e)
        finally:
            self.app.craft_state.running = False
            self.app.root.after(0, self._craft_reset_ui, total_requested)

    def _init_log_reading(self, log_path):
        """Prepare log file for reading."""
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                    f.seek(0, 2)
                    self.app.craft_state.log_position = f.tell()
                self.app.craft_state.partial_line = ""
                self.app.craft_state.partial_line = ""
            except Exception as e:
                pass

    def _get_log_pos(self):
        """Get current log file position safely."""
        return self.app.craft_state.log_position

    def _ensure_menu_open(self, open_keys, delay):
        """Ensure menu is open by pressing keys."""
        from utils.win_automation import press_key_by_name
        print(f"[Craft] Opening menu: {open_keys}")
        for key in open_keys:
            if not self.app.craft_state.running: return False
            press_key_by_name(key)
            time.sleep(0.1)
        return self._craft_sleep(delay)

    def _execute_sequence(self, seq, delay):
        """Press craft sequence keys."""
        from utils.win_automation import press_key_by_name
        for char in seq:
            if not self.app.craft_state.running: break
            press_key_by_name(char)
            time.sleep(delay)
        
        # Confirm with '1' seems standard, add delay before confirmation?
        if self.app.craft_state.running:
            time.sleep(delay)
            press_key_by_name("1")

    def _wait_for_log_success(self, item_name, timeout, start_pos, log_path):
        """Poll log for 'Acquired Item:' for 'timeout' seconds."""
        if not log_path or not os.path.exists(log_path):
            return True # If no log, assume success (blind mode fallback)
            
        end_time = time.time() + timeout
        
        # We will search for ANY "Acquired Item" because sometimes the result name differs 
        # from the recipe name (e.g. "Heal Deadly Wounds" -> "Heal Critical Wounds").
        # Trust that if we got an item, it's the right one.
        
        while time.time() < end_time and self.app.craft_state.running:
            try:
                if not os.path.exists(log_path):
                     time.sleep(0.5)
                     continue

                with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                    f.seek(start_pos)
                    content = f.read()
                    
                    if not content:
                        time.sleep(0.1)
                        continue
                        
                    # Simple check for success marker
                    if "Acquired Item:" in content:
                        return True
                        
            except Exception as e:
                pass
                
            time.sleep(0.1)
            
        return False
            
        print(f"[Craft] Timed out waiting for {item_name}")
        return False

    def _perform_emergency_reset(self, open_keys, delay_open):
        """Force reset menu state: ESC x6, then Reopen."""
        from utils.win_automation import press_key_by_name
        
        print("[Craft] performing EMERGENCY RESET")
        
        # Mash ESC to close everything
        for _ in range(6):
            if not self.app.craft_state.running: return
            press_key_by_name("ESC")
            time.sleep(0.1)
            
        time.sleep(0.5)
        
        # Reopen
        self._ensure_menu_open(open_keys, delay_open)

    def _craft_sleep(self, seconds):
        """Sleep with interrupt check."""
        steps = int(seconds / 0.1)
        for _ in range(steps):
            if not self.app.craft_state.running:
                return False
            time.sleep(0.1)
        rem = seconds - (steps * 0.1)
        if rem > 0:
            time.sleep(rem)
        return self.app.craft_state.running

    def _craft_reset_ui(self, total_requested=0):
        """Reset craft UI after stop."""
        self.app.craft_btn_start.configure(state="normal")
        self.app.craft_btn_stop.configure(state="disabled")

        # Resume Global Hotkeys
        if hasattr(self.app, 'multi_hotkey_manager'):
            self.app.multi_hotkey_manager.resume()
        
        # Check if we can resume
        can_resume = False
        if self.app.craft_state.session_progress and self.app.craft_state.real_count < total_requested:
            can_resume = True
            
        if hasattr(self.app, 'craft_btn_resume'):
             if can_resume:
                 self.app.craft_btn_resume.configure(state="normal")
             else:
                 self.app.craft_btn_resume.configure(state="disabled")
        
        if total_requested > 0:
            real_count = self.app.craft_state.real_count
            
            msg = f"Finished! Verified: {real_count} / {total_requested}"
            if real_count < total_requested:
                 msg = f"Stopped. Verified: {real_count} / {total_requested}"
                 
            color = COLORS["success"] if (real_count >= total_requested) else COLORS["warning"]
            self.app.craft_status_lbl.config(text=msg, fg=color)
