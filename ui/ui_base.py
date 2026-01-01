import tkinter as tk
from tkinter import ttk
import weakref

# Core color map; themes will replace these values
COLORS = {
    "bg_root": "#1E2128",
    "bg_panel": "#282C34",
    "bg_input": "#2E333D",
    "fg_text": "#E4E8EE",
    "fg_dim": "#9BA4B4",
    "accent": "#7EC8E3",
    "accent_hover": "#5AAFC7",
    "success": "#95D5B2",
    "success_hover": "#74C69D",
    "warning": "#FFD166",
    "warning_hover": "#F5C542",
    "danger": "#F28B82",
    "danger_hover": "#E66A5E",
    "border": "#3A3F4B",
    "header_bg": "#2E333D",
    "header_fg": "#7EC8E3",
    "text_dark": "#1E2128",
    "running_indicator": "#95D5B2",
    "offline": "#F28B82",
    "title_btn_hover": "#3A3F4B",
    "tooltip_bg": "#1E2128",
    "bg_sidebar": "#282C34",
}

# Tooltip global toggle and ModernButton registry
TOOLTIPS_ENABLED = True
_MODERN_BUTTONS = weakref.WeakSet()
_TITLEBAR_BUTTONS = weakref.WeakSet()


class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        try:
            x, y, _, _ = self.widget.bbox("insert")
        except Exception:
            x = y = 0
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(
            tw,
            text=self.text,
            justify="left",
            background=COLORS.get("tooltip_bg", COLORS["bg_root"]),
            foreground=COLORS.get("accent", "#88C0D0"),
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 8),
        )
        label.pack(ipadx=5, ipady=2)
        self.tooltip_window = tw

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            self.tooltip_window = None


class ModernButton(tk.Button):
    def __init__(self, master, bg_color, hover_color, tooltip: str = "", **kwargs):
        # decide text color for contrast
        user_fg = kwargs.pop("fg", None)
        if user_fg:
            text_color = user_fg
        else:
            # heuristic: light backgrounds use dark text
            light_backgrounds = [
                COLORS["success"],
                COLORS["warning"],
                COLORS["accent"],
                COLORS["danger"],
            ]
            text_color = COLORS["text_dark"] if bg_color in light_backgrounds else COLORS["fg_text"]

        super().__init__(
            master,
            bd=0,
            relief="flat",
            bg=bg_color,
            fg=text_color,
            activebackground=hover_color,
            activeforeground=text_color,
            cursor="hand2",
            **kwargs,
        )
        self.bg_color = bg_color
        self.hover_color = hover_color
        # Store semantic color key so future theme switches can remap reliably
        self._color_key = None
        self._hover_key = None
        try:
            for k, v in COLORS.items():
                if isinstance(v, str):
                    if v.lower() == (bg_color or '').lower():
                        self._color_key = k
                    if v.lower() == (hover_color or '').lower():
                        # For hover we expect key with _hover or a distinct palette entry
                        if k.endswith('_hover'):
                            self._hover_key = k
        except Exception:
            pass
        self._tooltip_text = tooltip
        self._tooltip = None
        _MODERN_BUTTONS.add(self)
        if tooltip and globals().get("TOOLTIPS_ENABLED", True):
            self._tooltip = ToolTip(self, tooltip)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _):
        try:
            self.configure(bg=self.hover_color)
        except Exception:
            pass

    def _on_leave(self, _):
        try:
            self.configure(bg=self.bg_color)
        except Exception:
            pass

    def enable_tooltip(self):
        if self._tooltip_text and not self._tooltip:
            self._tooltip = ToolTip(self, self._tooltip_text)

    def disable_tooltip(self):
        if getattr(self, "_tooltip", None):
            try:
                self._tooltip.hide_tooltip()
            except Exception:
                pass
            try:
                self._tooltip.widget.unbind("<Enter>")
                self._tooltip.widget.unbind("<Leave>")
            except Exception:
                pass


class AnimatedIconButton(ModernButton):
    """Icon button which on hover expands to show a label with a simple color fade."""
    def __init__(self, master, icon: str, label: str, base_bg: str, hover_bg: str, **kwargs):
        self.icon = icon
        self.label = label
        self._expanded = False
        self._animating = False
        self._steps = 6
        super().__init__(master, base_bg, hover_bg, text=icon, **kwargs)
        self.bind("<Enter>", self._expand_with_anim)
        self.bind("<Leave>", self._collapse_with_anim)

    def _fade_color(self, start: str, end: str, t: float) -> str:
        try:
            s = tuple(int(start[i:i+2], 16) for i in (1,3,5))
            e = tuple(int(end[i:i+2], 16) for i in (1,3,5))
            c = tuple(int(s[j] + (e[j]-s[j]) * t) for j in range(3))
            return f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"
        except Exception:
            return end

    def _expand_with_anim(self, _):
        if self._expanded:
            return
        self._expanded = True
        self._animate(True)

    def _collapse_with_anim(self, _):
        if not self._expanded:
            return
        self._expanded = False
        self._animate(False)

    def _animate(self, expanding: bool, step: int = 0):
        if step == 0:
            self._animating = True
        if step > self._steps:
            self._animating = False
            # final state
            if expanding:
                self.configure(text=f"{self.icon} {self.label}")
            else:
                self.configure(text=self.icon)
            return
        # choose colors
        start = self.bg_color if expanding else self.hover_color
        end = self.hover_color if expanding else self.bg_color
        t = step / self._steps
        new_col = self._fade_color(start, end, t)
        try:
            self.configure(bg=new_col, activebackground=new_col)
        except Exception:
            pass
        # update text mid-way for smoother feel
        if expanding and step == self._steps // 2:
            self.configure(text=f"{self.icon} {self.label}")
        if not expanding and step == self._steps // 2:
            self.configure(text=self.icon)
        # schedule next frame
        try:
            self.after(25, lambda: self._animate(expanding, step + 1))
        except Exception:
            pass
            self._tooltip = None

    def update_colors(self, colors_map: dict):
        """Remap button colors using stored semantic keys (more reliable than value comparison)."""
        try:
            # Base color
            if self._color_key and self._color_key in colors_map:
                self.bg_color = colors_map[self._color_key]
            # Hover color preference: explicit hover key else derive
            hover_key = self._hover_key
            if not hover_key and self._color_key:
                # conventional key + '_hover'
                candidate = f"{self._color_key}_hover"
                if candidate in colors_map:
                    hover_key = candidate
            if hover_key and hover_key in colors_map:
                self.hover_color = colors_map[hover_key]
            self.configure(bg=self.bg_color, activebackground=self.hover_color, fg=self.cget('fg'), activeforeground=self.cget('fg'))
        except Exception:
            pass


class TitleBarButton(tk.Button):
    def __init__(self, master, text, command, hover_color=None):
        bg = COLORS.get("bg_panel")
        fg = COLORS.get("fg_text")
        hover = hover_color or COLORS.get("title_btn_hover")
        super().__init__(
            master,
            text=text,
            command=command,
            bd=0,
            relief="flat",
            bg=bg,
            fg=fg,
            activebackground=hover,
            activeforeground=fg,
            font=("Segoe UI", 10),
            width=5,
            cursor="hand2",
        )
        self.default_bg = bg
        self.hover_color = hover
        _TITLEBAR_BUTTONS.add(self)
        self.bind("<Enter>", lambda e: self.configure(bg=self.hover_color))
        self.bind("<Leave>", lambda e: self.configure(bg=self.default_bg))

    def update_colors(self):
        try:
            self.default_bg = COLORS.get("bg_panel", self.default_bg)
            self.hover_color = COLORS.get("title_btn_hover", self.hover_color)
            self.configure(bg=self.default_bg, fg=COLORS.get("fg_text", self.cget('fg')), activebackground=self.hover_color, activeforeground=COLORS.get("fg_text", self.cget('fg')))
        except Exception:
            pass


class BaseDialog(tk.Toplevel):
    def __init__(self, parent, title: str, w: int, h: int):
        super().__init__(parent)
        self.title(title)
        self.w_req = w
        self.h_req = h
        self.configure(bg=COLORS.get("bg_root"))
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))
        self._drag_data = {"x": 0, "y": 0}
        title_bar = tk.Frame(self, bg=COLORS.get("bg_panel"), height=30)
        title_bar.pack(fill="x")
        title_bar.bind("<Button-1>", self.start_move)
        title_bar.bind("<B1-Motion>", self.do_move)
        tk.Label(title_bar, text=title, bg=COLORS.get("bg_panel"), fg=COLORS.get("fg_text")).pack(side="left", padx=10)

    def start_move(self, event):
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_data["x"])
        y = self.winfo_y() + (event.y - self._drag_data["y"])
        self.geometry(f"+{x}+{y}")

    def finalize_window(self, parent):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - self.w_req) // 2
        y = (sh - self.h_req) // 2
        self.geometry(f"{self.w_req}x{self.h_req}+{x}+{y}")
        self.lift()
        self.focus_force()
        self.after(50, self.grab_set)


class ToggleSwitch(tk.Frame):
    """Canvas-based toggle with improved visuals.

    Backed by a BooleanVar-compatible interface. Emits `<<ToggleChanged>>`.
    """

    def __init__(self, master, variable: tk.BooleanVar | None = None, *, width: int = 56, height: int = 30, on_color=None, off_color=None, padding: int = 3, command=None):
        bg_color = COLORS.get("bg_root", "#1e1e1e")
        try:
            bg_color = master.cget("bg")
        except Exception:
            pass
        super().__init__(master, bg=bg_color)
        
        self.var = variable if variable is not None else tk.BooleanVar(value=False)
        self._width = width
        self._height = height
        self._padding = padding
        self._on_color = on_color or COLORS.get("accent", "#4fc3f7")
        self._off_color = off_color or COLORS.get("border", "#444444")
        self._command = command
        self._bg_color = bg_color
        self._drawing = False  # Prevent recursive draws

        self.canvas = tk.Canvas(self, width=self._width, height=self._height, 
                                highlightthickness=0, bg=self._bg_color, cursor="hand2")
        self.canvas.pack()
        
        # Single click binding on entire canvas
        self.canvas.bind("<Button-1>", self._toggle)
        
        # Track variable changes (but avoid recursive drawing)
        self._trace_id = None
        try:
            self._trace_id = self.var.trace_add("write", self._on_var_change)
        except Exception:
            try:
                self._trace_id = self.var.trace("w", self._on_var_change)
            except Exception:
                pass

        self._draw()

    def _on_var_change(self, *args):
        """Called when variable changes externally"""
        if not self._drawing:
            self._draw()

    def _draw(self):
        """Redraw the toggle switch"""
        self._drawing = True
        try:
            self.canvas.delete("all")
            
            radius = (self._height - 2 * self._padding) // 2
            is_on = bool(self.var.get())
            
            # Background color based on state
            bg = self._on_color if is_on else self._off_color
            knob_x = (self._width - self._padding - radius) if is_on else (self._padding + radius)

            # Draw capsule shape (left circle + rectangle + right circle)
            self.canvas.create_oval(
                self._padding, self._padding, 
                self._padding + 2 * radius, self._padding + 2 * radius, 
                fill=bg, outline=bg
            )
            self.canvas.create_oval(
                self._width - self._padding - 2 * radius, self._padding, 
                self._width - self._padding, self._padding + 2 * radius, 
                fill=bg, outline=bg
            )
            self.canvas.create_rectangle(
                self._padding + radius, self._padding, 
                self._width - self._padding - radius, self._padding + 2 * radius, 
                fill=bg, outline=bg
            )

            # Draw knob
            knob_radius = radius - 2
            knob_fill = COLORS.get("bg_root", "#1e1e1e") if is_on else COLORS.get("fg_text", "#ffffff")
            self.canvas.create_oval(
                knob_x - knob_radius, self._padding, 
                knob_x + knob_radius, self._padding + 2 * radius, 
                fill=knob_fill, outline=COLORS.get("border", "#444444")
            )
        finally:
            self._drawing = False

    def _toggle(self, event=None):
        """Toggle the switch state"""
        new_value = not self.var.get()
        self.var.set(new_value)
        # _draw is called by trace, no need to call again
        
        try:
            self.event_generate("<<ToggleChanged>>")
        except Exception:
            pass
        
        if self._command:
            try:
                self._command()
            except Exception:
                pass
        
        return "break"  # Prevent event propagation

    def get(self) -> bool:
        return bool(self.var.get())

    def set(self, value: bool):
        self.var.set(bool(value))


def set_tooltips_enabled(enabled: bool):
    global TOOLTIPS_ENABLED
    TOOLTIPS_ENABLED = bool(enabled)
    for btn in list(_MODERN_BUTTONS):
        try:
            if TOOLTIPS_ENABLED:
                btn.enable_tooltip()
            else:
                btn.disable_tooltip()
        except Exception:
            pass


def bind_hover_effects(widget, normal_bg, hover_bg, normal_fg=None, hover_fg=None):
    """Utility to bind hover background/foreground changes to a widget."""
    def on_enter(e):
        try:
            widget.configure(bg=hover_bg)
            if hover_fg:
                widget.configure(fg=hover_fg)
        except Exception:
            pass
            
    def on_leave(e):
        try:
            widget.configure(bg=normal_bg)
            if normal_fg:
                widget.configure(fg=normal_fg)
        except Exception:
            pass
            
    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


# Named theme palettes
THEMES = {
    # === DARK THEMES ===
    
    # Nord-inspired dark with soft pastel accents
    "dark": {
        "bg_root": "#1E2128",
        "bg_panel": "#282C34",
        "bg_input": "#2E333D",
        "fg_text": "#E4E8EE",
        "fg_dim": "#9BA4B4",
        "accent": "#7EC8E3",        # Soft cyan accent
        "accent_hover": "#5AAFC7",
        "success": "#95D5B2",       # Pastel mint green
        "success_hover": "#74C69D",
        "warning": "#FFD166",       # Warm pastel yellow
        "warning_hover": "#F5C542",
        "danger": "#F28B82",        # Soft coral red
        "danger_hover": "#E66A5E",
        "border": "#3A3F4B",
        "header_bg": "#2E333D",
        "header_fg": "#7EC8E3",
        "text_dark": "#1E2128",
        "running_indicator": "#95D5B2",
        "offline": "#F28B82",
        "title_btn_hover": "#3A3F4B",
        "tooltip_bg": "#1E2128",
        "bg_sidebar": "#282C34",
    },
    
    # Purple/Violet night theme - soft and cozy
    "purple": {
        "bg_root": "#1A1625",
        "bg_panel": "#241E30",
        "bg_input": "#2D263B",
        "fg_text": "#EDE7F6",
        "fg_dim": "#B39DDB",
        "accent": "#CE93D8",        # Soft lavender
        "accent_hover": "#BA68C8",
        "success": "#A5D6A7",       # Soft green
        "success_hover": "#81C784",
        "warning": "#FFCC80",       # Warm peach
        "warning_hover": "#FFB74D",
        "danger": "#F48FB1",        # Soft pink
        "danger_hover": "#F06292",
        "border": "#3D3450",
        "header_bg": "#2D263B",
        "header_fg": "#CE93D8",
        "text_dark": "#1A1625",
        "running_indicator": "#A5D6A7",
        "offline": "#F48FB1",
        "title_btn_hover": "#3D3450",
        "tooltip_bg": "#1A1625",
        "bg_sidebar": "#241E30",
    },
    
    # Ocean blue dark theme
    "blue": {
        "bg_root": "#0D1B2A",
        "bg_panel": "#1B2838",
        "bg_input": "#233444",
        "fg_text": "#E0FBFC",
        "fg_dim": "#98C1D9",
        "accent": "#48CAE4",        # Bright ocean blue
        "accent_hover": "#00B4D8",
        "success": "#80ED99",       # Vibrant mint
        "success_hover": "#57CC99",
        "warning": "#FFD60A",       # Bright yellow
        "warning_hover": "#FFC300",
        "danger": "#FF6B6B",        # Coral
        "danger_hover": "#EE5A5A",
        "border": "#2C4158",
        "header_bg": "#1B2838",
        "header_fg": "#48CAE4",
        "text_dark": "#0D1B2A",
        "running_indicator": "#80ED99",
        "offline": "#FF6B6B",
        "title_btn_hover": "#2C4158",
        "tooltip_bg": "#0D1B2A",
        "bg_sidebar": "#1B2838",
    },
    
    # === LIGHT THEMES ===
    
    # Soft cream/beige light theme
    "light": {
        "bg_root": "#FAF8F5",
        "bg_panel": "#FFFFFF",
        "bg_input": "#F5F1EB",
        "fg_text": "#2D3142",
        "fg_dim": "#6B7280",
        "accent": "#6366F1",        # Indigo accent
        "accent_hover": "#4F46E5",
        "success": "#10B981",       # Emerald
        "success_hover": "#059669",
        "warning": "#F59E0B",       # Amber
        "warning_hover": "#D97706",
        "danger": "#EF4444",        # Red
        "danger_hover": "#DC2626",
        "border": "#E5E1DA",
        "header_bg": "#F5F1EB",
        "header_fg": "#6366F1",
        "text_dark": "#1F2937",
        "running_indicator": "#10B981",
        "offline": "#EF4444",
        "title_btn_hover": "#E5E1DA",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#FFFFFF",
    },
    
    # Mint/Sage light theme - fresh and clean
    "mint": {
        "bg_root": "#F0FDF4",
        "bg_panel": "#FFFFFF",
        "bg_input": "#ECFDF5",
        "fg_text": "#14532D",
        "fg_dim": "#4D7C5A",
        "accent": "#059669",        # Emerald accent
        "accent_hover": "#047857",
        "success": "#22C55E",       # Green
        "success_hover": "#16A34A",
        "warning": "#EAB308",       # Yellow
        "warning_hover": "#CA8A04",
        "danger": "#F43F5E",        # Rose
        "danger_hover": "#E11D48",
        "border": "#D1FAE5",
        "header_bg": "#ECFDF5",
        "header_fg": "#059669",
        "text_dark": "#052E16",
        "running_indicator": "#22C55E",
        "offline": "#F43F5E",
        "title_btn_hover": "#D1FAE5",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#FFFFFF",
    },
    
    # Rose/Pink light theme - warm and elegant
    "rose": {
        "bg_root": "#FFF1F2",
        "bg_panel": "#FFFFFF",
        "bg_input": "#FFE4E6",
        "fg_text": "#4C1D24",
        "fg_dim": "#9F1239",
        "accent": "#E11D48",        # Rose accent
        "accent_hover": "#BE123C",
        "success": "#34D399",       # Emerald
        "success_hover": "#10B981",
        "warning": "#FBBF24",       # Amber
        "warning_hover": "#F59E0B",
        "danger": "#DC2626",        # Red
        "danger_hover": "#B91C1C",
        "border": "#FECDD3",
        "header_bg": "#FFE4E6",
        "header_fg": "#E11D48",
        "text_dark": "#2C0A0F",
        "running_indicator": "#34D399",
        "offline": "#DC2626",
        "title_btn_hover": "#FECDD3",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#FFFFFF",
    },
    
    # === SPECIAL THEMES ===
    
    # High contrast black & white
    "bw": {
        "bg_root": "#0A0A0A",
        "bg_panel": "#171717",
        "bg_input": "#1F1F1F",
        "fg_text": "#FAFAFA",
        "fg_dim": "#A3A3A3",
        "accent": "#FAFAFA",
        "accent_hover": "#D4D4D4",
        "success": "#22C55E",       # Keep some color for clarity
        "success_hover": "#16A34A",
        "warning": "#EAB308",
        "warning_hover": "#CA8A04",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "border": "#2E2E2E",
        "header_bg": "#171717",
        "header_fg": "#FAFAFA",
        "text_dark": "#0A0A0A",
        "running_indicator": "#22C55E",
        "offline": "#EF4444",
        "title_btn_hover": "#2E2E2E",
        "tooltip_bg": "#0A0A0A",
        "bg_sidebar": "#171717",
    },
}


def setup_styles():
    """Configure base ttk styles for the application."""
    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "TCheckbutton",
        background=COLORS["bg_root"],
        foreground=COLORS["fg_text"],
        font=("Segoe UI", 10),
        focuscolor=COLORS["bg_root"],
    )

    style.map(
        "TCombobox",
        fieldbackground=[("readonly", COLORS["bg_input"])],
        selectbackground=[("readonly", COLORS["bg_input"])],
        selectforeground=[("readonly", COLORS["fg_text"])],
        background=[("readonly", COLORS["bg_panel"])],
    )

    style.configure(
        "TCombobox",
        background=COLORS["bg_panel"],
        foreground=COLORS["fg_text"],
        fieldbackground=COLORS["bg_input"],
        arrowcolor=COLORS["fg_text"],
        bordercolor=COLORS["border"],
    )


def set_theme(name: str, root: tk.Widget | None = None):
    """Apply a named theme and repaint existing widgets semantically.

    Improvements:
    - Capture previous palette so we can map old colors -> new colors, reducing flicker
      and ensuring frames that used panel/background colors receive the correct updated value.
    - Update ttk styles, ModernButtons, TitleBarButtons, and walk the widget tree performing
      semantic remapping instead of blind overwrites.
    """
    pal = THEMES.get(name)
    if not pal:
        return
    old_pal = dict(COLORS)  # snapshot before mutation
    COLORS.clear()
    COLORS.update(pal)

    # Update ttk styles that affect common widgets
    try:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "TCheckbutton",
            background=COLORS["bg_root"],
            foreground=COLORS["fg_text"],
            font=("Segoe UI", 10),
            focuscolor=COLORS["bg_root"],
        )
        style.configure(
            "TCombobox",
            background=COLORS["bg_panel"],
            foreground=COLORS["fg_text"],
            fieldbackground=COLORS["bg_input"],
            arrowcolor=COLORS["fg_text"],
            bordercolor=COLORS["border"],
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", COLORS["bg_input"])],
            selectbackground=[("readonly", COLORS["bg_input"])],
            selectforeground=[("readonly", COLORS["fg_text"])],
            background=[("readonly", COLORS["bg_panel"])],
        )
    except Exception:
        pass

    # Update registered ModernButton instances
    for btn in list(_MODERN_BUTTONS):
        try:
            btn.update_colors(COLORS)
        except Exception:
            pass
    # Update title bar buttons
    for tbtn in list(_TITLEBAR_BUTTONS):
        try:
            tbtn.update_colors()
        except Exception:
            pass

    # If a root widget was provided, walk and repaint common widget types
    if root is not None:
        try:
            _semantic_repaint_widget_tree(root, old_pal, COLORS)
        except Exception:
            pass


def _semantic_repaint_widget_tree(widget: tk.Widget, old: dict, new: dict):
    """Recursively map old palette colors to new palette colors for smoother transitions."""
    try:
        cls = widget.winfo_class().lower()
    except Exception:
        cls = ""

    try:
        # Update background for all common widgets
        if cls in ("frame", "tframe", "labelframe"):
            try:
                cur = widget.cget("bg")
                if cur.lower() == old.get("bg_panel", "").lower():
                    widget.configure(bg=new.get("bg_panel"))
                elif cur.lower() == old.get("bg_root", "").lower():
                    widget.configure(bg=new.get("bg_root"))
                elif cur.lower() == old.get("bg_input", "").lower():
                    widget.configure(bg=new.get("bg_input"))
            except Exception:
                pass
            # LabelFrame text color
            if cls == "labelframe":
                try:
                    widget.configure(fg=new.get("fg_dim"))
                except Exception:
                    pass
                    
        elif cls == "label":
            try:
                cur_bg = widget.cget("bg")
                if cur_bg.lower() == old.get("bg_panel", "").lower():
                    widget.configure(bg=new.get("bg_panel"))
                elif cur_bg.lower() == old.get("bg_root", "").lower():
                    widget.configure(bg=new.get("bg_root"))
                elif cur_bg.lower() == old.get("bg_input", "").lower():
                    widget.configure(bg=new.get("bg_input"))
            except Exception:
                pass
            try:
                cur_fg = widget.cget("fg")
                if cur_fg.lower() == old.get("fg_text", "").lower():
                    widget.configure(fg=new.get("fg_text"))
                elif cur_fg.lower() == old.get("fg_dim", "").lower():
                    widget.configure(fg=new.get("fg_dim"))
                elif cur_fg.lower() == old.get("accent", "").lower():
                    widget.configure(fg=new.get("accent"))
            except Exception:
                pass
                
        elif cls == "entry":
            try:
                widget.configure(
                    bg=new.get("bg_input"),
                    fg=new.get("fg_text"),
                    insertbackground=new.get("fg_text")
                )
            except Exception:
                pass
                
        elif cls == "listbox":
            try:
                widget.configure(
                    bg=new.get("bg_input"),
                    fg=new.get("fg_text"),
                    selectbackground=new.get("border"),
                    selectforeground=new.get("accent"),
                )
            except Exception:
                pass
                
        elif cls == "canvas":
            try:
                cur = widget.cget("bg")
                if cur.lower() == old.get("bg_root", "").lower():
                    widget.configure(bg=new.get("bg_root"))
                elif cur.lower() == old.get("bg_input", "").lower():
                    widget.configure(bg=new.get("bg_input"))
            except Exception:
                pass
                
        elif cls == "scale":
            try:
                widget.configure(
                    bg=new.get("bg_root"),
                    fg=new.get("fg_text"),
                    troughcolor=new.get("bg_input")
                )
            except Exception:
                pass
                
    except Exception:
        pass

    # Recurse into children
    for child in getattr(widget, "winfo_children", lambda: [])():
        _semantic_repaint_widget_tree(child, old, new)
