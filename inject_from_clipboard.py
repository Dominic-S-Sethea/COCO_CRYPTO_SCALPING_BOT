# TARGET_FILE: inject_from_clipboard.py
import pyperclip
import os
import sys

def inject_code_from_clipboard():
    try:
        clipboard_content = pyperclip.paste()
    except Exception as e:
        print(f"Failed to read clipboard: {e}")
        print("Make sure you have a GUI clipboard (e.g., not in pure SSH).")
        return

    if not clipboard_content.strip():
        print("Clipboard is empty.")
        return

    lines = clipboard_content.splitlines()
    if not lines:
        print("No content in clipboard.")
        return

    first_line = lines[0].strip()
    if not first_line.startswith("# TARGET_FILE:"):
        print("First line must start with '# TARGET_FILE: <path>'")
        print(f"Got: {first_line}")
        return

    target_path = first_line[len("# TARGET_FILE:"):].strip()
    if not target_path:
        print("No file path specified after '# TARGET_FILE:'")
        return

    # Normalize path (handle both / and \)
    target_path = os.path.normpath(target_path)

    # Ensure parent directory exists
    os.makedirs(os.path.dirname(target_path), exist_ok=True)

    # Remove the first line (directive)
    code_lines = lines[1:]

    # Write to file
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(code_lines))

    print(f"✅ Injected code into: {os.path.abspath(target_path)}")

if __name__ == "__main__":
    inject_code_from_clipboard()