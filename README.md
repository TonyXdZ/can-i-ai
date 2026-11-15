# Can I Run AI?

A small desktop app for **Windows and Linux** that checks your computer and tells you which local AI models (LLMs) it can run.

It detects your RAM, CPU and GPU (including VRAM), then shows each model with the best quantization that fits, how much memory it needs, and whether it will run fast (on the GPU), partly on the GPU, only on the CPU, or not at all.

## Features

- Detects RAM, CPU, NVIDIA and AMD GPUs (and VRAM) on Windows and Linux
- Modern window (CustomTkinter) that follows your system light/dark mode, with search and filters
- Classic window and terminal modes as fallbacks
- Model list updates itself weekly from the Hugging Face API through a GitHub Action
- Works offline: uses a cached or bundled model list when there is no internet
- Add your own models with a simple JSON file

## Install (no Python needed)

Download the latest app from the [Releases page](../../releases/latest), or use the one-line installer.

**Windows** (PowerShell):

```
irm https://raw.githubusercontent.com/TonyXdZ/can-i-ai/main/install.ps1 | iex
```

**Linux** (terminal):

```
curl -fsSL https://raw.githubusercontent.com/TonyXdZ/can-i-ai/main/install.sh | bash
```

Both install for the current user only (no admin or sudo) and add the app to the Start Menu or app menu. The apps are not code-signed, so Windows SmartScreen may show a warning the first time: click "More info" then "Run anyway". Read the install scripts first if you want to see exactly what they do.

## Quick start (run from source)

Requires Python 3.9 or newer.

```
pip install -r requirements.txt
python can_i_run_ai.py
```

Options:

| Command | What it does |
| --- | --- |
| `python can_i_run_ai.py` | Modern window (falls back to classic, then terminal) |
| `python can_i_run_ai.py --classic` | Classic tkinter window |
| `python can_i_run_ai.py --cli` | Print results in the terminal |

On Linux, if the window does not open, install tkinter: `sudo apt install python3-tk` (Debian/Ubuntu) or `sudo dnf install python3-tkinter` (Fedora).

For NVIDIA GPUs, the driver must be installed so that `nvidia-smi` works.

## How the check works

For each model, the app estimates the memory needed at several quantization levels (Q4_K_M, Q5_K_M, Q8_0, FP16) as roughly `parameters x bytes per parameter + 1.5 GB` for the context and runtime. It then compares that against your GPU memory and the RAM left after reserving 3 GB for the OS.

| Result | Meaning |
| --- | --- |
| Fast - GPU | Fits fully in GPU memory |
| Partial GPU | Split between GPU and RAM (slower) |
| CPU only | Runs from system RAM (slow) |
| Too big | Does not fit, even at Q4 |

These are estimates. Real usage changes with context length and the program you use to run the model. VRAM on non-NVIDIA GPUs under Windows can be misreported, because of a limit in the Windows API.

## The model list

The app picks its list in this order:

1. The online list (`models.json` from this repo), cached for 7 days
2. The `models.json` bundled with the app, if you are offline
3. A small built-in default list

To add your own models, create a file named `models.local.json` next to the app (or next to `can_i_run_ai.py`):

```json
{
  "models": [
    {"name": "My Model 13B", "params_b": 13.0}
  ]
}
```

`params_b` is the size in billions of parameters. Entries in this file are added to the list and replace models with the same name.

### Automatic updates

`update_models.py` queries the Hugging Face Hub API for popular text models from Meta, Qwen, Google, Mistral, Microsoft and DeepSeek, and rewrites `models.json`. If the API fails or returns too few results, the existing file is left untouched.

The workflow `.github/workflows/update-models.yml` runs it every Monday and commits the result if anything changed. You can also run it manually from the Actions tab.

To set it up on your own copy of this repo:

1. Make the repo public.
2. In Settings > Actions > General, set Workflow permissions to **Read and write permissions**.
3. In the Actions tab, run "Update model list" once and check that `models.json` is updated.
4. In `can_i_run_ai.py`, set `REMOTE_MODELS_URL` to
   `https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/models.json`

Optional: add a Hugging Face token as a repository secret named `HF_TOKEN` to avoid rate limits.

## Building the apps

Single-file apps are built with PyInstaller. PyInstaller builds for the system it runs on, so build Windows on Windows and Linux on Linux, or use the GitHub Action.

- **Windows:** double-click or run `build.bat` -> `dist\can-i-run-ai.exe`
- **Linux:** run `./build.sh` -> `dist/can-i-run-ai`
- **GitHub Actions:** the "Build apps" workflow builds both. Run it from the Actions tab, or push a tag such as `v0.1`, then download the results from the run page.

## Project files

| File | Purpose |
| --- | --- |
| `can_i_run_ai.py` | The app: hardware detection, fit logic, windows and CLI |
| `models.json` | The model list (auto-generated weekly) |
| `update_models.py` | Script that regenerates `models.json` |
| `requirements.txt` | Python dependency (CustomTkinter) |
| `build.sh`, `build.bat` | Local build scripts |
| `install.sh`, `install.ps1` | One-line installers for Linux and Windows (download from the latest release) |
| `.github/workflows/` | Weekly model update, and app build + release workflows |

## License

MIT License. See [LICENSE](LICENSE) for details.