"""
detect_cheats_ai_segments.py
Segmentna varijanta skripte detect_cheats_ai.py.
razlika u nacinu sazimanja predikcija po prozorima u konacnu odluku:
detect_cheats_ai.py : vecinsko glasanje
konacna odluka = najcesca oznaka kroz cijeli run.
Prikladno kad je tijekom cijele sesije isto ponasanje.
detect_cheats_ai_segments.pyy  : segmentna prijava
prijavljuje svaki oblik varanja koji se pojavi u barem
MIN_CHEAT_WINDOWS prozora, bez obzira na vecinu, te ispisuje
u kojim se vremenskim segmentima varanje javlja.
Prikladno kad je varanje moglo biti ukljuceno samo u dijelu igre.
Obje skripte koriste isti model (cheat_detector_model.pkl) i iste znacajke.
Koristenje:
    python detect_segments.py <gameplay_log.csv>
"""
import pandas as pd
import joblib
import sys

MODEL_FILE = 'cheat_detector_model.pkl'
MIN_CHEAT_WINDOWS = 3  #koliko prozora nekog cheata je dovoljno za prijavu


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
    print(f"=== Segmentna detekcija varanja (Random Forest): {csv_file} ===\n")

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
    predictions = list(model.predict(X))
    windows['predicted_label'] = predictions
    n = len(predictions)

    from collections import Counter
    counts = Counter(predictions)
    print(f"\n=== Random Forest predikcije ({n} prozora) ===")
    for label, count in counts.most_common():
        print(f"  {label:12} {count:3} ({100*count/n:.0f}%)")

    #Segmentna prijava: svaki cheat koji se javlja u >= MIN_CHEAT_WINDOWS prozora
    cheat_counts = {k: v for k, v in counts.items() if k != 'normal'}
    detected = {k: v for k, v in cheat_counts.items() if v >= MIN_CHEAT_WINDOWS}

    print(f"\n=== Konacna ocjena (Random Forest, segmentno) ===")
    if detected:
        print("=> DETEKTIRANO VARANJE:")
        for cheat, cnt in sorted(detected.items(), key=lambda x: -x[1]):
            print(f"   - {cheat.upper()}: u {cnt} od {n} prozora ({100*cnt/n:.0f}% igre)")
        print("\n   Vremenski segmenti varanja:")
        in_seg = False
        start = 0
        for i, p in enumerate(predictions):
            if p in detected and not in_seg:
                in_seg = True
                start = i
            elif p not in detected and in_seg:
                in_seg = False
                print(f"     prozori {start+1}-{i} ({predictions[start]})")
        if in_seg:
            print(f"     prozori {start+1}-{n} ({predictions[start]})")
    else:
        print("=> CISTA IGRA (nijedan oblik varanja nije zabiljezen u dovoljno prozora)")

    output_file = csv_file.replace('.csv', '_segments.csv')
    windows.to_csv(output_file, index=False)
    print(f"\nRezultati po prozorima: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Koristenje: python detect_segments.py <gameplay_log.csv>")
        sys.exit(1)
    detect(sys.argv[1])
