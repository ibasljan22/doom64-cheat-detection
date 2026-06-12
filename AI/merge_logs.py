"""
merge_logs.py (v2 - podrzava damage_attempts i shots_fired kolone)
Spaja vise gameplay CSV datoteka u jedan file.
Automatski dodaje kolone koje nedostaju (za kompatibilnost sa starijim logovima).
Brise prvi red svake datoteke (zbog inicijalnog spike-a u distance_delta).
"""

import pandas as pd
import sys
import os
import glob

def merge_logs(input_pattern, output_file):
    files = sorted(glob.glob(input_pattern))
    if not files:
        print(f"Nije pronadjena nijedna datoteka za pattern: {input_pattern}")
        return

    print(f"Spajam {len(files)} datoteka:")
    for f in files:
        print(f"  - {f}")

    dfs = []
    for f in files:
        df = pd.read_csv(f)
        # Brisi prvi red (inicijalni spike)
        if len(df) > 1:
            df = df.iloc[1:].reset_index(drop=True)

        # Dodaj kolone ako nedostaju (kompatibilnost sa starim logovima)
        for col in ['infinite_ammo', 'speedhack', 'damage_attempts', 'shots_fired']:
            if col not in df.columns:
                df[col] = 0

        dfs.append(df)

    merged = pd.concat(dfs, ignore_index=True)

    # Reorganiziraj kolone u smislen redoslijed
    expected_order = [
        'tick', 'health', 'armor',
        'ammo_bullets', 'ammo_shells', 'ammo_cells', 'ammo_rockets',
        'pos_x', 'pos_y', 'pos_z',
        'mom_x', 'mom_y', 'mom_z',
        'speed',
        'health_delta',
        'ammo_bullets_delta', 'ammo_shells_delta', 'ammo_cells_delta', 'ammo_rockets_delta',
        'distance_delta',
        'damage_count', 'attack_down',
        'cheats_flag', 'god_mode', 'noclip', 'infinite_ammo', 'speedhack',
        'damage_attempts', 'shots_fired',
        'player_state'
    ]

    cols_to_use = [c for c in expected_order if c in merged.columns]
    merged = merged[cols_to_use]

    merged.to_csv(output_file, index=False)
    print(f"\nSpojeno u: {output_file}")
    print(f"Ukupno redova: {len(merged)}")
    print(f"Kolone: {len(merged.columns)}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Koristenje: python merge_logs.py <pattern> <output_file>")
        print("Primjer: python merge_logs.py \"gameplay_log_*.csv\" normal_gameplay.csv")
        sys.exit(1)

    merge_logs(sys.argv[1], sys.argv[2])
