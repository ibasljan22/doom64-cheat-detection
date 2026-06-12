"""
realtime_monitor.py (v4 - koristi damage_attempts i shots_fired)
Realtime anti-cheat monitor za Doom 64.
Koristi tvrde signale (damage_attempts, shots_fired) za pouzdanu detekciju
bez laznih alarma na edge-case scenarijima.

Koristenje:
    1. Pokreni PRIJE igre:  python realtime_monitor.py
    2. Pokreni Doom 64
    3. Igraj - monitor analizira u realnom vremenu
    4. Detekcija cheata -> popup -> igra se zatvara
"""

import time
import pandas as pd
import os
import glob
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox

# ============== KONFIGURACIJA ==============
DEBUG_DIR = r"C:\Users\Ivan\Doom64EX-Plus\Windows\x64\Debug"
GAME_PROCESS = "DOOM64.exe"
CHECK_INTERVAL = 3
SLIDING_WINDOW = 1000  # ~140 sekundi
MIN_TOTAL_ROWS = 100

# Pragovi (tvrdi signali)
THRESHOLD_SPEED_MAX = 30
THRESHOLD_HIGH_SPEED_COUNT = 50
THRESHOLD_GODMODE_DMG_ATTEMPTS = 10   # napada na igraca bez gubitka healtha
THRESHOLD_INFAMMO_SHOTS = 20          # hitaca bez gubitka ammo
# ============================================


def find_latest_csv():
    pattern = os.path.join(DEBUG_DIR, "gameplay_log_*.csv")
    files = glob.glob(pattern)
    return max(files, key=os.path.getmtime) if files else None


def kill_game():
    try:
        subprocess.run(["taskkill", "/F", "/IM", GAME_PROCESS],
                       capture_output=True, timeout=5)
    except Exception as e:
        print(f"Greska pri zatvaranju igre: {e}")


def show_alert(cheat_type, details):
    names = {'godmode': 'GOD MODE', 'infammo': 'INFINITE AMMO', 'speedhack': 'SPEED HACK'}
    name = names.get(cheat_type, cheat_type.upper())
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    messagebox.showwarning(
        "Anti-Cheat: Detektirano varanje!",
        f"Sustav je detektirao varanje:\n\n   >>> {name} <<<\n\n{details}\n\nIgra ce se sada zatvoriti.",
        parent=root
    )
    print(f"\n>>> Zatvaram {GAME_PROCESS}...")
    kill_game()
    root.destroy()


def check_for_cheats(df):
    if len(df) < MIN_TOTAL_ROWS:
        return None, None

    recent = df.tail(SLIDING_WINDOW)

    health_drops = int((recent['health_delta'] < 0).sum())
    ammo_drops = int(((recent['ammo_bullets_delta'] < 0) | (recent['ammo_shells_delta'] < 0) |
                      (recent['ammo_cells_delta'] < 0) | (recent['ammo_rockets_delta'] < 0)).sum())
    damage_attempts = int(recent['damage_attempts'].sum()) if 'damage_attempts' in recent.columns else 0
    shots_fired = int(recent['shots_fired'].sum()) if 'shots_fired' in recent.columns else 0
    speed_max = recent['speed'].max()
    high_speed_count = int((recent['speed'] > 25).sum())

    # 1. SPEEDHACK
    if speed_max > THRESHOLD_SPEED_MAX:
        return 'speedhack', f"Maksimalna brzina: {speed_max:.1f}\n(normalna do 27)"
    if high_speed_count > THRESHOLD_HIGH_SPEED_COUNT:
        return 'speedhack', f"Visoka brzina u {high_speed_count} uzoraka"

    # 2. GODMODE - napadan ali bez gubitka healtha
    if damage_attempts >= THRESHOLD_GODMODE_DMG_ATTEMPTS and health_drops == 0:
        return 'godmode', (f"{damage_attempts} napada na igraca u zadnjih ~140 sek,\n"
                           f"ali 0 izgubljenog healtha.")

    # 3. INFAMMO - pucao ali bez gubitka ammo
    if shots_fired >= THRESHOLD_INFAMMO_SHOTS and ammo_drops == 0:
        return 'infammo', (f"{shots_fired} ispaljenih hitaca u zadnjih ~140 sek,\n"
                           f"ali 0 potrosenog ammo.")

    return None, None


def monitor():
    print("=" * 55)
    print("       ANTI-CHEAT MONITOR ZA DOOM 64 (v4)")
    print("=" * 55)
    print(f"Pratim: {DEBUG_DIR}")
    print(f"Sliding window: {SLIDING_WINDOW} redova (~140 sek)")
    print(f"Cekam log datoteku...\n")

    current_csv = None
    last_size = 0

    while True:
        csv = find_latest_csv()
        if csv != current_csv:
            current_csv = csv
            if csv:
                print(f"[{time.strftime('%H:%M:%S')}] Pratim: {os.path.basename(csv)}")
            last_size = 0

        if not current_csv:
            time.sleep(CHECK_INTERVAL)
            continue

        try:
            current_size = os.path.getsize(current_csv)
        except (FileNotFoundError, PermissionError):
            time.sleep(CHECK_INTERVAL)
            continue

        if current_size == last_size:
            time.sleep(CHECK_INTERVAL)
            continue
        last_size = current_size

        try:
            df = pd.read_csv(current_csv, on_bad_lines='skip')
        except Exception:
            time.sleep(CHECK_INTERVAL)
            continue

        if len(df) < 10:
            time.sleep(CHECK_INTERVAL)
            continue

        recent = df.tail(SLIDING_WINDOW)
        da = int(recent['damage_attempts'].sum()) if 'damage_attempts' in recent.columns else 0
        sf = int(recent['shots_fired'].sum()) if 'shots_fired' in recent.columns else 0
        hd = int((recent['health_delta'] < 0).sum())
        ad = int(((recent['ammo_bullets_delta'] < 0) | (recent['ammo_shells_delta'] < 0) |
                  (recent['ammo_cells_delta'] < 0) | (recent['ammo_rockets_delta'] < 0)).sum())
        ms = recent['speed'].max()

        print(f"[{time.strftime('%H:%M:%S')}] Ukupno:{len(df):4} | "
              f"dmg_att={da:2} hp_drop={hd:2} | shots={sf:3} ammo_drop={ad:2} | max_sp={ms:.1f} ", end="")

        cheat_type, details = check_for_cheats(df)
        if cheat_type:
            print(f"\n>>> DETEKTIRANO: {cheat_type.upper()}")
            print(f"    {details}")
            show_alert(cheat_type, details)
            print("\nMonitor zavrsen.")
            return
        else:
            print("OK")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        monitor()
    except KeyboardInterrupt:
        print("\n\nMonitor zaustavljen.")
        sys.exit(0)
