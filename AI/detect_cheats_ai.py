"""
detect_cheats_ai_only.py
detekcija varanja iskljucivo pomocu Random Forest modela.
Odluku donosi samo strojno ucenje.
Koristenje:
python detect_cheats_ai_only.py <gameplay_log.csv>
"""

import pandas as pd
import joblib
import sys
import os

MODEL_FILE = 'cheat_detector_model.pkl'


def extract_window_features(chunk):
    """Iz prozora podataka izvlaci iste znacajke kao kod treniranja."""
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
        'has_damage_no_health_loss': 1 if (damage_attempts > 0 and health_drops == 0) else 0,
        'has_shots_no_ammo_loss': 1 if (shots_fired > 5 and ammo_drops == 0) else 0,
    }


def windowize(df, window_size):
    n_windows = len(df) // window_size
    rows = []
    for i in range(n_windows):
        chunk = df.iloc[i * window_size:(i + 1) * window_size]
        rows.append(extract_window_features(chunk))
    return pd.DataFrame(rows)


def detect(csv_file):
    print(f"=== Detekcija varanja (Random Forest) u: {csv_file} ===\n")

    saved = joblib.load(MODEL_FILE)
    model = saved['model']
    features = saved['features']
    window_size = saved.get('window_size', 200)

    df = pd.read_csv(csv_file)
    print(f"Ucitano {len(df)} tickova")

    if len(df) < window_size:
        print(f"Premalo podataka (potrebno {window_size}+ tickova)")
        return

    df = df.sort_values('tick').reset_index(drop=True)

    #Random Forest klasificira svaki prozor
    windows = windowize(df, window_size)
    X = windows[features].fillna(0)
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    windows['predicted_label'] = predictions

    print(f"\n=== Random Forest predikcije ({len(windows)} prozora) ===")
    pred_counts = pd.Series(predictions).value_counts()
    for label, count in pred_counts.items():
        pct = 100 * count / len(predictions)
        print(f"  {label:12} {count:3} ({pct:.0f}%)")

    avg_conf = probabilities.max(axis=1).mean()

    #Konacna odluka na temelju vecinskog glasanja Random Foresta
    decision = pred_counts.idxmax()
    decision_pct = 100 * pred_counts.iloc[0] / len(predictions)

    print(f"\n=== Konacna ocjena (Random Forest) ===")
    print(f"Prosjecna pouzdanost modela: {avg_conf:.1%}")
    if decision == 'normal':
        print(f"=> CISTA IGRA ({decision_pct:.0f}% prozora normalno)")
    else:
        print(f"=> DETEKTIRANO VARANJE: {decision.upper()} ({decision_pct:.0f}% prozora)")

    output_file = csv_file.replace('.csv', '_predictions.csv')
    windows.to_csv(output_file, index=False)
    print(f"\nRezultati po prozorima: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Koristenje: python detect_cheats_ai_only.py <gameplay_log.csv>")
        sys.exit(1)
    detect(sys.argv[1])
