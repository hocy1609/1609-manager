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
        """
        Start crafting process.
        
        Args:
            resume (bool): If True, continues from current counts without resetting session tracking.
                           If False (default), starts fresh.
        """
        if self.app.craft_state.running:
            return

        # 1. READ ALL TKINTER VARS IN MAIN THREAD
        try:
            # Delays
            delay_open = max(0.15, self.app.craft_state.vars["delay_open"].get())
            # Fixed internal delay
            delay_fixed = 0.2
            
            # Sequence
            open_seq_str = self.app.craft_state.vars["open_sequence"].get()
            
            # Log path
            log_path = self.app.craft_state.log_path.get()
            
            # Queue
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
            self.app.craft_state.session_progress = {} # Reset session progress
            
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
        
        # Pass all safe data to thread
        self.app.craft_state.thread = threading.Thread(
            target=self._craft_loop, 
            args=(queue, delay_open, delay_fixed, open_seq_str, log_path),
            daemon=True
        )
        self.app.craft_state.thread.start()
    
    def craft_resume(self):
        """Resume crafting from where we left off."""
        # Calculate remaining items based on session_progress
        # We need to update the UI integers to reflect what's left
        
        total_remaining = 0
        
        for seq, (name, var_bool, var_int, lbl) in self.craft_queue.items():
            done = self.app.craft_state.session_progress.get(seq, 0)
            current_requested = var_int.get()
            
            if done > 0:
                # If we did some, subtract them from the request
                # But careful: 'current_requested' is what the USER sees.
                # If the user changed it while stopped, we respect that?
                # The requirement says: "check how many we crafted, subtract, and resume"
                
                # Logic:
                # 1. We had a target X. We did Y. Remaining = X - Y.
                # 2. Update var_int to (X - Y).
                # 3. If (X - Y) <= 0, uncheck.
                
                # Check if we tracked "original target" or just assume current var_int IS the target?
                # If we assume var_int hasn't changed since stop, then:
                new_val = max(0, current_requested - done)
                var_int.set(new_val)
                print(f"[Craft] Resume: {name} {current_requested} -> {new_val} (done {done})")
                
                if new_val == 0:
                     var_bool.set(False)
                     self._update_label_style(lbl, False)
                else:
                     var_bool.set(True) # Ensure checked if > 0
                     self._update_label_style(lbl, True)
                     total_remaining += new_val
            else:
                if var_bool.get() and var_int.get() > 0:
                     total_remaining += var_int.get()

        # Reset session progress for the NEW run (since we updated the UI inputs, 
        # the new run considers "0 done" for the new targets)
        # OR do we keep accumulating?
        # If we update UI, we should reset session_progress because the UI now reflects "Remaining".
        self.app.craft_state.session_progress = {}
        
        if total_remaining > 0:
            self.craft_start(resume=False) # Start fresh with new values
        else:
             messagebox.showinfo("Resume", "Nothing left to craft!", parent=self.app.root)
    
    def craft_stop(self):
        """Stop crafting process."""
        print("[Craft] Stop requested")
        self.app.craft_state.running = False
        self.app.craft_status_lbl.config(text="Останавливаем...", fg=COLORS["warning"])
    
    def _craft_loop(self, queue, delay_open, delay_fixed, open_seq_str, log_path):
        """
        Main craft loop - runs in thread.
        ALL ARGUMENTS must be plain data, NOT Tkinter vars.
        """
        from utils.win_automation import press_key_by_name
        
        # Initialize loop vars safely
        total_requested = 0
        
        try:
            # Parse open sequence
            open_keys = [k.strip() for k in open_seq_str.split(",") if k.strip()]
            
            total_requested = sum(c for _, _, c in queue)
            print(f"[Craft] Starting queue: {len(queue)} types, {total_requested} total items")
            
            # Countdown with hint to switch to NWN
            for i in range(3, 0, -1):
                if not self.app.craft_state.running:
                    return
                self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(
                    text=f"Переключись на NWN! {n}...", fg=COLORS["warning"]))
                time.sleep(1)
            
            self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
                text="Крафтим...", fg=COLORS["success"]))

            # Initialize log monitoring (file IO is safe in thread)
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                        f.seek(0, 2)
                        self.app.craft_state.log_position = f.tell()
                    self.app.craft_state.real_count = 0
                except Exception:
                    print("[Craft] Failed to init log reading")
            
            # Step 1: Open craft menu (ONCE)
            print(f"[Craft] Opening menu")
            for key in open_keys:
                if not self.app.craft_state.running:
                    break
                press_key_by_name(key)
                time.sleep(0.05) # Very fast
            
            # Wait for menu to fully open
            if self.app.craft_state.running:
                if not self._craft_sleep(delay_open):
                    return
            # Process queue

            prev_name = None



            # Fixed delay for all operations
            FIXED_DELAY = delay_fixed
            
            # Record Session Start & Queue
            self.app.craft_state.session_start_time = time.time()
            self.app.craft_state.original_queue = list(queue) # Snaphost of current request

            for name, seq, count in queue:
                if not self.app.craft_state.running:
                    break
                
                print(f"[Craft] Processing: {name} (x{count})")
                
                for i in range(count):
                    if not self.app.craft_state.running:
                        break
                    
                    # Step 1: Select potion (Full sequence)
                    # Blind Fire: No checks, just press keys
                    for char in seq:
                        if not self.app.craft_state.running:
                             break
                        press_key_by_name(char)
                        time.sleep(FIXED_DELAY)
                    
                    if not self.app.craft_state.running:
                        break
                        
                    # Confirm
                    time.sleep(FIXED_DELAY)
                    press_key_by_name("1")
                    
                    self.app.craft_state.potions_count += 1
                    
                    # Track progress per item type
                    current_progress = self.app.craft_state.session_progress.get(seq, 0)
                    self.app.craft_state.session_progress[seq] = current_progress + 1
                    
                    # LOG CHECK REMOVED - "Blind Fire"
                    # We will check logs ONLY in "Restore Missing" action after stop.
                            
                    real_c = self.app.craft_state.real_count
                    attempts = self.app.craft_state.potions_count
                    
                    # Update Progress UI
                    def update_ui_safe(p_val, d_text):
                        if hasattr(self.app, "craft_progress"):
                            self.app.craft_progress["value"] = p_val
                        if hasattr(self.app, "craft_details_log"):
                            self.app.craft_details_log.configure(state="normal")
                            self.app.craft_details_log.delete("1.0", "end")
                            self.app.craft_details_log.insert("end", d_text)
                            self.app.craft_details_log.configure(state="disabled")

                    pct = (attempts / total_requested) * 100 if total_requested > 0 else 0
                    
                    details_txt = ""
                    for q_name, q_seq, q_req in queue:
                        q_done = self.app.craft_state.session_progress.get(q_seq, 0)
                        details_txt += f"{q_name}: {q_done} / {q_req}\n"
                    
                    self.app.root.after(0, lambda n=name, r=real_c, t=total_requested, a=attempts: self.app.craft_status_lbl.config(
                        text=f"Crafting: {n}\nActual: {r} / {t} (Attempts: {a})", fg=COLORS["success"]))
                    
                    self.app.root.after(0, lambda p=pct, d=details_txt: update_ui_safe(p, d))
                    
                    # Pause between crafts
                    if not self._craft_sleep(FIXED_DELAY):
                        break

                prev_name = name

        except Exception as e:
            self.app.log_error("craft_loop", e)
        finally:
            # Press ESC to close menu
            if self.app.craft_state.running: # Only if finished naturally
                print("[Craft] Finishing: Pressing ESC")
                try:
                    press_key_by_name("ESC")
                except:
                    pass
            
            self.app.craft_state.running = False
            # Safely reset UI passing the value directly (avoids lambda closure issues)
            # Only reset if NOT stopped by error (if stopped by error, label is already set)
            # using a small delay to let error msg persist if needed, or check a flag?
            # actually _craft_reset_ui just sets button state and final text.
            # We want to keep the error text if it was an error.
            
            # Simple fix: if real_count < total and not running, it might be error or stop
            # Let's just call reset, but _craft_reset_ui needs to be smart or we just update buttons?
            
            self.app.root.after(0, self._craft_reset_ui, total_requested)

    def _craft_reset_ui(self, total_requested=0):
        """Reset craft UI after stop."""
        self.app.craft_btn_start.configure(state="normal")
        self.app.craft_btn_stop.configure(state="disabled")
        
        # Check if we can resume
        can_resume = False
        if self.app.craft_state.session_progress and self.app.craft_state.potions_count < total_requested:
            can_resume = True
            
        if hasattr(self.app, 'craft_btn_resume'):
             if can_resume:
                 self.app.craft_btn_resume.configure(state="normal")
             else:
                 self.app.craft_btn_resume.configure(state="disabled")
        
        # Only update status if we actually had a request (otherwise we overwrite "Queue Empty")
        if total_requested > 0:
            real_count = self.app.craft_state.real_count
            attempts = self.app.craft_state.potions_count
            
            msg = f"Finished! Actual: {real_count} / {total_requested} (Attempts: {attempts})"
            if attempts < total_requested: # Stopped early
                 msg = f"Stopped. Actual: {real_count} / {total_requested} (Attempts: {attempts})"
                 
            color = COLORS["success"] if (real_count >= total_requested) else COLORS["warning"]
            
            self.app.craft_status_lbl.config(text=msg, fg=color)
    
    def restore_missing_items(self):
        """
        Scans the log from session_start_time to now.
        Counts how many of each item in original_queue were actually crafted.
        Updates the app's craft queue with the difference (Missing items).
        """
        log_path = self.app.craft_state.log_path.get()
        if not log_path or not os.path.exists(log_path):
            self.app.log_error("Restore", "Log file not found or selected.")
            return

        start_time = self.app.craft_state.session_start_time
        original_request = self.app.craft_state.original_queue
        
        if not original_request or start_time == 0:
            self.app.log_error("Restore", "No previous session data found.")
            return

        print(f"[Restore] Scanning log since {time.ctime(start_time)}...")
        
        # 1. Parse Log for "Acquired Item: ... {Potion Name}"
        # We need a map of PotionName -> Count Crafted
        crafted_counts = {}
        
        try:
            with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                f.seek(self.app.craft_state.log_position) 
                
                for line in f:
                    if "Acquired Item:" in line:
                        parts = line.split("Acquired Item:")
                        if len(parts) > 1:
                            item_text = parts[1].strip()
                            # Loose match
                            for q_name, q_seq, q_req in original_request:
                                if q_name.lower() in item_text.lower():
                                    crafted_counts[q_seq] = crafted_counts.get(q_seq, 0) + 1
                                    pass

        except Exception as e:
            self.app.log_error("Restore", f"Error parsing log: {e}")
            return

        # 2. Calculate Missing
        new_queue = []
        report = []
        
        total_missing = 0
        
        for name, seq, req_count in original_request:
            actual = crafted_counts.get(seq, 0)
            missing = max(0, req_count - actual)
            
            report.append(f"{name}: Req {req_count}, Done {actual}, Missing {missing}")
            
            if missing > 0:
                new_queue.append((name, seq, missing, False)) # Name, Seq, Count, Active
                total_missing += missing

        print("[Restore] Report:\n" + "\n".join(report))

        # 3. Update UI
        if total_missing == 0:
            self.app.craft_status_lbl.config(text="All items accounted for!", fg=COLORS["success"])
        else:
            # Update internal queue (bound to UI)
            self._update_queue_from_restore(new_queue)
            
            self.app.craft_status_lbl.config(
                text=f"Restored {total_missing} missing items.\nCheck queue and Start.", 
                fg=COLORS["warning"]
            )

    def _update_queue_from_restore(self, new_queue_data):
        """
        Update vars in craft_queue based on restore data.
        new_queue_data: list of (name, seq, count, active)
        """
        # 1. Reset all to 0
        for name, var_bool, var_int, lbl in self.craft_queue.values():
            var_int.set(0)
            var_bool.set(False)
            self._update_label_style(lbl, False)
            
        # 2. Set restored values
        for _, seq, count, _ in new_queue_data:
            if seq in self.craft_queue:
                name, var_bool, var_int, lbl = self.craft_queue[seq]
                var_int.set(count)
                var_bool.set(True)
                self._update_label_style(lbl, True)

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
    
    def _check_craft_log(self, log_path, expected_names=None):
        """Check log file for Acquired Item entries and validate item name."""
        import re
        
        if not log_path or not os.path.exists(log_path):
            return 0, None
        
        count_increase = 0
        error_msg = None
        
        try:
            with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                f.seek(self.app.craft_state.log_position)
                new_content = f.read()
                self.app.craft_state.log_position = f.tell()
                
                # Check each line for "Acquired Item:"
                for line in new_content.splitlines():
                    if "Acquired Item:" in line:
                        # Extract item name: "Acquired Item: Item Name"
                        # Handle varied whitespace
                        match = re.search(r'Acquired Item:\s*(.+)', line, re.IGNORECASE)
                        if match:
                            item_name = match.group(1).strip()
                            
                            # Clean up quantity if present e.g. "Item Name (2)" - though usually 1 by 1
                            # But NWN log usually just says "Acquired Item: Potion Name"
                            
                            if expected_names:
                                # Normalize for comparison
                                item_name_lower = item_name.lower()
                                norm_item = item_name_lower.replace("`", "").replace("'", "")
                                
                                match_found = False
                                for expected_name in expected_names:
                                    norm_expect = expected_name.lower().replace("`", "").replace("'", "")
                                
                                    # Aliases for known mismatches (Menu Name -> Log Name partial)
                                    aliases = {
                                        # "menu key": "log value"
                                        "смертельных ран": "критических ран", # Critical Wounds
                                    }
                                    
                                    # Check aliases
                                    matched_alias = False
                                    for menu_key, log_val in aliases.items():
                                        if menu_key in norm_expect and log_val in norm_item:
                                            matched_alias = True
                                            break
                                    
                                    # Allow match if expected is substring of acquired (e.g. Log has extra " (2)")
                                    # BUT DO NOT allow acquired in expected (e.g. Log "Heal" should not match Expected "Heal Serious")
                                    if norm_expect in norm_item or matched_alias:
                                        match_found = True
                                        break
                                
                                if match_found:
                                    count_increase += 1
                                    print(f"[Craft] MATCH: '{item_name}' matches expectation")
                                else:
                                    # MISMATCH: Just warn, do NOT stop.
                                    print(f"[Craft] MISMATCH: Expected one of {expected_names}, got '{item_name}'")
                                    # Log mismatch but DO NOT STOP.
                                    error_msg = f"Mismatch: Got '{item_name}'"
                            else:
                                count_increase += 1
                                
                if count_increase > 0:
                     self.app.craft_state.real_count += count_increase
                     print(f"[Craft] Found {count_increase} items, total: {self.app.craft_state.real_count}")
                     
        except Exception as e:
            print(f"[Craft] Log read error: {e}")
        
        return count_increase, error_msg

    def _craft_loop(self, queue, delay_open, delay_fixed, open_seq_str, log_path):
        """
        Main craft loop - runs in thread.
        ALL ARGUMENTS must be plain data, NOT Tkinter vars.
        """
        from utils.win_automation import press_key_by_name
        
        # Initialize loop vars safely
        total_requested = 0
        
        try:
            # Parse open sequence
            open_keys = [k.strip() for k in open_seq_str.split(",") if k.strip()]
            
            total_requested = sum(c for _, _, c in queue)
            print(f"[Craft] Starting queue: {len(queue)} types, {total_requested} total items")
            
            # Countdown with hint to switch to NWN
            for i in range(3, 0, -1):
                if not self.app.craft_state.running:
                    return
                self.app.root.after(0, lambda n=i: self.app.craft_status_lbl.config(
                    text=f"Переключись на NWN! {n}...", fg=COLORS["warning"]))
                time.sleep(1)
            
            self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
                text="Крафтим...", fg=COLORS["success"]))

            # Initialize log monitoring (file IO is safe in thread)
            if log_path and os.path.exists(log_path):
                try:
                    with open(log_path, 'r', encoding='cp1251', errors='ignore') as f:
                        f.seek(0, 2)
                        self.app.craft_state.log_position = f.tell()
                    self.app.craft_state.real_count = 0
                except Exception:
                    print("[Craft] Failed to init log reading")
            
            # Step 1: Open craft menu (ONCE)
            self._open_craft_menu(open_keys, delay_open)
            
            # Fixed delay for all operations
            FIXED_DELAY = delay_fixed
            
            # Record Session Start & Queue
            self.app.craft_state.session_start_time = time.time()
            self.app.craft_state.original_queue = list(queue)

            for name, seq, target_count in queue:
                if not self.app.craft_state.running:
                    break
                
                print(f"[Craft] Processing: {name} (Target: {target_count})")
                
                items_crafted_in_batch = 0
                
                while items_crafted_in_batch < target_count:
                    if not self.app.craft_state.running:
                        break
                    
                    # --- ATTEMPT CRAFT ---
                    # Blind Fire sequence
                    for char in seq:
                        if not self.app.craft_state.running: break
                        press_key_by_name(char)
                        time.sleep(FIXED_DELAY)
                    
                    if not self.app.craft_state.running: break
                        
                    # Confirm
                    time.sleep(FIXED_DELAY)
                    press_key_by_name("1")
                    
                    self.app.craft_state.potions_count += 1
                    
                    # --- VERIFY ---
                    # Wait up to 3.0s for log entry
                    verified = self._wait_for_log_confirmation(log_path, [name], timeout=3.0)
                    
                    if verified:
                        # SUCCESS
                        items_crafted_in_batch += 1
                        current_progress = self.app.craft_state.session_progress.get(seq, 0)
                        self.app.craft_state.session_progress[seq] = current_progress + 1
                        
                        # Note: real_count is incremented inside _check_craft_log called by _wait_for_log_confirmation
                        
                        self._update_progress_ui(queue, total_requested, name)
                        
                        if items_crafted_in_batch < target_count:
                             if not self._craft_sleep(FIXED_DELAY): break
                    else:
                        # FAILURE / LAG
                        print(f"[Craft] Failed to verify {name}. Retrying/Resetting...")
                        if not self.app.craft_state.running: break
                        
                        # Reset Menu
                        self._perform_menu_reset(open_keys, delay_open)
                        # Loop will continue and retry the same item because items_crafted_in_batch didn't increment

        except Exception as e:
            self.app.log_error("craft_loop", e)
        finally:
            # Press ESC to close menu
            if self.app.craft_state.running: # Only if finished naturally
                print("[Craft] Finishing: Pressing ESC")
                try:
                    press_key_by_name("ESC")
                except:
                    pass
            
            self.app.craft_state.running = False
            self.app.root.after(0, self._craft_reset_ui, total_requested)

    def _open_craft_menu(self, open_keys, delay_open):
        """Helper to open craft menu."""
        from utils.win_automation import press_key_by_name
        print(f"[Craft] Opening menu")
        for key in open_keys:
            if not self.app.craft_state.running: return
            press_key_by_name(key)
            time.sleep(0.05)
        
        if self.app.craft_state.running:
            self._craft_sleep(delay_open)

    def _perform_menu_reset(self, open_keys, delay_open):
        """Close and reopen menu to reset state."""
        from utils.win_automation import press_key_by_name
        if not self.app.craft_state.running: return
        
        print("[Craft] Performing Menu Reset...")
        self.app.root.after(0, lambda: self.app.craft_status_lbl.config(
            text="Lag detected. Resetting menu...", fg=COLORS["warning"]))
            
        press_key_by_name("ESC")
        time.sleep(1.0)
        press_key_by_name("ESC") # Double tap safe
        time.sleep(1.0)
        
        self._open_craft_menu(open_keys, delay_open)
        
    def _wait_for_log_confirmation(self, log_path, expected_names, timeout=3.0):
        """Poll log for confirmation."""
        # expected_names is list of possible names
        start = time.time()
        while time.time() - start < timeout:
            if not self.app.craft_state.running: return False
            
            count, _ = self._check_craft_log(log_path, expected_names)
            if count > 0:
                return True
            time.sleep(0.2)
        return False

    def _update_progress_ui(self, queue, total_requested, current_name):
        """Update Status and Details UI."""
        real_c = self.app.craft_state.real_count
        attempts = self.app.craft_state.potions_count
        
        pct = (real_c / total_requested) * 100 if total_requested > 0 else 0
        
        details_txt = ""
        for q_name, q_seq, q_req in queue:
            q_done = self.app.craft_state.session_progress.get(q_seq, 0)
            details_txt += f"{q_name}: {q_done} / {q_req}\n"
        
        def update_ui_safe(p_val, d_text):
            if hasattr(self.app, "craft_progress"):
                self.app.craft_progress["value"] = p_val
            if hasattr(self.app, "craft_details_log"):
                self.app.craft_details_log.configure(state="normal")
                self.app.craft_details_log.delete("1.0", "end")
                self.app.craft_details_log.insert("end", d_text)
                self.app.craft_details_log.configure(state="disabled")

        self.app.root.after(0, lambda n=current_name, r=real_c, t=total_requested, a=attempts: self.app.craft_status_lbl.config(
            text=f"Crafting: {n}\nActual: {r} / {t} (Attempts: {a})", fg=COLORS["success"]))
        
        self.app.root.after(0, lambda p=pct, d=details_txt: update_ui_safe(p, d))
