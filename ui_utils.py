import math
import time

def generate_progress_bar(current, total, width=20):
    if total == 0:
        return "░" * width + " 0.0%"
    percent = (current / total) * 100
    percent = min(100, max(0, percent))
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return f"{bar} {percent:.1f}%"

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{int(minutes)}m {int(seconds)}s"

def calculate_eta(start_time, current, total):
    if current == 0:
        return "Calculating..."
    elapsed = time.time() - start_time
    speed = current / elapsed
    remaining = total - current
    eta_seconds = remaining / speed
    return format_time(eta_seconds)
