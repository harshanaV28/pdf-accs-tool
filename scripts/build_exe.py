"""
PyInstaller Release Build Script
Builds the standalone release executable: dist/PDF-Accessibility-Inspector.exe
"""

import sys
import os
import subprocess
import shutil


def build():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    sys.path.insert(0, root_dir)
    os.chdir(root_dir)

    print("=== Step 1: Generating application icons ===")
    from scripts.generate_app_icon import generate_icons
    generate_icons(os.path.join(root_dir, "assets", "icons"))

    icon_ico = os.path.join(root_dir, "assets", "icons", "app_icon.ico")
    main_script = os.path.join(root_dir, "src", "pdf_inspector", "app.py")

    print("=== Step 2: Running PyInstaller ===")
    # Format data paths for PyInstaller (source;dest on Windows)
    theme_data = f"{os.path.join(root_dir, 'assets', 'styles', 'theme.qss')};assets/styles"
    icon_data = f"{os.path.join(root_dir, 'assets', 'icons', 'app_icon.png')};assets/icons"

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name", "PDF-Accessibility-Inspector",
        "--icon", icon_ico,
        "--add-data", theme_data,
        "--add-data", icon_data,
        "--hidden-import", "pymupdf",
        "--hidden-import", "fitz",
        "--hidden-import", "pikepdf",
        "--hidden-import", "reportlab",
        "--hidden-import", "reportlab.platypus",
        "--hidden-import", "reportlab.lib",
        "--hidden-import", "reportlab.lib.styles",
        "--hidden-import", "reportlab.lib.colors",
        "--hidden-import", "reportlab.lib.pagesizes",
        "--hidden-import", "PIL",
        "--hidden-import", "PySide6.QtCore",
        "--hidden-import", "PySide6.QtGui",
        "--hidden-import", "PySide6.QtWidgets",
        main_script
    ]

    print("Executing command:\n", " ".join(pyinstaller_cmd))
    res = subprocess.run(pyinstaller_cmd)

    if res.returncode != 0:
        print(f"PyInstaller build failed with exit code {res.returncode}")
        sys.exit(res.returncode)

    exe_path = os.path.join(root_dir, "dist", "PDF-Accessibility-Inspector.exe")
    if os.path.exists(exe_path):
        size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 2)
        print("============================================================")
        print(f"BUILD SUCCESSFUL!")
        print(f"Deliverable: {exe_path} ({size_mb} MB)")
        print("============================================================")
    else:
        print("ERROR: Output executable not found in dist/")
        sys.exit(1)


if __name__ == "__main__":
    build()
