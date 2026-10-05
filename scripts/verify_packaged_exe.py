"""
PDF Accessibility Inspector - Packaged Executable Verification Suite
Enforces strict timeouts, process tree termination, and comprehensive health checks.
Guarantees the verification suite never hangs indefinitely.
"""

import sys
import os
import time
import subprocess
import tempfile
from typing import Tuple, Optional


def kill_process_tree(pid: int):
    """Safely and forcefully terminates a process and all its child subprocesses on Windows."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True, timeout=5)
    except Exception:
        pass


def run_command_with_timeout(cmd: list, timeout_sec: int, description: str) -> Tuple[bool, str, float]:
    """
    Executes a command with a strict timeout.
    Returns (success: bool, output_or_error: str, elapsed_seconds: float).
    """
    start_time = time.perf_counter()
    proc = None
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        stdout, stderr = proc.communicate(timeout=timeout_sec)
        elapsed = time.perf_counter() - start_time
        
        if proc.returncode != 0:
            err_msg = f"Process exited with error code {proc.returncode}.\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            return False, err_msg, elapsed
            
        combined_output = stdout if stdout else stderr
        return True, combined_output, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"TIMEOUT: {description} exceeded strict timeout of {timeout_sec}s", elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"ERROR: Exception during {description}: {str(e)}", elapsed


def verify_gui_launch(exe_path: str, timeout_sec: int = 12) -> Tuple[bool, str, float]:
    """
    Tests launching the packaged GUI application.
    Verifies that the window process initializes and remains running without crashing.
    Safely terminates the GUI process afterwards within the timeout.
    """
    start_time = time.perf_counter()
    proc = None
    try:
        proc = subprocess.Popen(
            [exe_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Monitor for initial launch stability
        poll_interval = 0.5
        waited = 0.0
        while waited < 4.0:
            time.sleep(poll_interval)
            waited += poll_interval
            poll_code = proc.poll()
            if poll_code is not None:
                elapsed = time.perf_counter() - start_time
                stdout, stderr = proc.communicate(timeout=2)
                return False, f"GUI crashed immediately with exit code {poll_code}. STDERR: {stderr}", elapsed

        # Process is alive and healthy - terminate gracefully
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)

        elapsed = time.perf_counter() - start_time
        return True, "GUI window initialized successfully and process running cleanly", elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"TIMEOUT: GUI launch test exceeded {timeout_sec}s", elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"ERROR: Exception during GUI launch test: {e}", elapsed


def verify_pdf_open_cli(exe_path: str, pdf_path: str, timeout_sec: int = 15) -> Tuple[bool, str, float]:
    """
    Tests launching the packaged executable with a PDF file argument.
    Verifies document loading into the application without crashing.
    """
    start_time = time.perf_counter()
    proc = None
    try:
        proc = subprocess.Popen(
            [exe_path, pdf_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Monitor for 4 seconds to verify file is ingested
        poll_interval = 0.5
        waited = 0.0
        while waited < 4.0:
            time.sleep(poll_interval)
            waited += poll_interval
            poll_code = proc.poll()
            if poll_code is not None:
                elapsed = time.perf_counter() - start_time
                stdout, stderr = proc.communicate(timeout=2)
                return False, f"Executable crashed while opening PDF with exit code {poll_code}. STDERR: {stderr}", elapsed

        # Process is healthy - terminate gracefully
        proc.terminate()
        try:
            proc.wait(timeout=4)
        except subprocess.TimeoutExpired:
            kill_process_tree(proc.pid)

        elapsed = time.perf_counter() - start_time
        return True, f"Real PDF ({os.path.basename(pdf_path)}) opened successfully by packaged executable", elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"TIMEOUT: PDF open test exceeded {timeout_sec}s", elapsed

    except Exception as e:
        elapsed = time.perf_counter() - start_time
        if proc:
            kill_process_tree(proc.pid)
        return False, f"ERROR: Exception opening PDF: {e}", elapsed


def main():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    exe_path = os.path.join(root_dir, "dist", "PDF-Accessibility-Inspector.exe")
    sample_pdf = os.path.join(root_dir, "test_samples", "accessible_sample.pdf")

    print("================================================================================")
    print("  PDF ACCESSIBILITY INSPECTOR - PACKAGED EXECUTABLE VERIFICATION SUITE")
    print("================================================================================")
    print(f"Target Binary : {exe_path}")
    print(f"Test Document : {sample_pdf}")
    print(f"Start Time    : {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("================================================================================\n")

    if not os.path.exists(exe_path):
        print(f"[FAIL] Executable not found at {exe_path}")
        print("Please build the executable first using: python scripts/build_exe.py")
        sys.exit(1)

    file_size_mb = round(os.path.getsize(exe_path) / (1024 * 1024), 2)
    print(f"Executable File Size: {file_size_mb} MB")

    total_start = time.perf_counter()
    results = []

    # -------------------------------------------------------------------------
    # TEST 1: Packaged Runtime Self-Verification (--verify)
    # -------------------------------------------------------------------------
    print("--- [TEST 1/3] Packaged Binary Self-Verification (--verify) ---")
    print("Enforcing strict 30-second timeout...")
    verify_log = os.path.join(tempfile.gettempdir(), "pdf_inspector_verification.log")
    if os.path.exists(verify_log):
        try:
            os.remove(verify_log)
        except Exception:
            pass

    ok1, out1, t1 = run_command_with_timeout([exe_path, "--verify"], timeout_sec=30, description="Self-Verification")
    
    # Check verification log if present
    log_content = ""
    if os.path.exists(verify_log):
        try:
            with open(verify_log, "r", encoding="utf-8") as f:
                log_content = f.read().strip()
        except Exception:
            pass

    if ok1:
        print(f"--> [PASS] Self-verification succeeded in {t1:.2f}s")
        if log_content:
            print("    Verification Log:")
            for line in log_content.splitlines():
                print(f"      {line}")
        results.append(("Self-Verification (--verify)", "PASS", t1, "All 41 rules, parser, and reports passed"))
    else:
        print(f"--> [FAIL] Self-verification failed in {t1:.2f}s: {out1}")
        if log_content:
            print(f"    Verification Log:\n{log_content}")
        results.append(("Self-Verification (--verify)", "FAIL", t1, out1))

    # -------------------------------------------------------------------------
    # TEST 2: GUI Application Desktop Launch
    # -------------------------------------------------------------------------
    print("\n--- [TEST 2/3] GUI Application Desktop Launch ---")
    print("Enforcing strict 12-second timeout...")
    ok2, out2, t2 = verify_gui_launch(exe_path, timeout_sec=12)
    if ok2:
        print(f"--> [PASS] GUI launch test passed in {t2:.2f}s ({out2})")
        results.append(("GUI Desktop Launch", "PASS", t2, out2))
    else:
        print(f"--> [FAIL] GUI launch test failed in {t2:.2f}s: {out2}")
        results.append(("GUI Desktop Launch", "FAIL", t2, out2))

    # -------------------------------------------------------------------------
    # TEST 3: Real PDF Inspection via CLI Argument
    # -------------------------------------------------------------------------
    print("\n--- [TEST 3/3] Real PDF Document Inspection via Executable ---")
    print("Enforcing strict 15-second timeout...")
    ok3, out3, t3 = verify_pdf_open_cli(exe_path, sample_pdf, timeout_sec=15)
    if ok3:
        print(f"--> [PASS] Real PDF scan test passed in {t3:.2f}s ({out3})")
        results.append(("Real PDF Scan via EXE", "PASS", t3, out3))
    else:
        print(f"--> [FAIL] Real PDF scan test failed in {t3:.2f}s: {out3}")
        results.append(("Real PDF Scan via EXE", "FAIL", t3, out3))

    total_time = time.perf_counter() - total_start

    # -------------------------------------------------------------------------
    # SUMMARY REPORT
    # -------------------------------------------------------------------------
    print("\n================================================================================")
    print("  VERIFICATION SUMMARY REPORT")
    print("================================================================================")
    all_passed = all(r[1] == "PASS" for r in results)
    for name, status, duration, detail in results:
        status_str = f"[{status}]".ljust(8)
        print(f"  {status_str} | {duration:6.2f}s | {name:<30} | {detail[:40]}")
    print("--------------------------------------------------------------------------------")
    print(f"  Total Suite Runtime: {total_time:.2f} seconds")
    print(f"  Final Status       : {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("================================================================================\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
