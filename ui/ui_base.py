import tkinter as tk
from tkinter import ttk
import weakref
from typing import Dict, Any, Optional, Set, List

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
    "bg_menu": "#2E333D",
}

# Font family - uses Mona Sans with Segoe UI fallback
FONT_FAMILY = "Mona Sans"

# Tooltip global toggle and ModernButton registry
TOOLTIPS_ENABLED = True
_MODERN_BUTTONS = weakref.WeakSet()
_TITLEBAR_BUTTONS = weakref.WeakSet()



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
        self._color_key: Optional[str] = None
        self._hover_key: Optional[str] = None
        self._fg_key: Optional[str] = None
        self._trace_id: Optional[str] = None
        self._tooltip_text: Optional[str] = None
        self._tooltip: Optional[Any] = None
        self._user_fg = user_fg  # Remember if user explicitly set fg
        try:
            for k, v in COLORS.items():
                if isinstance(v, str):
                    if v.lower() == (bg_color or '').lower():
                        self._color_key = k
                    if v.lower() == (hover_color or '').lower():
                        # For hover we expect key with _hover or a distinct palette entry
                        if k.endswith('_hover'):
                            self._hover_key = k
                    # Also detect semantic fg key if user_fg matches a COLORS entry
                    if user_fg and v.lower() == user_fg.lower():
                        self._fg_key = k
        except Exception:
            pass
        _MODERN_BUTTONS.add(self)
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

    def update_colors(self, colors_map: dict):
        """Remap button colors using stored semantic keys for theme switching."""
        try:
            # Remap base color if we have a semantic key
            if self._color_key and self._color_key in colors_map:
                self.bg_color = colors_map[self._color_key]
            
            # Remap hover color - prefer explicit hover key, else derive from base key
            hover_key = self._hover_key
            if not hover_key and self._color_key:
                candidate = f"{self._color_key}_hover"
                if candidate in colors_map:
                    hover_key = candidate
            if hover_key and hover_key in colors_map:
                self.hover_color = colors_map[hover_key]
            
            # Recalculate text color based on new background
            light_backgrounds = [
                colors_map.get("success"),
                colors_map.get("warning"),
                colors_map.get("accent"),
                colors_map.get("danger"),
            ]
            
            # Determine text color
            if self._user_fg and self._fg_key and self._fg_key in colors_map:
                # User specified fg that maps to a semantic key - remap it
                text_color = colors_map[self._fg_key]
            elif not self._user_fg:
                # Auto-calculate based on background brightness
                text_color = colors_map.get("text_dark") if self.bg_color in light_backgrounds else colors_map.get("fg_text")
            else:
                # User specified fg but no semantic key found - keep as is
                text_color = self.cget('fg')
            
            self.configure(
                bg=self.bg_color,
                fg=text_color,
                activebackground=self.hover_color,
                activeforeground=text_color
            )
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
            font=("Segoe Fluent Icons", 10),  # Use Segoe Fluent Icons for window controls
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


class CenterPopup(tk.Toplevel):
    """
    A Toplevel window that automatically centers itself relative to the parent window.
    """
    def __init__(self, parent, title="Popup", width=400, height=300):
        super().__init__(parent)
        self.title(title)
        self.configure(bg=COLORS["bg_root"])
        
        # Center relative to parent
        self.withdraw() # Hide initially
        self.update_idletasks() # Calculate sizes
        
        # If parent is root or has geometry, use it
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            
            x = px + (pw - width) // 2
            y = py + (ph - height) // 2
            
            # Ensure not off-screen
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, min(x, sw - width))
            y = max(0, min(y, sh - height))
            
            self.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            # Fallback to screen center
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{width}x{height}+{(sw-width)//2}+{(sh-height)//2}")
            
        self.deiconify() # Show
        self.transient(parent)
        self.grab_set()
        self.focus_set()


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

    def update_colors(self, colors_map: dict, bg_override: str = None):
        """Update colors from the provided map and redraw."""
        try:
            self._on_color = colors_map.get("accent", "#4fc3f7")
            self._off_color = colors_map.get("border", "#444444")
            self._bg_color = bg_override if bg_override else colors_map.get("bg_root", "#1e1e1e")
            
            # Update container bg
            self.configure(bg=self._bg_color)
            
            # Update canvas bg
            if hasattr(self, 'canvas') and self.canvas:
                self.canvas.configure(bg=self._bg_color)
            
            # Force redraw
            self._draw()
        except Exception:
            pass

    def _draw(self):
        """Redraw the toggle switch"""
        try:
            if not self.winfo_exists():
                return
        except Exception:
            return

        self._drawing = True
        try:
            try:
                self.canvas.delete("all")
            except tk.TclError:
                return
            
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
            # Use specific colors for knob if needed, or derived
            knob_fill = self._bg_color if is_on else COLORS.get("fg_text", "#ffffff")
            knob_outline = self._off_color
            
            self.canvas.create_oval(
                knob_x - knob_radius, self._padding, 
                knob_x + knob_radius, self._padding + 2 * radius, 
                fill=knob_fill, outline=knob_outline
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


class SectionFrame(tk.LabelFrame):
    """Styled LabelFrame with accent border for visual grouping."""
    
    def __init__(self, master, text: str = "", accent: bool = False, **kwargs):
        # Default styling
        bg = kwargs.pop("bg", COLORS.get("bg_root"))
        fg = kwargs.pop("fg", COLORS.get("fg_dim"))
        
        super().__init__(
            master,
            text=f" {text} " if text else "",
            bg=bg,
            fg=fg,
            font=(FONT_FAMILY, 10, "bold"),
            bd=1,
            relief="solid",
            **kwargs
        )
        
        self._accent = accent
        if accent:
            self.configure(
                highlightbackground=COLORS.get("accent"),
                highlightcolor=COLORS.get("accent"),
                highlightthickness=2
            )
        else:
            self.configure(
                highlightbackground=COLORS.get("border"),
                highlightcolor=COLORS.get("border"),
                highlightthickness=1
            )
    
    def set_accent(self, accent: bool):
        """Toggle accent border."""
        self._accent = accent
        if accent:
            self.configure(
                fg=COLORS.get("accent"),
                highlightbackground=COLORS.get("accent"),
                highlightcolor=COLORS.get("accent"),
                highlightthickness=2
            )

    def update_colors(self, colors: dict):
        """Update frame colors from new palette."""
        try:
            bg = colors.get("bg_root")
            fg = colors.get("accent") if self._accent else colors.get("fg_dim")
            self.configure(bg=bg, fg=fg)
            highlight = colors.get("accent") if self._accent else colors.get("border")
            self.configure(highlightbackground=highlight, highlightcolor=highlight)
        except Exception:
            pass


class Separator(tk.Frame):
    """Visual separator line (horizontal or vertical)."""
    
    def __init__(self, master, orient: str = "horizontal", color: str = None, thickness: int = 1, padding: int = 10, **kwargs):
        bg_color = color or COLORS.get("border")
        super().__init__(master, bg=bg_color, **kwargs)
        
        self._orient = orient
        self._thickness = thickness
        self._padding = padding
        
        if orient == "horizontal":
            self.configure(height=thickness)
        else:
            self.configure(width=thickness)
    
    def pack(self, cnf: dict[str, Any] | None = None, **kwargs):
        if cnf is None: cnf = {}
        if self._orient == "horizontal":
            kwargs.setdefault("fill", "x")
            kwargs.setdefault("pady", self._padding)
        else:
            kwargs.setdefault("fill", "y")
            kwargs.setdefault("padx", self._padding)
        super().pack(cnf, **kwargs)
    
    def grid(self, cnf: dict[str, Any] | None = None, **kwargs):
        if cnf is None: cnf = {}
        if self._orient == "horizontal":
            kwargs.setdefault("sticky", "ew")
            kwargs.setdefault("pady", self._padding)
        else:
            kwargs.setdefault("sticky", "ns")
            kwargs.setdefault("padx", self._padding)
        super().grid(cnf, **kwargs)


class SectionHeader(tk.Frame):
    """Header with text and underline accent."""
    
    def __init__(self, master, text: str, **kwargs):
        bg = kwargs.pop("bg", COLORS.get("bg_root"))
        super().__init__(master, bg=bg, **kwargs)
        
        self.label = tk.Label(
            self,
            text=text,
            bg=bg,
            fg=COLORS.get("fg_text"),
            font=(FONT_FAMILY, 12, "bold")
        )
        self.label.pack(anchor="w")
        
        self.underline = tk.Frame(
            self,
            bg=COLORS.get("accent"),
            height=2
        )
        self.underline.pack(fill="x", pady=(5, 0))


class CategoryIndicator(tk.Frame):
    """Colored indicator bar for category items."""
    
    def __init__(self, master, color: str = None, width: int = 4, **kwargs):
        super().__init__(master, **kwargs)
        
        self.indicator = tk.Frame(
            self,
            bg=color or COLORS.get("accent"),
            width=width
        )
        self.indicator.pack(side="left", fill="y")
        
        self.content = tk.Frame(self, bg=self.cget("bg"))
        self.content.pack(side="left", fill="both", expand=True)
    
    def set_color(self, color: str):
        self.indicator.configure(bg=color)


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
    
    # Deep Charcoal - Modern and sleek
    "dark": {
        "bg_root": "#14161B",
        "bg_panel": "#1C1F26",
        "bg_input": "#252932",
        "fg_text": "#E4E8EE",
        "fg_dim": "#94A3B8",
        "accent": "#00D2FF",        # Electric Cyan
        "accent_hover": "#00B4DB",
        "success": "#4ADE80",
        "success_hover": "#22C55E",
        "warning": "#FBBF24",
        "warning_hover": "#F59E0B",
        "danger": "#F87171",
        "danger_hover": "#EF4444",
        "border": "#2E333D",
        "header_bg": "#1C1F26",
        "header_fg": "#00D2FF",
        "text_dark": "#0F172A",
        "running_indicator": "#4ADE80",
        "offline": "#F87171",
        "title_btn_hover": "#2D333F",
        "tooltip_bg": "#0F172A",
        "bg_sidebar": "#1C1F26",
        "bg_menu": "#1C1F26",
    },
    
    # Midnight Purple - Deep and mystical
    "purple": {
        "bg_root": "#120E1A",
        "bg_panel": "#1A1626",
        "bg_input": "#231F30",
        "fg_text": "#F5F3FF",
        "fg_dim": "#A78BFA",
        "accent": "#D8B4FE",        # Soft Lavender
        "accent_hover": "#C084FC",
        "success": "#A7F3D0",
        "success_hover": "#6EE7B7",
        "warning": "#FDE68A",
        "warning_hover": "#FCD34D",
        "danger": "#FDA4AF",
        "danger_hover": "#FB7185",
        "border": "#2D283B",
        "header_bg": "#1A1626",
        "header_fg": "#D8B4FE",
        "text_dark": "#120E1A",
        "running_indicator": "#A7F3D0",
        "offline": "#FDA4AF",
        "title_btn_hover": "#2D283B",
        "tooltip_bg": "#120E1A",
        "bg_sidebar": "#1A1626",
        "bg_menu": "#1A1626",
    },
    
    # Deep Ocean - Deep blue tones
    "blue": {
        "bg_root": "#0A111A",
        "bg_panel": "#121A26",
        "bg_input": "#1B2533",
        "fg_text": "#F1F5F9",
        "fg_dim": "#7DD3FC",
        "accent": "#38BDF8",        # Sky Blue
        "accent_hover": "#0EA5E9",
        "success": "#4ADE80",
        "success_hover": "#22C55E",
        "warning": "#FBBF24",
        "warning_hover": "#F59E0B",
        "danger": "#F87171",
        "danger_hover": "#EF4444",
        "border": "#253140",
        "header_bg": "#121A26",
        "header_fg": "#38BDF8",
        "text_dark": "#0A111A",
        "running_indicator": "#4ADE80",
        "offline": "#F87171",
        "title_btn_hover": "#253140",
        "tooltip_bg": "#0A111A",
        "bg_sidebar": "#121A26",
        "bg_menu": "#121A26",
    },
    
    # === LIGHT THEMES (Refreshed/Softer) ===
    
    # Quiet White/Sand - Soft and premium
    "light": {
        "bg_root": "#F7F4EF",
        "bg_panel": "#FEFDFB",
        "bg_input": "#EFEAE2",
        "fg_text": "#334155",
        "fg_dim": "#64748B",
        "accent": "#6366F1",        # Indigo
        "accent_hover": "#4F46E5",
        "success": "#10B981",
        "success_hover": "#059669",
        "warning": "#F59E0B",
        "warning_hover": "#D97706",
        "danger": "#EF4444",
        "danger_hover": "#DC2626",
        "border": "#E5DFD3",
        "header_bg": "#FEFDFB",
        "header_fg": "#6366F1",
        "text_dark": "#1E293B",
        "running_indicator": "#10B981",
        "offline": "#EF4444",
        "title_btn_hover": "#E5DFD3",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#FEFDFB",
        "bg_menu": "#FEFDFB",
    },
    
    # Fresh Mint/Sage - Softer greens
    "mint": {
        "bg_root": "#EFF5F1",
        "bg_panel": "#F7FAF8",
        "bg_input": "#E1EBE4",
        "fg_text": "#164E63",
        "fg_dim": "#475569",
        "accent": "#2DD4BF",        # Seafoam/Teal
        "accent_hover": "#14B8A6",
        "success": "#34D399",
        "success_hover": "#10B981",
        "warning": "#FBBF24",
        "warning_hover": "#F59E0B",
        "danger": "#FB7185",
        "danger_hover": "#F43F5E",
        "border": "#D4E1D9",
        "header_bg": "#F7FAF8",
        "header_fg": "#0D9488",
        "text_dark": "#064E3B",
        "running_indicator": "#10B981",
        "offline": "#FB7185",
        "title_btn_hover": "#D4E1D9",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#F7FAF8",
        "bg_menu": "#F7FAF8",
    },
    
    # Pearl Rose - Elegant blush tones
    "rose": {
        "bg_root": "#FAF5F5",
        "bg_panel": "#FDFBFB",
        "bg_input": "#F2EAEB",
        "fg_text": "#881337",
        "fg_dim": "#BE123C",
        "accent": "#FB7185",        # Rose Pink
        "accent_hover": "#F43F5E",
        "success": "#34D399",
        "success_hover": "#10B981",
        "warning": "#FBBF24",
        "warning_hover": "#F59E0B",
        "danger": "#E11D48",
        "danger_hover": "#BE123C",
        "border": "#E9DEE0",
        "header_bg": "#FDFBFB",
        "header_fg": "#E11D48",
        "text_dark": "#4C0519",
        "running_indicator": "#34D399",
        "offline": "#E11D48",
        "title_btn_hover": "#E9DEE0",
        "tooltip_bg": "#FFFFFF",
        "bg_sidebar": "#FDFBFB",
        "bg_menu": "#FDFBFB",
    },
    
    # === SPECIAL THEMES ===
    
    # High contrast monochrome
    "bw": {
        "bg_root": "#0A0A0A",
        "bg_panel": "#171717",
        "bg_input": "#1F1F1F",
        "fg_text": "#FAFAFA",
        "fg_dim": "#A3A3A3",
        "accent": "#FAFAFA",
        "accent_hover": "#D4D4D4",
        "success": "#22C55E",
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
        "bg_menu": "#1F1F1F",
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
            font=(FONT_FAMILY, 10),
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
        # Style the dropdown list (Listbox) for Combobox - ttk.Style doesn't affect it
        if root is not None:
            root.option_add("*TCombobox*Listbox.background", COLORS["bg_input"])
            root.option_add("*TCombobox*Listbox.foreground", COLORS["fg_text"])
            root.option_add("*TCombobox*Listbox.selectBackground", COLORS["accent"])
            root.option_add("*TCombobox*Listbox.selectForeground", COLORS["text_dark"])
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
    try:
        children = widget.winfo_children()
    except Exception:
        children = []

    for child in children:
        _semantic_repaint_widget_tree(child, old, new)
