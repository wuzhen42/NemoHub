#!/usr/bin/env python3
"""
Script to update translation files for NemoHub.
This script uses pylupdate6 to extract translatable strings from Python files.
"""

import subprocess
import os
import sys

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
translations_dir = os.path.join(project_root, "translations")

# List of source files to scan for translatable strings
source_files = [
    "NemoHub.py",
    "app/easy.py",
    "app/drop.py",
    "app/assets.py",
    "app/login.py",
    "app/proxy.py",
    "app/settings.py",
    "app/license.py",
]

# Language codes we support
languages = [
    "zh_CN",  # Simplified Chinese
]

def update_translations():
    """Extract strings and update .ts files"""
    print("Updating translation files...")

    for lang in languages:
        ts_file = os.path.join(translations_dir, f"nemohub_{lang}.ts")

        # Build the command
        cmd = ["pyside6-lupdate", "-verbose"]

        # Add all source files
        for src in source_files:
            src_path = os.path.join(project_root, src)
            if os.path.exists(src_path):
                cmd.append(src_path)
            else:
                print(f"Warning: Source file not found: {src_path}")

        # Output file
        cmd.extend(["-ts", ts_file])

        print(f"\nGenerating {lang} translation file...")
        print(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✓ Successfully updated {ts_file}")
                if result.stdout:
                    print(result.stdout)
            else:
                print(f"✗ Failed to update {ts_file}")
                print(result.stderr)
        except FileNotFoundError:
            print("\n✗ ERROR: pyside6-lupdate not found!")
            print("Please install it with: pip install PySide6")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}")
            sys.exit(1)

    print("\n" + "="*60)
    print("Translation files updated successfully!")
    print(f"Files location: {translations_dir}")
    print("\nNext steps:")
    print("1. Open .ts files with Qt Linguist to translate")
    print("2. Run compile_translations.py to generate .qm files")
    print("="*60)

if __name__ == "__main__":
    update_translations()
