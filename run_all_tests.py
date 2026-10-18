#!/usr/bin/env python3
"""
Xealeus State-Machine Engine — Master Test Runner (`run_all_tests.py`)
================================================-------------------
Executes all five core verification scripts sequentially against the
Takahashi IVTFF transcription dataset (`LSI_ivtff_0d.txt`):

  1. test_deep_structure.py  — Intra-word NMI slot coupling & line-envelope profiles
  2. test_currier_ab.py      — Cross-dialect middle core stem transfer (Currier A vs. B)
  3. test_voynich_compiler.py — Memoryless 3-stage Markov state-machine compiler (V1)
  4. test_compiler_v2.py     — Inter-word domino chaining & core-persistence compiler (V2)
  5. test_diagram_geometry.py — 2D diagram geometry & spatial layout mode-switch analysis

Usage:
    python3 run_all_tests.py [path_to_LSI_ivtff_0d.txt]
"""

import sys
import os
import subprocess
import json
import time

TEST_SCRIPTS = [
    ("1. Deep Structure & NMI Slot Coupling Analysis", "test_deep_structure.py"),
    ("2. Currier A/B Cross-Dialect Core Transfer", "test_currier_ab.py"),
    ("3. Markov State-Machine Compiler V1 (80/20 Train/Test)", "test_voynich_compiler.py"),
    ("4. Inter-Word Domino Chaining Compiler V2", "test_compiler_v2.py"),
    ("5. 2D Diagram Geometry & Layout Coupling", "test_diagram_geometry.py"),
]

def print_header(title: str):
    width = 72
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)

def main():
    corpus_file = sys.argv[1] if len(sys.argv) > 1 else "LSI_ivtff_0d.txt"

    print("\n" + "░" * 72)
    print("  XEALEUS STATE-MACHINE ENGINE — FULL VERIFICATION SUITE")
    print("░" * 72)
    print(f"Target Corpus File : {corpus_file}")
    print(f"Total Test Modules : {len(TEST_SCRIPTS)}")
    print("░" * 72)

    if not os.path.exists(corpus_file):
        print(f"\n[!] ERROR: Input corpus file '{corpus_file}' not found in current directory.")
        print("    Please obtain 'LSI_ivtff_0d.txt' from the Stolfi/Zandbergen Voynich archives")
        print("    and place it in the root directory before running this runner.\n")
        sys.exit(1)

    suite_start = time.time()
    results_summary = {}

    for title, script_name in TEST_SCRIPTS:
        print_header(title)
        if not os.path.exists(script_name):
            print(f"[!] Warning: Script file '{script_name}' missing from workspace. Skipping...")
            results_summary[script_name] = "SKIPPED (File Not Found)"
            continue

        print(f"Running `python3 {script_name} {corpus_file}`...\n")
        t0 = time.time()
        try:
            res = subprocess.run(
                [sys.executable, script_name, corpus_file],
                capture_output=True,
                text=True,
                check=True
            )
            elapsed = round(time.time() - t0, 2)
            print(f"[✓] {script_name} completed successfully in {elapsed}s.")
            
            # Attempt to pretty-print returned JSON output
            try:
                parsed_json = json.loads(res.stdout)
                formatted_out = json.dumps(parsed_json, indent=2)
                # Display condensed preview if output is very large
                lines = formatted_out.splitlines()
                if len(lines) > 60:
                    print("\n--- Output Preview (First 30 & Last 15 lines) ---")
                    print("\n".join(lines[:30]))
                    print(f"  ... [{len(lines) - 45} lines omitted for readability] ...")
                    print("\n".join(lines[-15:]))
                else:
                    print("\n--- Output ---")
                    print(formatted_out)
            except json.JSONDecodeError:
                print("\n--- Raw Output ---")
                print(res.stdout[:1000])

            results_summary[script_name] = f"PASSED ({elapsed}s)"

        except subprocess.CalledProcessError as e:
            elapsed = round(time.time() - t0, 2)
            print(f"[×] {script_name} FAILED (Exit Code {e.returncode}) after {elapsed}s!")
            print("--- Error Traceback ---")
            print(e.stderr if e.stderr else e.stdout)
            results_summary[script_name] = f"FAILED (Exit Code {e.returncode})"

    total_time = round(time.time() - suite_start, 2)
    print("\n" + "░" * 72)
    print("  SUITE EXECUTION SUMMARY")
    print("░" * 72)
    for script_name, status in results_summary.items():
        print(f"  • {script_name:<28} : {status}")
    print(f"\nTotal Suite Time: {total_time} seconds")
    print("░" * 72 + "\n")

if __name__ == "__main__":
    main()
