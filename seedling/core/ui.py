import sys
import os
import tempfile
import time
import random
from pathlib import Path

def ensure_utf8_output():
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def ask_yes_no(prompt_text):
    while True:
        ans = input(prompt_text).strip().lower()
        if ans in ['y', 'yes']:
            return True
        if ans in ['n', 'no']:
            return False
        print("⚠️  Invalid input. Please enter 'y' or 'n'.")

def print_progress_bar(count, label="Processing", icon="⏳"):
    pulse = ["#---", "-#--", "--#-", "---#", "--#-", "-#--"]
    idx = (count // 5) % len(pulse)
    sys.stdout.write(f"\r{icon} {label}... [{pulse[idx]}] Scanned: {count} items ")
    sys.stdout.flush()

def _get_state_file(tool_name): 
    try:
        ppid = os.getppid()
    except AttributeError:
        ppid = "default"
    temp_dir = Path(tempfile.gettempdir())
    return temp_dir / f"seedling_session_{ppid}_{tool_name}.state"

def _get_and_increment_run_count(tool_name): 
    state_file = _get_state_file(tool_name)
    count = 0
    try:
        if state_file.exists():
            count = int(state_file.read_text().strip())
    except Exception: pass
    count += 1
    try:
        state_file.write_text(str(count))
    except Exception: pass
    return count

def print_welcome_message():
    welcome_text = """
    ==================================================================
      🌲 Seedling, A Directory Tree Scanner & Builder 🌲
    ==================================================================
    Welcome! This is a powerful CLI tool designed to explore, search, 
    and construct your directory structures.

    [ Basic Usage ]
      scan .                  -> Scan the current directory
      scan /path/to/dir       -> Scan a specific directory
      
    [ Advanced Features ]
      scan . -f "test"        -> Find files/folders containing "test"
      scan . --full           -> Scan + Bundle ALL code into one file!
      build my_tree.txt       -> Build a folder structure from a file

    [ Need Help? ]
      scan -h                 -> View all advanced options and flags.
    ==================================================================
    """
    print(welcome_text)

def print_build_welcome():
    welcome_text = """
    ==================================================================
      🏗️  Project Structure Builder (build) 🌲
    ==================================================================
    Welcome! Give me a "blueprint" (txt/md), and I'll construct 
    the entire directory hierarchy for you in a split second.

    [ Usage ]
      build <blueprint_file>          -> Build in current folder
      build <file> /path/to/target    -> Build in specific folder

    💡 Pro Tip: You can copy a tree from a README and it just works!
    ==================================================================
    """
    print(welcome_text)

def handle_empty_run():
    count = _get_and_increment_run_count("scan")
    if count == 1:
        print_welcome_message()
        sys.exit(0)
    elif count == 2:
        print("\n💡 [ Notice ] Since you ran 'scan' directly again, please use 'scan -h' for the full manual!\n")
        sys.exit(0)
    elif count == 3:
        print("\n🐿️  [ Easter Egg ] Are you lost in the woods? Let the squirrel search for arguments...\n")
        track_length = 40
        for i in range(track_length):
            track = "." * i + "🐿️ " + "." * (track_length - i - 1)
            sys.stdout.write(f"\r   [{track}]")
            sys.stdout.flush()
            time.sleep(0.06)
        print("\n\n   (The squirrel found nothing. Try adding a path!)\n")
        sys.exit(0)
    elif count == 4:
        print("\n🌱 [ Easter Egg ] Waiting for a tree to scan? Let's grow one instead...\n")
        stages = ["       🌱       ", "       🌿       ", "       🌲       ", "      🌳🌳      ", "     🌳🌲🌳     ", "   🌳🌳🌲🌳🌳   "]
        for stage in stages:
            sys.stdout.write(f"\r   {stage}")
            sys.stdout.flush()
            time.sleep(0.5)
        print("\n\n   (Beautiful! Now give me a real folder to scan!)\n")
        sys.exit(0)
    else:
        text = f"\n🤖 [ Easter Egg ] Okay, you've typed 'scan' {count} times with no arguments.\nInitiating bored-user protocol. Wiping system drive...\n\n"
        for char in text:
            sys.stdout.write(char)
            sys.stdout.flush()
            time.sleep(0.03)
        sys.stdout.write("   rm -rf / : [")
        for i in range(25):
            sys.stdout.write("█")
            sys.stdout.flush()
            time.sleep(random.uniform(0.01, 0.2))
        print("] 100%")
        time.sleep(1)
        print("\n   ...Just kidding! 😂 But seriously, try typing 'scan -h'.\n")
        sys.exit(0)

def handle_empty_build_run():
    count = _get_and_increment_run_count("build")
    if count == 1:
        print_build_welcome()
        sys.exit(0)
    elif count == 2:
        print("\n🏗️  [ Construction Notice ] Need the blueprint specs? Run 'build -h'!\n")
        sys.exit(0)
    elif count == 3:
        print("\n🏗️  [ Easter Egg ] Deploying heavy machinery...\n")
        crane = ["   |          ", "   |---🏗️     ", "   |      |   ", "   |      📦  ", "  _|_         "]
        for i in range(5):
            sys.stdout.write(f"\r   {crane[i]}"); sys.stdout.flush(); time.sleep(0.3)
        print("\n\n   (Crane ready. Now, where is that blueprint?)\n")
        sys.exit(0)
    else:
        print(f"\n👷 [ Easter Egg ] Chief, that's {count} empty calls! Workers are playing cards now. 🃏")
        sys.exit(0)