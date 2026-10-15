"""
Terminal formatting, colors, and banner utilities for Hamsa OSINT CLI.
"""

import sys
import os

# ANSI escape sequences
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

HAMSA_BANNER = rf"""{CYAN}{BOLD}
  _    _                                
 | |  | |                               
 | |__| | __ _ _ __ ___  ___  __ _      
 |  __  |/ _` | '_ ` _ \/ __|/ _` |     
 | |  | | (_| | | | | | \__ \ (_| |     
 |_|  |_|\__,_|_| |_| |_|___/\__,_|     
{RESET}{DIM}  Open Source Intelligence & Correlation Framework v0.1.0{RESET}
"""

def supports_color() -> bool:
    """Check if the current terminal supports ANSI color output."""
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return True

COLOR_ENABLED = supports_color()

def colorize(text: str, color_code: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{color_code}{text}{RESET}"

def log_info(msg: str) -> None:
    print(f"[{colorize('*', CYAN)}] {msg}")

def log_success(msg: str) -> None:
    print(f"[{colorize('+', GREEN)}] {msg}")

def log_warn(msg: str) -> None:
    print(f"[{colorize('!', YELLOW)}] {msg}")

def log_error(msg: str) -> None:
    print(f"[{colorize('-', RED)}] {msg}")

def log_debug(msg: str) -> None:
    print(f"[{colorize('.', DIM)}] {colorize(msg, DIM)}")
