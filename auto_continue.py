#!/usr/bin/env python3
"""
Claude Code Auto-Continue Automation for VS Code
================================================
Monitors Claude Code usage limits in VS Code and automatically sends
'continue' (or custom prompt) as soon as the limit resets.

Supports:
- Auto-detection from Claude session logs (~/.claude/projects)
- Manual timer input (e.g. '04:10 AM', '45m', '1h 30m')
- Multi-window VS Code detection & matching
- Visual in-place countdown timer with progress bar
- Audio chimes & desktop logging
- Continuous loop / Night mode (sleep mode)
"""

import os
import sys
import time
import glob
import json
import re
import argparse
import datetime
import ctypes
import winsound

# Required third-party packages (auto-installed or fallback)
try:
    import pyautogui
    import pyperclip
except ImportError:
    print("Required packages missing. Installing pyautogui and pyperclip...")
    os.system(f'"{sys.executable}" -m pip install pyautogui pyperclip')
    import pyautogui
    import pyperclip

# Windows Win32 API functions
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def log_message(msg):
    """Print to console and append to history.log"""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    line = f"[{timestamp}] {msg}"
    print(line)
    try:
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.log")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def play_chime(success=True):
    """Plays an audible chime through the PC speaker / system audio."""
    try:
        if success:
            winsound.Beep(784, 150)  # G5
            winsound.Beep(1046, 250) # C6
        else:
            winsound.Beep(400, 300)
    except Exception:
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass


def get_all_vscode_windows():
    """
    Finds all running VS Code windows across active desktops using EnumDesktopWindows.
    Returns list of tuples: (hwnd, title)
    """
    hwnds = []
    h_desk = user32.OpenInputDesktop(0, False, 0x01FF)
    
    def enum_cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            buff = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, buff, 512)
            title = buff.value
            if "Visual Studio Code" in title:
                hwnds.append((hwnd, title))
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumDesktopWindows(h_desk, WNDENUMPROC(enum_cb), 0)
    return hwnds


def activate_window(hwnd):
    """
    Robustly restores and brings a window to the foreground, bypassing
    Windows background-focus restrictions via Alt-key simulation and AttachThreadInput.
    """
    user32.ShowWindow(hwnd, 9)  # 9 = SW_RESTORE
    
    cur_tid = kernel32.GetCurrentThreadId()
    target_tid = user32.GetWindowThreadProcessId(hwnd, None)
    fg_hwnd = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
    
    if cur_tid != target_tid:
        user32.AttachThreadInput(cur_tid, target_tid, True)
    if fg_tid and cur_tid != fg_tid:
        user32.AttachThreadInput(cur_tid, fg_tid, True)
        
    # Simulate Alt key tap to unlock foreground window change
    user32.keybd_event(0x12, 0, 0, 0)
    user32.keybd_event(0x12, 0, 2, 0)
    
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    
    if cur_tid != target_tid:
        user32.AttachThreadInput(cur_tid, target_tid, False)
    if fg_tid and cur_tid != fg_tid:
        user32.AttachThreadInput(cur_tid, fg_tid, False)
        
    time.sleep(0.5)


def send_prompt_to_vscode(hwnd, prompt="continue", focus_mode="extension"):
    """
    Brings VS Code to foreground, focuses Claude input, and sends the prompt.
    focus_mode:
      - 'extension': Opens VS Code command palette (Ctrl+Shift+P) and runs 'Claude Code: Focus input'
      - 'terminal': Focuses terminal via command palette ('View: Focus Terminal')
      - 'direct': Directly types into whatever is currently active in the VS Code window
    """
    log_message(f"Activating VS Code window (HWND: {hwnd})...")
    activate_window(hwnd)
    
    if focus_mode == "extension":
        log_message("Focusing Claude Code input box via Command Palette...")
        # Open Command Palette
        pyautogui.hotkey("ctrl", "shift", "p")
        time.sleep(0.35)
        # Type command to focus Claude Code input
        pyautogui.write("Claude Code: Focus input", interval=0.01)
        time.sleep(0.25)
        pyautogui.press("enter")
        time.sleep(0.5)
    elif focus_mode == "terminal":
        log_message("Focusing VS Code terminal...")
        pyautogui.hotkey("ctrl", "shift", "p")
        time.sleep(0.35)
        pyautogui.write("View: Focus Terminal", interval=0.01)
        time.sleep(0.25)
        pyautogui.press("enter")
        time.sleep(0.5)
    else:
        log_message("Using direct focus mode...")
        time.sleep(0.3)
        
    # Send the prompt using clipboard paste to avoid dropping characters
    log_message(f"Typing prompt: '{prompt}'...")
    old_clipboard = ""
    try:
        old_clipboard = pyperclip.paste()
    except Exception:
        pass
        
    pyperclip.copy(prompt)
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(0.5)
    
    # Restore original clipboard
    try:
        if old_clipboard:
            pyperclip.copy(old_clipboard)
    except Exception:
        pass

    log_message(f"SUCCESS: Prompt '{prompt}' successfully sent to Claude!")
    play_chime(success=True)


def parse_target_time(input_str, base_dt=None):
    """
    Parses a string into a future datetime object.
    Supports:
    - Relative duration: '45m', '1h 30m', '2 hours', '90min', '120s'
    - Clock time: '4:10am', '4:10 PM', '16:10', '04:10'
    """
    if base_dt is None:
        base_dt = datetime.datetime.now()
        
    s = input_str.strip().lower()
    
    # 1. Relative duration
    total_seconds = 0
    duration_matched = False
    
    h_m = re.search(r'(\d+)\s*(?:h|hr|hour|hours)', s)
    if h_m:
        total_seconds += int(h_m.group(1)) * 3600
        duration_matched = True
        
    m_m = re.search(r'(\d+)\s*(?:m|min|minute|minutes)', s)
    if m_m:
        total_seconds += int(m_m.group(1)) * 60
        duration_matched = True
        
    s_m = re.search(r'(\d+)\s*(?:s|sec|second|seconds)', s)
    if s_m:
        total_seconds += int(s_m.group(1))
        duration_matched = True
        
    if not duration_matched and re.match(r'^\d+$', s):
        total_seconds = int(s) * 60
        duration_matched = True
        
    if duration_matched:
        return base_dt + datetime.timedelta(seconds=total_seconds)
        
    # 2. Clock time
    m_clock = re.search(r'(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(am|pm)?', s)
    if m_clock:
        hr = int(m_clock.group(1))
        minute = int(m_clock.group(2))
        sec = int(m_clock.group(3)) if m_clock.group(3) else 0
        ampm = m_clock.group(4)
        
        if ampm == 'pm' and hr < 12:
            hr += 12
        elif ampm == 'am' and hr == 12:
            hr = 0
            
        target = base_dt.replace(hour=hr, minute=minute, second=sec, microsecond=0)
        # If target has already passed today by more than 2 minutes, assume tomorrow
        if target <= base_dt - datetime.timedelta(minutes=2):
            target += datetime.timedelta(days=1)
        return target
        
    raise ValueError(f"Could not understand time format: '{input_str}'. Use formats like '4:10am' or '45m'.")


def detect_claude_limit():
    """
    Inspects ~/.claude/sessions and ~/.claude/projects to detect if any
    active session has hit a usage limit and extracts the reset time.
    """
    sessions_dir = os.path.expanduser("~/.claude/sessions")
    projects_dir = os.path.expanduser("~/.claude/projects")
    
    sess_files = glob.glob(os.path.join(sessions_dir, "*.json"))
    active_sessions = []
    for sf in sess_files:
        try:
            with open(sf, "r", encoding="utf-8") as f:
                d = json.load(f)
                active_sessions.append(d)
        except Exception:
            pass
            
    # Sort active sessions by updatedAt descending
    active_sessions.sort(key=lambda x: x.get("updatedAt", 0), reverse=True)
    
    for sess in active_sessions:
        sid = sess.get("sessionId")
        pid = sess.get("pid")
        cwd = sess.get("cwd", "")
        matching = glob.glob(os.path.join(projects_dir, f"**/*{sid}*.jsonl"), recursive=True)
        if not matching:
            continue
        jsonl_path = matching[0]
        
        try:
            with open(jsonl_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            continue
            
        # Scan backward from end of file
        for line in reversed(lines):
            try:
                data = json.loads(line)
            except Exception:
                continue
                
            # If the last interaction was a user prompt, then the user has already continued
            if data.get("type") == "user" and data.get("message", {}).get("role") == "user":
                prompt_content = data.get("message", {}).get("content", "")
                # Ignore tool results as user messages
                is_real_prompt = True
                if isinstance(prompt_content, list):
                    for part in prompt_content:
                        if isinstance(part, dict) and part.get("type") == "tool_result":
                            is_real_prompt = False
                            break
                if is_real_prompt:
                    # User already continued or prompted after the limit
                    break
                    
            content = data.get("message", {}).get("content", [])
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text = item.get("text", "")
                        # e.g., "resets 4:10am", "resets at 3:00 PM", "resets in 45m"
                        m = re.search(r"resets?\s+(?:at\s+)?(\d{1,2}:\d{2}\s*(?:am|pm)?|\d+\s*(?:m|min|minute|h|hour|s|second)s?)", text, re.IGNORECASE)
                        if m:
                            return {
                                "sessionId": sid,
                                "pid": pid,
                                "cwd": cwd,
                                "jsonl": jsonl_path,
                                "raw_text": text.strip(),
                                "extracted_time_str": m.group(1),
                                "timestamp": data.get("timestamp")
                            }
    return None


def match_vscode_window(cwd, windows):
    """
    Matches the best VS Code window based on the project cwd path.
    """
    if not windows:
        return None
    if not cwd:
        return windows[0]
        
    folder_name = os.path.basename(os.path.normpath(cwd)).lower()
    for hwnd, title in windows:
        if folder_name in title.lower():
            return (hwnd, title)
            
    return windows[0]


def run_countdown(target_dt, safety_buffer_seconds=10):
    """
    Displays a smooth in-place countdown timer with ASCII progress bar.
    """
    # Add safety buffer so we don't trigger 1 second before Anthropic's clock ticks over
    effective_target = target_dt + datetime.timedelta(seconds=safety_buffer_seconds)
    now = datetime.datetime.now()
    total_wait = (effective_target - now).total_seconds()
    
    if total_wait <= 0:
        log_message("Target reset time has already passed! Ready to send prompt immediately.")
        return
        
    print()
    print("=" * 64)
    print(f" ⏳ COUNTDOWN STARTED")
    print(f" • Target Reset Time : {target_dt.strftime('%I:%M:%S %p')} (+{safety_buffer_seconds}s buffer)")
    print(f" • Expected Trigger  : {effective_target.strftime('%I:%M:%S %p')}")
    print(f" • Press Ctrl+C anytime to cancel or trigger manually")
    print("=" * 64)
    print()
    
    while True:
        now = datetime.datetime.now()
        rem_sec = (effective_target - now).total_seconds()
        if rem_sec <= 0:
            break
            
        hours, rem = divmod(int(rem_sec), 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{hours:02d}h {minutes:02d}m {seconds:02d}s"
        
        # Calculate progress
        elapsed = total_wait - rem_sec
        pct = max(0.0, min(1.0, elapsed / total_wait)) if total_wait > 0 else 1.0
        bar_len = 22
        filled = int(round(bar_len * pct))
        bar = "█" * filled + "░" * (bar_len - filled)
        
        sys.stdout.write(f"\r ⏳ Time Remaining: [{time_str}] [{bar}] {int(pct*100):3d}% | Current: {now.strftime('%I:%M:%S %p')} ")
        sys.stdout.flush()
        time.sleep(1)
        
    print("\n\n" + "=" * 64)
    log_message("⏰ TIME'S UP! Usage limit has reset. Sending prompt now...")
    print("=" * 64 + "\n")


def interactive_menu():
    """Interactive CLI menu when run without command line flags."""
    print()
    print("=" * 66)
    print("  🤖 CLAUDE CODE AUTO-CONTINUE AUTOMATION (VS CODE)")
    print("=" * 66)
    
    # 1. Detect open VS Code windows
    windows = get_all_vscode_windows()
    if not windows:
        print("\n❌ Warning: No open VS Code windows detected!")
        print("   Please make sure VS Code is open with your Claude Code session.\n")
    else:
        print(f"\n📂 Detected {len(windows)} VS Code window(s):")
        for i, (h, t) in enumerate(windows, 1):
            print(f"   [{i}] HWND {h}: {t[:70]}")
            
    # 2. Check for auto-detected limit in session logs
    limit_info = detect_claude_limit()
    auto_choice_text = "[1] ⚡ Auto-Detect Reset Time"
    if limit_info:
        auto_choice_text += f" (Found: '{limit_info['extracted_time_str']}' in {os.path.basename(limit_info['cwd'])})"
    else:
        auto_choice_text += " (Scan active session logs)"
        
    print("\nOPTIONS:")
    print(f"  {auto_choice_text}")
    print("  [2] ⏱️  Enter Custom Reset Time (e.g. '04:10 AM' or '45m')")
    print("  [3] 🔄 Continuous Night Mode (Auto-loop overnight)")
    print("  [4] 🧪 Test Trigger Now (Send 'continue' to VS Code right now)")
    print("  [5] ❌ Exit")
    print("=" * 66)
    
    choice = input("\nSelect an option [1-5] (default 1): ").strip()
    if not choice:
        choice = "1"
        
    prompt = "continue"
    focus_mode = "extension"
    
    if choice == "4":
        # Test trigger
        target_win = select_window(windows)
        if not target_win:
            return
        log_message("Testing trigger in 3 seconds... Switch your view if needed.")
        time.sleep(3)
        send_prompt_to_vscode(target_win[0], prompt=prompt, focus_mode=focus_mode)
        return
        
    if choice == "5":
        print("Exiting.")
        return
        
    loop_mode = (choice == "3")
    
    # Target time determination
    target_dt = None
    target_win = None
    
    if choice in ("1", "3"):
        if limit_info:
            log_message(f"Auto-detected limit: '{limit_info['raw_text']}'")
            try:
                target_dt = parse_target_time(limit_info['extracted_time_str'])
                target_win = match_vscode_window(limit_info['cwd'], windows)
            except Exception as e:
                log_message(f"Could not parse extracted time '{limit_info['extracted_time_str']}': {e}")
                
        if not target_dt:
            # Re-scan or ask
            print("\nCould not find a current rate limit in active logs.")
            custom = input("Please enter the reset time manually (e.g. '04:10 AM' or '45m'): ").strip()
            if not custom:
                print("No time provided. Exiting.")
                return
            target_dt = parse_target_time(custom)
    elif choice == "2":
        custom = input("Enter reset time (e.g. '04:10 AM' or '45m' or '1h 20m'): ").strip()
        if not custom:
            print("No time provided. Exiting.")
            return
        target_dt = parse_target_time(custom)
        
    if not target_win:
        target_win = select_window(windows)
        if not target_win:
            return

    # Focus mode preference
    print("\nFocus Mode:")
    print("  [1] Claude Code Extension Chat Panel (Recommended)")
    print("  [2] Integrated Terminal")
    print("  [3] Direct (Use currently active cursor)")
    f_choice = input("Select focus mode [1-3] (default 1): ").strip()
    if f_choice == "2":
        focus_mode = "terminal"
    elif f_choice == "3":
        focus_mode = "direct"
        
    # Execute single or loop
    while True:
        log_message(f"Target VS Code Window: [{target_win[0]}] {target_win[1][:60]}")
        run_countdown(target_dt, safety_buffer_seconds=10)
        send_prompt_to_vscode(target_win[0], prompt=prompt, focus_mode=focus_mode)
        
        if not loop_mode:
            break
            
        log_message("Night Mode: Waiting 60 seconds before checking for the next usage limit...")
        time.sleep(60)
        
        # In loop mode, wait until next limit occurs
        log_message("Watching for next Claude usage limit...")
        while True:
            new_limit = detect_claude_limit()
            if new_limit and new_limit['extracted_time_str'] != limit_info.get('extracted_time_str'):
                log_message(f"New limit detected: {new_limit['raw_text']}")
                target_dt = parse_target_time(new_limit['extracted_time_str'])
                limit_info = new_limit
                break
            time.sleep(15)


def select_window(windows):
    """Helper to let user select a window if multiple exist."""
    if not windows:
        print("❌ Error: No VS Code window found.")
        return None
    if len(windows) == 1:
        return windows[0]
        
    print("\nSelect target VS Code window:")
    for i, (h, t) in enumerate(windows, 1):
        print(f"  [{i}] {t[:75]}")
    sel = input(f"Enter number [1-{len(windows)}] (default 1): ").strip()
    try:
        idx = int(sel) - 1 if sel else 0
        return windows[idx]
    except Exception:
        return windows[0]


def main():
    parser = argparse.ArgumentParser(description="Claude Code Auto-Continue for VS Code")
    parser.add_argument("--time", "-t", type=str, help="Reset time, e.g. '04:10 AM' or '16:10'")
    parser.add_argument("--minutes", "-m", type=int, help="Minutes to wait, e.g. 45")
    parser.add_argument("--prompt", "-p", type=str, default="continue", help="Prompt to send (default: 'continue')")
    parser.add_argument("--focus-mode", choices=["extension", "terminal", "direct"], default="extension", help="Focus method")
    parser.add_argument("--loop", action="store_true", help="Continuous night mode")
    parser.add_argument("--buffer", type=int, default=10, help="Safety buffer in seconds (default: 10)")
    parser.add_argument("--test", action="store_true", help="Test trigger immediately")

    args = parser.parse_args()

    # If flags were provided, run in automated CLI mode
    if args.test or args.time or args.minutes:
        windows = get_all_vscode_windows()
        if not windows:
            log_message("Error: No VS Code windows found.")
            sys.exit(1)
            
        target_win = windows[0]
        if args.test:
            log_message("Testing trigger in 3 seconds...")
            time.sleep(3)
            send_prompt_to_vscode(target_win[0], prompt=args.prompt, focus_mode=args.focus_mode)
            return

        if args.time:
            target_dt = parse_target_time(args.time)
        elif args.minutes:
            target_dt = datetime.datetime.now() + datetime.timedelta(minutes=args.minutes)

        while True:
            run_countdown(target_dt, safety_buffer_seconds=args.buffer)
            send_prompt_to_vscode(target_win[0], prompt=args.prompt, focus_mode=args.focus_mode)
            if not args.loop:
                break
            time.sleep(60)
            # Wait for next
            while True:
                limit_info = detect_claude_limit()
                if limit_info:
                    target_dt = parse_target_time(limit_info['extracted_time_str'])
                    break
                time.sleep(15)
        return

    # Otherwise show interactive menu
    interactive_menu()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nAutomation cancelled by user. Goodbye!")
    except Exception as e:
        log_message(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
