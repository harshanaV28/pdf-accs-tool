"""
PDF Accessibility Inspector - Standalone Application Entry Point
Used for development execution and PyInstaller release packaging.
"""
import sys
import os

# Ensure workspace root and src directory are on sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(root_dir, "src")

for p in (root_dir, src_dir):
    if p not in sys.path:
        sys.path.insert(0, p)

from pdf_inspector.app import main

if __name__ == "__main__":
    main()
