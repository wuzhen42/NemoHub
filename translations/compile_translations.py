#!/usr/bin/env python3
"""
Script to compile .ts files to .qm files for NemoHub.
.qm files are binary compiled translation files used at runtime.
"""

import subprocess
import os
import sys
import glob

# Get the translations directory
translations_dir = os.path.dirname(os.path.abspath(__file__))

def compile_translations():
    """Compile all .ts files to .qm files"""
    print("Compiling translation files...")

    # Find all .ts files
    ts_files = glob.glob(os.path.join(translations_dir, "*.ts"))

    if not ts_files:
        print("✗ No .ts files found in translations directory")
        print(f"Directory: {translations_dir}")
        sys.exit(1)

    success_count = 0
    fail_count = 0

    for ts_file in ts_files:
        qm_file = ts_file.replace(".ts", ".qm")
        base_name = os.path.basename(ts_file)

        print(f"\nCompiling {base_name}...")

        try:
            cmd = ["pyside6-lrelease", ts_file, "-qm", qm_file]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print(f"✓ Successfully compiled to {os.path.basename(qm_file)}")
                if result.stdout:
                    print(result.stdout.strip())
                success_count += 1
            else:
                print(f"✗ Failed to compile {base_name}")
                print(result.stderr)
                fail_count += 1
        except FileNotFoundError:
            print("\n✗ ERROR: pyside6-lrelease not found!")
            print("Please install it with: pip install PySide6")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}")
            fail_count += 1

    print("\n" + "="*60)
    print(f"Compilation complete: {success_count} succeeded, {fail_count} failed")
    if success_count > 0:
        print(f"\n.qm files location: {translations_dir}")
        print("\nThe application will automatically load these at runtime.")
    print("="*60)

if __name__ == "__main__":
    compile_translations()
