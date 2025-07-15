import tkinter as tk
from tkinter import filedialog, messagebox
import pywinstyles 
import json, os
from parser import parse_map_file, deobfuscate_stacktrace
import re
import glob

CONFIG_PATH = "config.json"

def load_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return json.load(f)
    return {"map_path": "", "mapping_dir": ""}

def save_config(conf):
    with open(CONFIG_PATH, "w") as f:
        json.dump(conf, f)

config = load_config()
mapping = {}

def select_map_file():
    path = filedialog.askopenfilename(filetypes=[("ProGuard map", "*.map")])
    if path:
        try:
            global mapping
            mapping = parse_map_file(path)
            config["map_path"] = path
            save_config(config)
            map_label.config(text=f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

def select_mapping_folder():
    folder = filedialog.askdirectory()
    if folder:
        config["mapping_dir"] = folder
        save_config(config)
        mapping_dir_label.config(text=f"Mapping dir: {folder}")

def deobfuscate():
    global last_input, last_output, last_highlights, current_view
    if not mapping:
        messagebox.showwarning("No .map", "Select a .map file first.")
        return
    last_input = textbox.get("1.0", tk.END)
    result, highlights = deobfuscate_stacktrace_highlight(last_input, mapping)
    last_output = result
    last_highlights = highlights
    if current_view == "input":
        show_output()
    else:
        show_input()
    adjust_window_width()

def deobfuscate_stacktrace_highlight(text, mapping):
    """
    Like deobfuscate_stacktrace, but returns positions for highlighting.
    """
    IGNORED_PREFIXES = (
        "java.", "javax.", "sun.", "com.sun.", "jdk.", "org.bukkit.", "net.minecraft.",
        "String", "Integer", "Boolean", "Double", "Float", "Long", "Short", "Byte", "Void"
    )
    pattern = re.compile(r'([a-zA-Z_][\w\.]*\w)')
    highlights = []
    lines = []
    current_index = 0
    for line in text.splitlines(keepends=True):
        def replace_match(match):
            word = match.group(1)
            if any(word.startswith(prefix) for prefix in IGNORED_PREFIXES):
                return word
            parts = word.split('.')
            for i in range(len(parts), 0, -1):
                candidate = '.'.join(parts[:i])
                if candidate in mapping:
                    replaced = mapping[candidate] + word[len(candidate):]
                    # Calcola posizione per evidenziare
                    start = f"{len(lines)+1}.{match.start()}"
                    end = f"{len(lines)+1}.{match.start()+len(replaced)}"
                    highlights.append((start, end))
                    return replaced
            return word
        new_line = pattern.sub(replace_match, line)
        lines.append(new_line)
    return ''.join(lines), highlights

def find_jar_name_from_stacktrace(text):
    """
    Find the first .jar name in the stacktrace (after 'at' or in brackets).
    """
    # Look for lines with 'at ...jar/'
    for line in text.splitlines():
        match = re.search(r'at ([\w\-\.]+\.jar)/', line)
        if match:
            return match.group(1)
    return None

def find_map_file_by_jar(jar_name, search_dir):
  """
  Look for a .map file matching the jar name in the given directory (recursively).
  """
  if not jar_name or not search_dir:
    return None
  map_name = os.path.splitext(jar_name)[0] + ".map"
  # First, try direct match in root
  candidate = os.path.join(search_dir, map_name)
  if os.path.isfile(candidate):
    return candidate
  # Recursively search for exact match
  for root_dir, _, files in os.walk(search_dir):
    if map_name in files:
      return os.path.join(root_dir, map_name)
  # fallback: search for any .map file containing the jar base name (recursively)
  base = os.path.splitext(jar_name)[0]
  print(f"Searching recursively for .map files matching: {base} in {search_dir}")
  for root_dir, _, files in os.walk(search_dir):
    for f in files:
      if f.endswith(".map") and base in f:
        return os.path.join(root_dir, f)
  return None

def on_paste(event=None):
    # Wait for paste to complete, then try to auto-load map and deobfuscate
    def after_paste():
        try_autoload_map_from_stacktrace()
        deobfuscate()
        show_output()  # Automatically switch to deobfuscated view after paste
    root.after(50, after_paste)
    return None  # allow default paste event

def try_autoload_map_from_stacktrace():
    """
    When pasting a stacktrace, try to find and load the matching .map file from the selected mapping folder.
    """
    input_text = textbox.get("1.0", tk.END)
    jar_name = find_jar_name_from_stacktrace(input_text)
    search_dir = config.get("mapping_dir")
    if jar_name and search_dir:
        found_map = find_map_file_by_jar(jar_name, search_dir)
        if found_map:
            try:
                global mapping
                mapping = parse_map_file(found_map)
                config["map_path"] = found_map
                save_config(config)
                map_label.config(text=f"Loaded: {os.path.basename(found_map)} (auto)")
                print(f"Auto-loaded map: {found_map} for jar: {jar_name}")
            except Exception as e:
                messagebox.showerror("Error loading map", str(e))

# --- DARK THEME (Dracula-like) ---
DRACULA_BG = "#282a36"
DRACULA_FG = "#f8f8f2"
DRACULA_ENTRY_BG = "#44475a"
DRACULA_ENTRY_FG = "#f8f8f2"
DRACULA_YELLOW = "#fffb96"
DRACULA_BTN_BG = "#6272a4"
DRACULA_BTN_FG = "#f8f8f2"
DRACULA_LABEL = "#bd93f9"

root = tk.Tk()
root.title("Stacktrace Deobfuscator")

pywinstyles.apply_style(root, "acrylic") 

# Set Windows title bar to dark mode (Windows 10+ only)
try:
    import ctypes
    HWND = ctypes.windll.user32.GetParent(root.winfo_id())
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    for attr in (20, 19):
        ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND, attr, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int(1)))
    # Windows 11 acrylic (mica) transparency effect
    DWMWA_SYSTEMBACKDROP_TYPE = 38
    # 2 = Mica, 3 = Acrylic (try both, Mica is more native for Windows 11)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(HWND, DWMWA_SYSTEMBACKDROP_TYPE, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int(1)))
except Exception:
    pass

# Always open fullscreen
root.state('zoomed')  # This makes the window fullscreen on Windows

root.configure(bg=DRACULA_BG)

style_args = {"bg": DRACULA_BG, "fg": DRACULA_LABEL, "font": ("Consolas", 11, "bold")}

map_label = tk.Label(root, text="No .map file loaded", **style_args)
map_label.pack(pady=(10, 0))

btn_select = tk.Button(root, text="Select .map File", command=select_map_file,
                       bg=DRACULA_BTN_BG, fg=DRACULA_BTN_FG, activebackground=DRACULA_LABEL, activeforeground=DRACULA_BG)
btn_select.pack(pady=(5, 10))

# Add button and label to select mapping folder
mapping_dir_label = tk.Label(root, text=f"Mapping dir: {config.get('mapping_dir','') or 'None'}", bg=DRACULA_BG, fg=DRACULA_LABEL, font=("Consolas", 10, "bold"))
mapping_dir_label.pack(pady=(0, 0))
btn_mapping_dir = tk.Button(root, text="Select Mapping Folder", command=select_mapping_folder,
                            bg=DRACULA_BTN_BG, fg=DRACULA_BTN_FG, activebackground=DRACULA_LABEL, activeforeground=DRACULA_BG)
btn_mapping_dir.pack(pady=(0, 10))

tk.Label(root, text="Stacktrace / Deobfuscated", bg=DRACULA_BG, fg=DRACULA_FG, font=("Consolas", 10, "bold")).pack()

textbox = tk.Text(
    root,
    height=30,
    bg=DRACULA_ENTRY_BG,
    fg=DRACULA_ENTRY_FG,
    insertbackground=DRACULA_FG,
    selectbackground="#fffb96",
    selectforeground="#222222",
    font=("Consolas", 11)
)
textbox.pack(fill="both", expand=True, padx=10, pady=(0, 10))
textbox.tag_configure("highlight", background=DRACULA_YELLOW, foreground="#222222", font=("Consolas", 11, "bold"))

# State to keep track of which view is shown
current_view = "input"  # or "output"
last_input = ""
last_output = ""
last_highlights = []

def show_input():
    global current_view
    current_view = "input"
    text = last_input
    textbox.config(state="normal")
    textbox.delete("1.0", tk.END)
    textbox.insert("1.0", text)
    textbox.tag_remove("highlight", "1.0", tk.END)
    switch_btn.config(text="Show Deobfuscated")
    # Restore scroll position
    if hasattr(show_input, "scroll"):
        textbox.yview_moveto(show_input.scroll)
    textbox.config(state="normal")

def show_output():
    global current_view
    current_view = "output"
    text = last_output
    textbox.config(state="normal")
    textbox.delete("1.0", tk.END)
    textbox.insert("1.0", text)
    # Highlight replaced parts
    for start, end in last_highlights:
        textbox.tag_add("highlight", start, end)
    switch_btn.config(text="Show Original")
    # Restore scroll position
    if hasattr(show_output, "scroll"):
        textbox.yview_moveto(show_output.scroll)
    textbox.config(state="normal")

def switch_view():
    # Save current scroll position
    scroll = textbox.yview()[0]
    if current_view == "input":
        show_output.scroll = scroll
        show_output()
    else:
        show_input.scroll = scroll
        show_input()

switch_btn = tk.Button(root, text="Show Deobfuscated", command=switch_view,
                       bg=DRACULA_BTN_BG, fg=DRACULA_BTN_FG, activebackground=DRACULA_LABEL, activeforeground=DRACULA_BG)
switch_btn.pack(pady=(0, 10))

def adjust_window_width():
    """
    Adjust the window width based on the longest line in the current textbox.
    """
    lines = textbox.get("1.0", tk.END).splitlines()
    if not lines:
        return
    max_len = max((len(line) for line in lines), default=80)
    width_px = int(max(800, min(1800, max_len * 8.5 + 60)))
    root.geometry(f"{width_px}x600")

def on_text_change(event=None):
    adjust_window_width()

textbox.bind("<KeyRelease>", on_text_change)
textbox.bind("<<Paste>>", on_paste)
textbox.bind("<Control-v>", on_paste)

# Initialize with input view
show_input()

# Auto-load last .map file if present
if os.path.exists(config.get("map_path", "")):
    try:
        mapping = parse_map_file(config["map_path"])
        map_label.config(text=f"Loaded: {os.path.basename(config['map_path'])}")
    except Exception:
        pass

root.mainloop()
