#!/usr/bin/env python3
"""
Can I Run AI? - checks which local AI models (LLMs) your computer can run.
Works on Linux and Windows. Uses only the Python standard library.

Usage:
    python can_i_run_ai.py          # opens the GUI
    python can_i_run_ai.py --cli    # prints results in the terminal
"""
import os
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# 1. Hardware detection
# --------------------------------------------------------------------------


@dataclass
class GPU:
    name: str
    vram_gb: float  # 0 if unknown


@dataclass
class Hardware:
    os_name: str = ""
    cpu_name: str = ""
    cpu_threads: int = 0
    ram_gb: float = 0.0
    gpus: list = field(default_factory=list)

    @property
    def best_vram_gb(self) -> float:
        return max((g.vram_gb for g in self.gpus), default=0.0)

    @property
    def total_vram_gb(self) -> float:
        return sum(g.vram_gb for g in self.gpus)


def _run(cmd, timeout=10):
    try:
        out = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def detect_ram_gb() -> float:
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        return int(line.split()[1]) / 1024 / 1024
        except Exception:
            pass
    elif sys.platform == "win32":
        import ctypes

        class MEMSTATUS(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        s = MEMSTATUS()
        s.dwLength = ctypes.sizeof(MEMSTATUS)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s)):
            return s.ullTotalPhys / 1024 ** 3
    return 0.0


def detect_cpu_name() -> str:
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/cpuinfo") as f:
                for line in f:
                    if line.lower().startswith("model name"):
                        return line.split(":", 1)[1].strip()
        except Exception:
            pass
    elif sys.platform == "win32":
        out = _run(["powershell", "-NoProfile", "-Command",
                    "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"])
        if out:
            return out
    return platform.processor() or "Unknown CPU"


def _nvidia_gpus():
    smi = shutil.which("nvidia-smi")
    if not smi:
        return []
    out = _run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"])
    gpus = []
    for line in out.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) == 2 and parts[1].replace(".", "").isdigit():
            gpus.append(GPU(parts[0], float(parts[1]) / 1024))
    return gpus


def _amd_gpus_linux():
    gpus = []
    # sysfs exposes VRAM size for amdgpu cards
    base = "/sys/class/drm"
    if not os.path.isdir(base):
        return gpus
    for card in sorted(os.listdir(base)):
        if not re.fullmatch(r"card\d+", card):
            continue
        dev = os.path.join(base, card, "device")
        try:
            with open(os.path.join(dev, "vendor")) as f:
                if f.read().strip() != "0x1002":
                    continue
            with open(os.path.join(dev, "mem_info_vram_total")) as f:
                vram = int(f.read().strip()) / 1024 ** 3
        except Exception:
            continue
        name = "AMD GPU"
        lspci = shutil.which("lspci")
        if lspci:
            for line in _run([lspci]).splitlines():
                if "VGA" in line and ("AMD" in line or "ATI" in line):
                    name = line.split(": ", 1)[-1]
                    break
        gpus.append(GPU(name, vram))
    return gpus


def _windows_gpus():
    # Fallback for non-NVIDIA cards. AdapterRAM is a 32-bit field, so it caps
    # at ~4 GB and can be wrong; the GUI warns when VRAM is "unknown".
    out = _run(["powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name + '|' + $_.AdapterRAM }"])
    gpus = []
    for line in out.splitlines():
        if "|" not in line:
            continue
        name, ram = line.rsplit("|", 1)
        try:
            vram = int(ram) / 1024 ** 3
        except ValueError:
            vram = 0.0
        gpus.append(GPU(name.strip(), vram))
    return gpus


def detect_hardware() -> Hardware:
    hw = Hardware(
        os_name=f"{platform.system()} {platform.release()}",
        cpu_name=detect_cpu_name(),
        cpu_threads=os.cpu_count() or 0,
        ram_gb=detect_ram_gb(),
    )
    gpus = _nvidia_gpus()
    if not gpus:
        gpus = _amd_gpus_linux() if sys.platform.startswith("linux") else _windows_gpus()
    # Ignore basic virtual adapters
    hw.gpus = [g for g in gpus if not re.search(r"basic|virtual|remote", g.name, re.I)]
    return hw


# --------------------------------------------------------------------------
# 2. Model catalogue (edit freely - parameters are in billions)
# --------------------------------------------------------------------------

DEFAULT_MODELS = [
    # (name, params in billions) - used only if models.json can't be found
    ("Qwen2.5 0.5B", 0.5),
    ("Llama 3.2 1B", 1.2),
    ("Qwen2.5 1.5B", 1.5),
    ("Gemma 2 2B", 2.6),
    ("Llama 3.2 3B", 3.2),
    ("Phi-3 Mini 3.8B", 3.8),
    ("Qwen2.5 7B", 7.6),
    ("Mistral 7B", 7.2),
    ("DeepSeek-R1 Distill 7B", 7.6),
    ("Llama 3.1 8B", 8.0),
    ("Gemma 2 9B", 9.2),
    ("Qwen2.5 14B", 14.8),
    ("DeepSeek-R1 Distill 14B", 14.8),
    ("Phi-3 Medium 14B", 14.0),
    ("Gemma 2 27B", 27.2),
    ("Qwen2.5 32B", 32.8),
    ("DeepSeek-R1 Distill 32B", 32.8),
    ("Mixtral 8x7B", 46.7),
    ("Llama 3.3 70B", 70.6),
    ("Qwen2.5 72B", 72.7),
]

# Approximate bytes per parameter for common GGUF quantizations
QUANTS = [
    ("Q4_K_M", 0.60),
    ("Q5_K_M", 0.70),
    ("Q8_0", 1.07),
    ("FP16", 2.00),
]

def load_models():
    """Load models.json. A copy next to the app/script wins over the bundled
    one, so users can edit the list without rebuilding."""
    import json
    folders = []
    if getattr(sys, "frozen", False):
        folders.append(os.path.dirname(sys.executable))
        if hasattr(sys, "_MEIPASS"):
            folders.append(sys._MEIPASS)
    else:
        folders.append(os.path.dirname(os.path.abspath(__file__)))
    for folder in folders:
        path = os.path.join(folder, "models.json")
        if os.path.isfile(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                models = [(m["name"], float(m["params_b"])) for m in data["models"]]
                if models:
                    return models
            except Exception as e:
                print(f"Warning: could not read {path} ({e}); trying next option.", file=sys.stderr)
    return DEFAULT_MODELS


# Set this to the raw URL of models.json in YOUR GitHub repo, e.g.
# "https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/models.json"
# Leave empty to disable online updates (the bundled list is used).
REMOTE_MODELS_URL = "https://raw.githubusercontent.com/TonyXdZ/can-i-ai/main/models.json"
CACHE_MAX_AGE_DAYS = 7


def _parse_models(data):
    models = [(m["name"], float(m["params_b"])) for m in data["models"]]
    if not models:
        raise ValueError("empty model list")
    return models


def _cache_path():
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "can-i-run-ai", "models_cache.json")


def _load_remote_cached():
    """Return the online model list (from a fresh cache, else downloaded),
    or None if unavailable. Never raises."""
    import json
    import time
    import urllib.request
    url = os.environ.get("CIRA_MODELS_URL", REMOTE_MODELS_URL)
    if not url:
        return None
    cache = _cache_path()
    age_days = None
    if os.path.isfile(cache):
        age_days = (time.time() - os.path.getmtime(cache)) / 86400
        if age_days < CACHE_MAX_AGE_DAYS:
            try:
                with open(cache, encoding="utf-8") as f:
                    return _parse_models(json.load(f))
            except Exception:
                pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "can-i-run-ai"})
        with urllib.request.urlopen(req, timeout=3) as r:
            raw = r.read().decode("utf-8")
        models = _parse_models(json.loads(raw))
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as f:
            f.write(raw)
        return models
    except Exception:
        pass
    if age_days is not None:  # offline: a stale cache beats the bundled list
        try:
            with open(cache, encoding="utf-8") as f:
                return _parse_models(json.load(f))
        except Exception:
            pass
    return None


def _load_local_extras():
    """models.local.json next to the app: your own models, added to the list."""
    import json
    if getattr(sys, "frozen", False):
        folder = os.path.dirname(sys.executable)
    else:
        folder = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(folder, "models.local.json")
    try:
        with open(path, encoding="utf-8") as f:
            return _parse_models(json.load(f))
    except Exception:
        return []


def load_models_with_updates():
    models = _load_remote_cached() or load_models()
    extras = _load_local_extras()
    if extras:
        names = {n.lower() for n, _ in extras}
        models = [m for m in models if m[0].lower() not in names] + extras
        models.sort(key=lambda m: m[1])
    return models


MODELS = load_models_with_updates()

OVERHEAD_GB = 1.5  # rough allowance for KV cache + runtime at a modest context
OS_RESERVE_GB = 3.0  # RAM kept free for the OS and other apps

# --------------------------------------------------------------------------
# 3. Fit logic
# --------------------------------------------------------------------------


def required_gb(params_b: float, bytes_per_param: float) -> float:
    return params_b * bytes_per_param + OVERHEAD_GB


def verdict(need_gb: float, hw: Hardware) -> str:
    """Return one of: 'GPU', 'GPU+RAM', 'CPU', 'No'."""
    vram = hw.best_vram_gb
    usable_ram = max(hw.ram_gb - OS_RESERVE_GB, 0)
    if vram and need_gb <= vram * 0.95:
        return "GPU"
    if vram and need_gb <= vram * 0.95 + usable_ram:
        return "GPU+RAM"
    if need_gb <= usable_ram:
        return "CPU"
    return "No"


VERDICT_TEXT = {
    "GPU": "Great - fits fully in GPU memory (fast)",
    "GPU+RAM": "OK - split between GPU and RAM (slower)",
    "CPU": "Slow - runs on CPU / system RAM only",
    "No": "Too big for this computer",
}


def evaluate(hw: Hardware):
    """For each model, find the highest-quality quantization that still runs
    well, falling back to lower quality. Returns list of row dicts."""
    rows = []
    order = {"GPU": 0, "GPU+RAM": 1, "CPU": 2, "No": 3}
    for name, params in MODELS:
        best = None
        # Prefer best quality at the best speed tier
        for q, bpp in reversed(QUANTS):  # Q4 -> FP16 reversed = FP16 first
            need = required_gb(params, bpp)
            v = verdict(need, hw)
            cand = (v, q, need)
            if best is None or order[v] < order[best[0]]:
                best = cand
        # best now has the fastest tier achievable at the highest quality in that tier
        v, q, need = best
        rows.append({"model": name, "params": params, "quant": q if v != "No" else "-",
                     "need_gb": need if v != "No" else required_gb(params, QUANTS[0][1]),
                     "verdict": v})
    return rows


# --------------------------------------------------------------------------
# 4. Front ends
# --------------------------------------------------------------------------


def hardware_summary(hw: Hardware) -> str:
    lines = [f"OS:   {hw.os_name}",
             f"CPU:  {hw.cpu_name} ({hw.cpu_threads} threads)",
             f"RAM:  {hw.ram_gb:.1f} GB"]
    if hw.gpus:
        for g in hw.gpus:
            v = f"{g.vram_gb:.1f} GB VRAM" if g.vram_gb else "VRAM unknown"
            lines.append(f"GPU:  {g.name} ({v})")
    else:
        lines.append("GPU:  none detected (CPU-only mode)")
    return "\n".join(lines)


def run_cli():
    hw = detect_hardware()
    print(hardware_summary(hw))
    print(f"\n{'Model':28} {'Quant':8} {'Needs':>8}  Result")
    print("-" * 78)
    for r in evaluate(hw):
        print(f"{r['model']:28} {r['quant']:8} {r['need_gb']:6.1f}GB  {VERDICT_TEXT[r['verdict']]}")
    print("\nEstimates are approximate. Real needs vary with context length and runtime.")


def run_gui():
    import tkinter as tk
    from tkinter import ttk

    hw = detect_hardware()
    root = tk.Tk()
    root.title("Can I Run AI?")
    root.geometry("860x600")

    ttk.Label(root, text="Your computer", font=("TkDefaultFont", 12, "bold")).pack(anchor="w", padx=12, pady=(12, 0))
    ttk.Label(root, text=hardware_summary(hw), justify="left", font=("TkFixedFont", 10)).pack(anchor="w", padx=12, pady=4)

    cols = ("model", "quant", "need", "result")
    tree = ttk.Treeview(root, columns=cols, show="headings", height=18)
    for c, t, w in (("model", "Model", 230), ("quant", "Best quant", 90),
                    ("need", "Memory needed", 120), ("result", "Result", 380)):
        tree.heading(c, text=t)
        tree.column(c, width=w, anchor="w")
    tree.tag_configure("GPU", background="#d8f5d8")
    tree.tag_configure("GPU+RAM", background="#fff4c4")
    tree.tag_configure("CPU", background="#ffe2c4")
    tree.tag_configure("No", background="#f5d0d0")
    for r in evaluate(hw):
        tree.insert("", "end", values=(r["model"], r["quant"], f"{r['need_gb']:.1f} GB",
                                       VERDICT_TEXT[r["verdict"]]), tags=(r["verdict"],))
    tree.pack(fill="both", expand=True, padx=12, pady=8)

    note = "Estimates are approximate; actual needs vary with context length and runtime."
    if any(g.vram_gb == 0 or (sys.platform == "win32" and g.vram_gb and "nvidia" not in g.name.lower())
           for g in hw.gpus):
        note += "\nNote: VRAM for non-NVIDIA GPUs on Windows can be misreported."
    ttk.Label(root, text=note, foreground="#555").pack(anchor="w", padx=12, pady=(0, 10))
    root.mainloop()


BADGES = {  # verdict -> (label, (light-mode color, dark-mode color))
    "GPU": ("Fast - GPU", ("#2e7d32", "#43a047")),
    "GPU+RAM": ("Partial GPU", ("#b26a00", "#d98a1c")),
    "CPU": ("CPU only", ("#c4571a", "#e0703a")),
    "No": ("Too big", ("#8a8f98", "#5d636d")),
}
FILTERS = {
    "All": None,
    "Fast": {"GPU"},
    "Possible": {"GPU+RAM", "CPU"},
    "Too big": {"No"},
}


def run_gui_modern():
    """Modern GUI using CustomTkinter (pip install customtkinter)."""
    import customtkinter as ctk

    hw = detect_hardware()
    rows = evaluate(hw)
    runnable = sum(1 for r in rows if r["verdict"] != "No")

    ctk.set_appearance_mode("system")  # follows the OS light/dark setting
    ctk.set_default_color_theme("blue")
    app = ctk.CTk()
    app.title("Can I Run AI?")
    app.geometry("940x700")
    app.minsize(780, 540)
    app.grid_columnconfigure(0, weight=1)
    app.grid_rowconfigure(3, weight=1)

    # Header
    header = ctk.CTkFrame(app, fg_color="transparent")
    header.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))
    ctk.CTkLabel(header, text="Can I Run AI?", font=ctk.CTkFont(size=26, weight="bold")).pack(anchor="w")
    ctk.CTkLabel(header, text=f"{runnable} of {len(rows)} models can run on this computer",
                 font=ctk.CTkFont(size=14), text_color=("gray35", "gray70")).pack(anchor="w")

    # Hardware cards
    cards = ctk.CTkFrame(app, fg_color="transparent")
    cards.grid(row=1, column=0, sticky="ew", padx=24, pady=8)
    gpu_text = "\n".join(
        f"{g.name}\n{g.vram_gb:.1f} GB VRAM" if g.vram_gb else f"{g.name}\nVRAM unknown"
        for g in hw.gpus) or "No GPU detected\nCPU-only mode"
    items = [
        ("MEMORY", f"{hw.ram_gb:.1f} GB RAM"),
        ("PROCESSOR", f"{hw.cpu_name}\n{hw.cpu_threads} threads"),
        ("GRAPHICS", gpu_text),
    ]
    for i, (title, body) in enumerate(items):
        cards.grid_columnconfigure(i, weight=1, uniform="cards")
        card = ctk.CTkFrame(cards, corner_radius=12)
        card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=("gray40", "gray60")).pack(anchor="w", padx=14, pady=(12, 0))
        ctk.CTkLabel(card, text=body, justify="left", anchor="w", wraplength=260,
                     font=ctk.CTkFont(size=13)).pack(anchor="w", padx=14, pady=(2, 12))

    # Search + filter
    controls = ctk.CTkFrame(app, fg_color="transparent")
    controls.grid(row=2, column=0, sticky="ew", padx=24, pady=(10, 4))
    controls.grid_columnconfigure(0, weight=1)
    search_var = ctk.StringVar()
    search = ctk.CTkEntry(controls, placeholder_text="Search models...", textvariable=search_var, height=34)
    search.grid(row=0, column=0, sticky="ew", padx=(0, 12))
    seg = ctk.CTkSegmentedButton(controls, values=list(FILTERS), command=lambda _v: render())
    seg.set("All")
    seg.grid(row=0, column=1)

    # Scrollable list
    listbox = ctk.CTkScrollableFrame(app, corner_radius=12)
    listbox.grid(row=3, column=0, sticky="nsew", padx=24, pady=8)
    listbox.grid_columnconfigure(0, weight=1)

    def render(*_):
        for w in listbox.winfo_children():
            w.destroy()
        q = search_var.get().strip().lower()
        allowed = FILTERS[seg.get()]
        shown = [r for r in rows
                 if (allowed is None or r["verdict"] in allowed) and q in r["model"].lower()]
        if not shown:
            ctk.CTkLabel(listbox, text="No models match.", text_color=("gray40", "gray60")).grid(pady=30)
            return
        for i, r in enumerate(shown):
            label, color = BADGES[r["verdict"]]
            row = ctk.CTkFrame(listbox, corner_radius=8, fg_color=("gray90", "gray17"))
            row.grid(row=i, column=0, sticky="ew", pady=3, padx=2)
            row.grid_columnconfigure(0, weight=1)
            ctk.CTkLabel(row, text=r["model"], anchor="w",
                         font=ctk.CTkFont(size=14, weight="bold")).grid(row=0, column=0, sticky="w", padx=14, pady=(8, 0))
            detail = f"{r['params']:g}B parameters"
            if r["quant"] != "-":
                detail += f"  •  {r['quant']}  •  needs ~{r['need_gb']:.1f} GB"
            else:
                detail += f"  •  needs ~{r['need_gb']:.1f} GB even at Q4"
            ctk.CTkLabel(row, text=detail, anchor="w", font=ctk.CTkFont(size=12),
                         text_color=("gray35", "gray65")).grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))
            ctk.CTkLabel(row, text=label, fg_color=color, text_color="white", corner_radius=10,
                         width=104, height=26, font=ctk.CTkFont(size=12, weight="bold")
                         ).grid(row=0, column=1, rowspan=2, padx=14)

    search_var.trace_add("write", render)
    render()

    note = "Estimates are approximate; real needs vary with context length and runtime."
    if any((g.vram_gb == 0) or (sys.platform == "win32" and "nvidia" not in g.name.lower()) for g in hw.gpus):
        note += "  VRAM for non-NVIDIA GPUs on Windows can be misreported."
    ctk.CTkLabel(app, text=note, font=ctk.CTkFont(size=11), text_color=("gray40", "gray60"),
                 wraplength=880, justify="left").grid(row=4, column=0, sticky="w", padx=24, pady=(0, 14))
    app.mainloop()


def main():
    if "--cli" in sys.argv:
        run_cli()
        return
    if "--classic" not in sys.argv:
        try:
            run_gui_modern()
            return
        except ImportError:
            print("customtkinter not installed - using the classic window. "
                  "For the modern look run: pip install customtkinter\n")
        except Exception as e:
            print(f"Modern GUI failed ({e}); trying the classic window.\n")
    try:
        run_gui()
    except Exception as e:  # no display / no tkinter
        print(f"GUI unavailable ({e}); falling back to terminal output.\n")
        run_cli()


if __name__ == "__main__":
    main()
