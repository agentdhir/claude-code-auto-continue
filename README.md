# Claude Code Auto-Continue (VS Code, Windows)

When Claude Code in VS Code stops at its usage limit ("You've hit your session limit · resets 4:10am"), this
script counts down to the reset time, focuses the VS Code window, types `continue` into Claude's prompt box and
presses Enter, so a long task resumes without you at the keyboard. Python with pyautogui; double-click
`run_automation.bat` to start.

---

# 🤖 Claude Code Auto-Continue Automation for VS Code

Jab bhi VS Code me **Claude Code** ki usage limit / rate limit hit hoti hai (jaise: *"You've hit your session limit · resets 4:10am"*), yeh automation script background me countdown chalata hai, aur jaise hi reset time hota hai:
1. **VS Code window ko automatic focus** karta hai.
2. Claude ke prompt box me automatically **`continue`** likhta hai.
3. **Enter press karke** session ko automatically continue kar deta hai!

---

## 🚀 Quick Start (Kaise Chalayein)

### Tarika 1: 1-Click Launch (Sabse Aasan)
Folder me maujood **`run_automation.bat`** par double click karein.
Menu samne aayega:
```text
==================================================================
  🤖 CLAUDE CODE AUTO-CONTINUE AUTOMATION (VS CODE)
==================================================================

📂 Detected 2 VS Code window(s):
   [1] HWND 985886: Startup recruiter lead... - Visual Studio Code

OPTIONS:
  [1] ⚡ Auto-Detect Reset Time (Found: '4:10am' in autoapply...)
  [2] ⏱️  Enter Custom Reset Time (e.g. '04:10 AM' or '45m')
  [3] 🔄 Continuous Night Mode (Auto-loop overnight)
  [4] 🧪 Test Trigger Now (Send 'continue' to VS Code right now)
  [5] ❌ Exit
==================================================================
Select an option [1-5] (default 1):
```
Bas `1` dabayein (ya Enter). Script automatically reset time (`4:10am`) nikal kar countdown shuru kar dega!

---

### Tarika 2: Command Prompt / Terminal Se

```bash
# 1. Interactive Menu
python auto_continue.py

# 2. Specific time set karna (e.g., 4:10 AM)
python auto_continue.py --time "04:10 AM"

# 3. Minutes countdown (e.g., 45 minutes)
python auto_continue.py --minutes 45

# 4. Night Mode / Continuous Loop (Raat bhar chalane ke liye)
python auto_continue.py --time "04:10 AM" --loop

# 5. Immediate test dekhne ke liye
python auto_continue.py --test
```

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| **⚡ 100% Auto-Detection** | `~/.claude/sessions` aur project logs se khud detect kar leta hai ki limit kis time reset hogi (e.g. `4:10am`). |
| **⏳ Live ASCII Countdown** | Terminal me live progress bar aur remaining time dikhta hai (`[02h 38m 10s] [████░░░] 45%`). |
| **🛡️ 10-Second Safety Buffer** | Anthropic ke servers par time sync issue na ho, isliye reset time ke baad 10s ka buffer wait karke prompt bhejta hai. |
| **🎯 Smart Window Matcher** | Jis project folder me Claude chal raha tha, us project ki VS Code window ko hi target karta hai. |
| **📋 Clipboard-Safe Input** | Keystrokes drop hone se bachane ke liye prompt clipboard ke zariye paste (`Ctrl+V`) karke Enter karta hai. |
| **🔔 Audio Chime & Logs** | Jab prompt submit hota hai, audio chime bajti hai aur `history.log` file me entry save hoti hai. |
| **🔄 Overnight Night Mode** | Agar ek limit ke baad agli limit bhi hit ho, to loop me automatically agla reset detect karke chalata rehta hai. |

---

## ⚙️ Parameters (CLI Options)

- `--time`, `-t`: Reset time specify karein (e.g. `"04:10 AM"`, `"16:30"`, `"4:10am"`).
- `--minutes`, `-m`: Kitne minute wait karna hai (e.g. `45`).
- `--prompt`, `-p`: Kya prompt likhna hai (default: `"continue"`).
- `--focus-mode`: 
  - `extension` *(Default)*: VS Code Command Palette ke zariye `Claude Code: Focus input` run karta hai.
  - `terminal`: VS Code Integrated Terminal focus karta hai.
  - `direct`: Jo bhi window active ho usme seedha type karta hai.
- `--loop`: Session ko bar-bar monitor karne ke liye (Night Mode).
- `--buffer`: Safety buffer seconds me (default: `10`).
- `--test`: Check karne ke liye ki window focus aur typing theek se ho rahi hai ya nahi.

---

## 📝 Files Overview
- [auto_continue.py](file:///c:/Users/HP/Desktop/automation%20for%20claude/auto_continue.py) - Main automation script
- [run_automation.bat](file:///c:/Users/HP/Desktop/automation%20for%20claude/run_automation.bat) - 1-Click Double-Click launcher
- [requirements.txt](file:///c:/Users/HP/Desktop/automation%20for%20claude/requirements.txt) - Dependencies (`pyautogui`, `pyperclip`)
- `history.log` - Har automated run ka timestamp aur result log
