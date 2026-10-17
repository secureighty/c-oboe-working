from pathlib import Path
from math import ceil, hypot
import json
import tkinter as tk
from tkinter import font
import random
from PIL import Image, ImageTk


ACTIVITIES = {
    "Working": "Working",
    "Eating": "Eating",
    "Project Dev": "Project Dev",
    "Dicking Around": "Dicking Around",
}
IMAGE_EXTENSIONS = {".gif", ".png", ".ppm", ".pgm"}
GRADIENT_STOPS = (
    (0, (255, 0, 0)),
    (10, (255, 154, 0)),
    (20, (208, 222, 33)),
    (30, (79, 220, 74)),
    (40, (63, 218, 216)),
    (50, (47, 201, 226)),
    (60, (28, 127, 238)),
    (70, (95, 21, 242)),
    (80, (186, 12, 248)),
    (90, (251, 7, 217)),
    (100, (255, 0, 0)),
)


class GradientPanel(tk.Label):
    def __init__(self, master):
        super().__init__(master, bd=0, highlightthickness=0, anchor="nw")
        self._gradient_photo = None
        self._gradient_image = None
        self._gradient_job = None
        self.bind("<Configure>", self._schedule_gradient)

    def _schedule_gradient(self, event=None):
        if self._gradient_job is not None:
            self.after_cancel(self._gradient_job)
        self._gradient_job = self.after_idle(self._render_gradient)

    def _render_gradient(self):
        self._gradient_job = None
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        root = self.winfo_toplevel()
        root_width = max(1, root.winfo_width())
        root_height = max(1, root.winfo_height())
        left = self.winfo_rootx() - root.winfo_rootx()
        top = self.winfo_rooty() - root.winfo_rooty()
        diagonal_width = max(1, root_width - 1)
        diagonal_height = max(1, root_height - 1)
        diagonal_squared = diagonal_width**2 + diagonal_height**2
        strip_length = max(2, ceil(hypot(diagonal_width, diagonal_height)) + 1)
        strip = Image.new("RGB", (1, strip_length))
        pixels = strip.load()

        for index in range(strip_length):
            position = 100 * index / (strip_length - 1)
            for stop_index in range(len(GRADIENT_STOPS) - 1):
                start, start_color = GRADIENT_STOPS[stop_index]
                end, end_color = GRADIENT_STOPS[stop_index + 1]
                if position <= end:
                    fraction = (position - start) / (end - start)
                    pixels[0, index] = tuple(
                        round(first + (last - first) * fraction)
                        for first, last in zip(start_color, end_color)
                    )
                    break

        scale = (strip_length - 1) / diagonal_squared
        gradient = strip.transform(
            (width, height),
            Image.Transform.AFFINE,
            (
                0,
                0,
                0,
                diagonal_width * scale,
                diagonal_height * scale,
                (left * diagonal_width + top * diagonal_height) * scale,
            ),
            resample=Image.Resampling.BILINEAR,
        )
        self._gradient_image = gradient
        self._gradient_photo = ImageTk.PhotoImage(gradient, master=self)
        self.configure(image=self._gradient_photo)


class Workagochi:
    def __init__(self, root):
        self.root = root
        self.root.title("c_Oboe_working")
        asset_root = Path(__file__).resolve().parent
        if self.root.tk.call("tk", "windowingsystem") == "win32":
            self.root.iconbitmap(default=str(asset_root / "oboe.ico"))
        else:
            self.window_icon = tk.PhotoImage(master=self.root, file=str(asset_root / "oboe.png"))
            self.root.iconphoto(True, self.window_icon)
        self.root.geometry("760x570")
        self.root.minsize(760, 500)
        self.root.configure(bg="#f4f2eb")
        self.background = GradientPanel(self.root)
        self.background.place(x=0, y=0, relwidth=1, relheight=1)
        self.background.lower()
        self.colors = {"paper": "#fffdf7", "green": "#4e795f", "green_dark": "#315941", "ink": "#25352e", "line": "#dce2d7"}
        self.animation_root = Path(__file__).resolve().parent / "animations"
        self.checklist_path = Path(__file__).resolve().parent / "checklist.json"
        self.saved_checklist = self._load_checklist()
        self.checklist_items = []
        self.selected_activity = None
        self.button_widgets = {}
        self.animation_frames = []
        self.frame_index = 0
        self.scaled_animation_image = None
        self.animation_resize_job = None
        self.last_animation_render_key = None
        self._build_ui()
        self.set_activity("Dicking Around")
        self.root.after(1000, self._advance_animation)

    def _build_ui(self):
        body_font = font.Font(family="Segoe UI", size=10)
        self.checklist_font = body_font

        activity_bar = GradientPanel(self.root)
        activity_bar.pack(fill="x", padx=24, pady=(22, 8))
        for activity in ACTIVITIES:
            button = tk.Button(
                activity_bar,
                text=activity,
                command=lambda name=activity: self.set_activity(name),
                font=body_font,
                relief="flat",
                bd=0,
                padx=13,
                pady=10,
                cursor="hand2",
                bg=self.colors["paper"],
                fg=self.colors["ink"],
                activebackground=self.colors["green_dark"],
                activeforeground="white",
                highlightthickness=1,
                highlightbackground=self.colors["line"],
            )
            button.pack(side="left", fill="x", expand=True, padx=5)
            self.button_widgets[activity] = button

        content = GradientPanel(self.root)
        content.pack(fill="both", expand=True, padx=24, pady=(8, 24))

        self.animation_pane = GradientPanel(content)
        self.animation_pane.bind("<Configure>", self._print_animation_label_size, add="+")
        self.animation_label = tk.Label(self.animation_pane, bg="#f4f2eb", bd=0)
        self.animation_label.place(relx=0.5, rely=0.5, anchor="center")

        checklist = tk.Frame(
            content,
            bg=self.colors["paper"],
            width=300,
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        )
        checklist.pack(side="right", fill="y", padx=(14, 0))
        checklist.pack_propagate(False)
        self.animation_pane.pack(side="left", fill="both", expand=True)

        tk.Label(
            checklist,
            text="Checklist",
            font=font.Font(family="Segoe UI", size=12, weight="bold"),
            fg=self.colors["ink"],
            bg=self.colors["paper"],
            anchor="w",
        ).pack(fill="x", padx=14, pady=(15, 10))

        checklist_list = tk.Frame(checklist, bg=self.colors["paper"])
        checklist_list.pack(fill="both", expand=True, padx=10)
        self.checklist_canvas = tk.Canvas(
            checklist_list,
            bg=self.colors["paper"],
            bd=0,
            highlightthickness=0,
        )
        checklist_scrollbar = tk.Scrollbar(
            checklist_list,
            orient="vertical",
            command=self.checklist_canvas.yview,
        )
        self.checklist_canvas.configure(yscrollcommand=checklist_scrollbar.set)
        self.checklist_canvas.pack(side="left", fill="both", expand=True)
        checklist_scrollbar.pack(side="right", fill="y")
        self.checklist_rows = tk.Frame(self.checklist_canvas, bg=self.colors["paper"])
        self.checklist_rows_window = self.checklist_canvas.create_window(
            (0, 0),
            window=self.checklist_rows,
            anchor="nw",
        )
        self.checklist_rows.bind("<Configure>", self._update_checklist_scroll_region)
        self.checklist_canvas.bind("<Configure>", self._resize_checklist_rows)
        self.checklist_entries = []
        tk.Button(
            checklist,
            text="Add item",
            command=self._add_checklist_item_from_button,
            font=body_font,
            relief="flat",
            bd=0,
            padx=10,
            pady=7,
            cursor="hand2",
            bg=self.colors["paper"],
            fg=self.colors["green_dark"],
            activebackground=self.colors["paper"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
        ).pack(anchor="w", padx=14, pady=(10, 0))

        for item in self.saved_checklist:
            self._add_checklist_item(item["text"], item["done"])
        self.root.bind_all("<Button-1>", self._on_checklist_mouse_click, add="+")

    def _on_checklist_mouse_click(self, event):
        clicked_textbox = event.widget if event.widget in self.checklist_entries else None
        for entry in self.checklist_entries:
            if entry is not clicked_textbox:
                entry.tag_remove("sel", "1.0", "end")

        if clicked_textbox is None and self.root.focus_get() in self.checklist_entries:
            self.root.focus_set()

    def _print_animation_label_size(self, event):
        if self.animation_resize_job is not None:
            self.root.after_cancel(self.animation_resize_job)
        self.animation_resize_job = self.root.after_idle(self._finish_animation_resize)

    def _finish_animation_resize(self):
        self.animation_resize_job = None
        print(
            f"Animation label size: {self.animation_label.winfo_width()}x"
            f"{self.animation_label.winfo_height()}"
        )
        self._resize_animation_frame()

    def _load_checklist(self):
        try:
            saved_items = json.loads(self.checklist_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            saved_items = []

        if isinstance(saved_items, list):
            items = [
                {"text": str(item.get("text", "")), "done": item.get("done") is True}
                for item in saved_items
                if isinstance(item, dict)
            ]
            if items:
                return items
        return [{"text": "", "done": False}]

    def _save_checklist(self):
        self.checklist_path.write_text(
            json.dumps(
                [
                    {"text": item["text"].get(), "done": item["done"]}
                    for item in self.checklist_items
                ],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _update_checklist_scroll_region(self, event=None):
        self.checklist_canvas.configure(scrollregion=self.checklist_canvas.bbox("all"))

    def _resize_checklist_rows(self, event):
        self.checklist_canvas.itemconfigure(self.checklist_rows_window, width=event.width)

    def _add_checklist_item(self, text="", done=False, index=None):
        row = tk.Frame(self.checklist_rows, bg=self.colors["paper"])
        item = {"text": tk.StringVar(master=self.root, value=text), "done": done, "row": row}
        insert_index = len(self.checklist_items) if index is None else index
        next_item = self.checklist_items[insert_index] if insert_index < len(self.checklist_items) else None
        self.checklist_items.insert(insert_index, item)
        if next_item is None:
            row.pack(fill="x", pady=4)
        else:
            row.pack(fill="x", pady=4, before=next_item["row"])
        toggle = tk.Button(
            row,
            text="✅" if done else "⬜",
            command=lambda: self._toggle_checklist_item(item, toggle),
            font=font.Font(family="Segoe UI Emoji", size=12),
            relief="flat",
            bd=0,
            width=3,
            cursor="hand2",
            bg=self.colors["paper"],
            activebackground=self.colors["paper"],
            highlightthickness=0,
        )
        toggle.pack(side="left")
        toggle.bind(
            "<Return>",
            lambda event, current_item=item: self._add_checklist_item_on_enter(event, current_item),
        )
        delete_button = tk.Button(
            row,
            text="🗑️",
            command=lambda current_item=item: self._delete_checklist_item(current_item),
            font=font.Font(family="Segoe UI Emoji", size=12),
            relief="flat",
            bd=0,
            width=3,
            cursor="hand2",
            bg=self.colors["paper"],
            activebackground=self.colors["paper"],
            highlightthickness=0,
        )
        delete_button.pack(side="right")

        entry = tk.Text(
            row,
            wrap="word",
            height=1,
            font=self.checklist_font,
            relief="flat",
            bd=0,
            bg="#f4f2eb",
            fg=self.colors["ink"],
            insertbackground=self.colors["ink"],
            highlightthickness=1,
            highlightbackground=self.colors["line"],
            highlightcolor=self.colors["green"],
        )
        entry.insert("1.0", text)
        entry.edit_modified(False)
        entry.pack(side="left", fill="x", expand=True, ipady=7)
        item["entry"] = entry
        entry.bind("<<Modified>>", self._on_checklist_text_modified)
        entry.bind("<Configure>", self._on_checklist_textbox_configure)
        entry.bind("<Control-a>", self._select_checklist_text)
        entry.bind("<Control-A>", self._select_checklist_text)
        entry.bind("<Control-Return>", self._insert_checklist_newline)
        entry.bind(
            "<Return>",
            lambda event, current_item=item: self._add_checklist_item_on_enter(event, current_item),
        )
        self.checklist_entries.insert(insert_index, entry)
        self._schedule_checklist_text_height(entry)
        return entry

    def _on_checklist_text_modified(self, event):
        entry = event.widget
        if not entry.edit_modified():
            return

        item = next((item for item in self.checklist_items if item["entry"] is entry), None)
        if item is not None:
            item["text"].set(entry.get("1.0", "end-1c"))
        entry.edit_modified(False)
        self._schedule_checklist_text_height(entry)
        self._save_checklist()

    def _on_checklist_textbox_configure(self, event):
        self._schedule_checklist_text_height(event.widget)

    def _schedule_checklist_text_height(self, entry):
        if getattr(entry, "height_update_job", None) is None:
            entry.height_update_job = self.root.after_idle(
                lambda current_entry=entry: self._set_checklist_text_height(current_entry)
            )

    def _insert_checklist_newline(self, event):
        event.widget.insert("insert", "\n")
        event.widget.see("insert")
        return "break"

    def _select_checklist_text(self, event):
        entry = event.widget
        entry.tag_add("sel", "1.0", "end-1c")
        entry.mark_set("insert", "end-1c")
        return "break"

    def _set_checklist_text_height(self, entry):
        entry.height_update_job = None
        if not entry.winfo_exists():
            return
        if entry.winfo_width() <= 1:
            return

        display_lines = entry.count("1.0", "end", "displaylines")
        desired_height = max(1, display_lines[0] if display_lines else 1)
        if int(entry.cget("height")) != desired_height:
            entry.configure(height=desired_height)

    def _add_checklist_item_from_button(self):
        entry = self._add_checklist_item()
        self._save_checklist()
        entry.focus_set()

    def _add_checklist_item_on_enter(self, event, item):
        try:
            item_index = self.checklist_items.index(item)
        except ValueError:
            return None

        entry = self._add_checklist_item(index=item_index + 1)
        self._save_checklist()
        entry.focus_set()
        return "break"

    def _toggle_checklist_item(self, item, button):
        item["done"] = not item["done"]
        button.configure(text="✅" if item["done"] else "⬜")
        self._save_checklist()

    def _delete_checklist_item(self, item):
        if item not in self.checklist_items:
            return

        item["row"].destroy()
        self.checklist_items.remove(item)
        self.checklist_entries = [current["entry"] for current in self.checklist_items]
        self._save_checklist()

    def set_activity(self, activity):
        self.selected_activity = activity
        self.animation_frames = []
        self.frame_index = 0
        self.last_animation_render_key = None
        folder = self.animation_root / ACTIVITIES[activity]
        if folder.is_dir():
            for path in sorted(folder.iterdir(), key=lambda item: item.name.casefold()):
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    try:
                        with Image.open(path) as frame:
                            self.animation_frames.append(frame.convert("RGBA"))
                    except OSError:
                        continue
        self._show_animation_frame()

        for name, button in self.button_widgets.items():
            is_selected = name == activity
            button.configure(
                bg=self.colors["green_dark"] if is_selected else self.colors["paper"],
                fg="white" if is_selected else self.colors["ink"],
                highlightbackground=self.colors["green_dark"] if is_selected else self.colors["line"],
            )

    def _show_animation_frame(self):
        if self.animation_frames:
            self._resize_animation_frame()
        else:
            self.animation_label.configure(image="")
            self.animation_label.image = None
            self.scaled_animation_image = None

    def _resize_animation_frame(self):
        if not self.animation_frames:
            return

        source = self.animation_frames[self.frame_index]
        pane_width = max(1, self.animation_pane.winfo_width() - 12)
        pane_height = max(1, self.animation_pane.winfo_height() - 12)
        scale = min(
            pane_width / source.width,
            pane_height / source.height,
        )
        target_size = (
            round(source.width * scale),
            round(source.height * scale),
        )
        render_key = (self.frame_index, target_size)
        if render_key == self.last_animation_render_key:
            return

        resized = source.resize(target_size, Image.Resampling.BILINEAR)
        self.scaled_animation_image = ImageTk.PhotoImage(resized, master=self.root)
        self.animation_label.configure(image=self.scaled_animation_image)
        self.animation_label.image = self.scaled_animation_image
        self.last_animation_render_key = render_key

    def _advance_animation(self):
        if self.animation_frames:
            self.frame_index = (self.frame_index + 1) % len(self.animation_frames)
            self._show_animation_frame()
        self.root.after(random.randint(1500, 2500), self._advance_animation)


def main():
    root = tk.Tk()
    Workagochi(root)
    root.mainloop()

if __name__ == "__main__":
    main()