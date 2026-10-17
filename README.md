# Workagochi

A small Tkinter coworking companion with activity animations and a persistent checklist.

## Run

Requires Python 3.9 or later, Tkinter, and Pillow. Install Pillow with:

```powershell
python -m pip install -r requirements.txt
```

Then run:

```powershell
python workagochi.py
```

Animation frames are loaded from the matching folders under `animations/`, bilinearly scaled while preserving their aspect ratio, and never reduced below their original dimensions.
