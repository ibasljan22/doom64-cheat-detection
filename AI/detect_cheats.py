"""
detect_cheats.py (v7 - hibridni pristup s damage_attempts/shots_fired)
Kombinira:
1. Session-level pravila (tvrdi dokazi) - koriste damage_attempts i shots_fired
2. ML model (Random Forest) na prozorima - za granularnu analizu

Tvrdi signali rjesavaju edge-case scenarije:
- Vjesti igrac koji ne prima damage: damage_attempts=0 -> NIJE godmode
- Chainsaw igra: shots_fired=0 -> NIJE infammo
"""

import pandas as pd
import joblib
import sys
import os

MODEL_FILE = 'cheat_detector_model.pkl'


def extract_window_features(chunk):
    total_ammo = (chunk['ammo_bullets'] + chunk['ammo_shells'] +
                  chunk['ammo_cells'] + chunk['ammo_rockets'])
    n_attacks = int(chunk['attack_down'].sum())
    health_drops = int((chunk['health_delta'] < 0).sum())
    ammo_drops = int(((chunk['ammo_bullets_delta'] < 0) |
                      (chunk['ammo_shells_delta'] < 0) |
                      (chunk['ammo_cells_delta'] < 0) |
                      (chunk['ammo_rockets_delta'] < 0)).sum())
    damage_attempts = int(chunk['damage_attempts'].sum())
    shots_fired = int(chunk['shots_fired'].sum())

    return {
        'speed_max': chunk['speed'].max(),
        'speed_mean': chunk['speed'].mean(),
        'speed_std': chunk['speed'].std() if len(chunk) > 1 else 0,
        'high_speed_ratio': (chunk['speed'] > 25).sum() / len(chunk),
        'damage_attempts': damage_attempts,
        'health_drops': health_drops,
        'damage_absorbed_ratio': (
            (damage_attempts - health_drops) / max(damage_attempts, 1)
        ) if damage_attempts > 0 else 0,
        'shots_fired': shots_fired,
        'ammo_drops': ammo_drops,
        'shots_without_ammo_loss_ratio': (
            (shots_fired - ammo_drops) / max(shots_fired, 1)
        ) if shots_fired > 0 else 0,
        'attacks': n_attacks,
        'distance_total': chunk['distance_delta'].sum(),
        'health_std': chunk['health'].std() if len(chunk) > 1 else 0,
        'ammo_total_std': total_ammo.std() if len(chunk) > 1 else 0,
    }


def windowize(df, window_size):
    n_windows = len(df) // window_size
    rows = []
    for i in range(n_windows):
        chunk = df.iloc[i * window_size:(i + 1) * window_size]
        rows.append(extract_window_features(chunk))
    return pd.DataFrame(rows)


def session_level_check(df):
    """Tvrdi dokazi cheatova na razini cijele sesije."""
    n_attacks = int((df['attack_down'] == 1).sum())
    health_drops = int((df['health_delta'] < 0).sum())
    ammo_drops = int(((df['ammo_bullets_delta'] < 0) | (df['ammo_shells_delta'] < 0) |
                      (df['ammo_cells_delta'] < 0) | (df['ammo_rockets_delta'] < 0)).sum())
    damage_attempts = int(df['damage_attempts'].sum())
    shots_fired = int(df['shots_fired'].sum())
    speed_max = df['speed'].max()
    high_speed_count = int((df['speed'] > 25).sum())

    return {
        'damage_attempts': damage_attempts,
        'health_drops': health_drops,
        'shots_fired': shots_fired,
        'ammo_drops': ammo_drops,
        'speed_max': speed_max,
        'high_speed_count': high_speed_count,
        'attacks': n_attacks,

        # === TVRDI SIGNALI ===
        # God mode: neprijatelj te napadao (damage_attempts) ali health nije pao
        # Ako damage_attempts=0 (nitko te nije napao), NEMA dokaza za godmode
        'godmode_proven': damage_attempts >= 10 and health_drops == 0,

        # Infinite ammo: ispalio hice oruzjem koje trosi ammo, ali ammo nije pao
        # Ako shots_fired=0 (samo chainsaw), NEMA dokaza za infammo
        'infammo_proven': shots_fired >= 20 and ammo_drops == 0,

        # Speedhack: brzina iznad fizickog maksimuma normalne igre
        'speedhack_proven': speed_max > 30 or high_speed_count > 50,
    }


def detect(csv_file):
    print(f"=== Detekcija varanja u: {csv_file} ===\n")

    saved = joblib.load(MODEL_FILE)
    model = saved['model']
    features = saved['features']
    window_size = saved.get('window_size', 100)

    df = pd.read_csv(csv_file)
    print(f"Ucitano {len(df)} tickova")

    if len(df) < window_size:
        print(f"Premalo podataka (potrebno {window_size}+)")
        return

    df = df.sort_values('tick').reset_index(drop=True)

    # === Session-level (tvrdi dokazi) ===
    s = session_level_check(df)
    print(f"\n=== Analiza cijele sesije ===")
    print(f"  Damage attempts (napadi na igraca): {s['damage_attempts']}")
    print(f"  Health drops (stvarno izgubljen health): {s['health_drops']}")
    print(f"  Shots fired (hici oruzjem s ammo): {s['shots_fired']}")
    print(f"  Ammo drops (stvarno potrosen ammo): {s['ammo_drops']}")
    print(f"  Max brzina: {s['speed_max']:.1f}")

    # === ML predikcije (granularno) ===
    windows = windowize(df, window_size)
    X = windows[features].fillna(0)
    predictions = model.predict(X)
    windows['predicted_label'] = predictions

    print(f"\n=== ML predikcije ({len(windows)} prozora) ===")
    pred_counts = pd.Series(predictions).value_counts()
    for label, count in pred_counts.items():
        print(f"  {label:12} {count:3} ({100*count/len(predictions):.0f}%)")

    # === KONACNA ODLUKA (tvrdi dokazi imaju prioritet) ===
    print(f"\n=== Konacna ocjena ===")
    detected = []
    if s['speedhack_proven']:
        detected.append(('speedhack', f"max brzina {s['speed_max']:.1f} (prag 30)"))
    if s['godmode_proven']:
        detected.append(('godmode', f"{s['damage_attempts']} napada na igraca, 0 izgubljenog healtha"))
    if s['infammo_proven']:
        detected.append(('infammo', f"{s['shots_fired']} ispaljenih hitaca, 0 potrosenog ammo"))

    if detected:
        for cheat, reason in detected:
            print(f"=> DETEKTIRANO VARANJE: {cheat.upper()}")
            print(f"   Dokaz: {reason}")
    else:
        # Nema tvrdih dokaza - oslon na ML
        normal_pct = 100 * pred_counts.get('normal', 0) / len(predictions)
        if normal_pct >= 60:
            print(f"=> CISTA IGRA ({normal_pct:.0f}% prozora normalno, nema tvrdih dokaza cheata)")
        else:
            most = pred_counts.idxmax()
            print(f"=> SUMNJIVO (ML ukazuje na '{most}', ali nema tvrdih dokaza)")
            print(f"   Preporuka: rucna provjera")

    output_file = csv_file.replace('.csv', '_predictions.csv')
    windows.to_csv(output_file, index=False)
    print(f"\nRezultati po prozorima: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Koristenje: python detect_cheats.py <gameplay_log.csv>")
        sys.exit(1)
    detect(sys.argv[1])
