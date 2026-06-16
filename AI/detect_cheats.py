"""

RANDOM FOREST donosi konacnu odluku (vecinsko glasanje po prozorima)
Session-level pravila su SADA samo SIGURNOSNA PROVJERA:
ako se model i tvrdi dokazi NE slazu, ispisuje se upozorenje za rucnu provjeru.
Time je ML model primarni mehanizam detekcije, a pravila sluze kao kontrola kvalitete.
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


def safety_check(df):
    """SIGURNOSNA PROVJERA - tvrdi dokazi za usporedbu s ML odlukom (ne odlucuje sama)."""
    health_drops = int((df['health_delta'] < 0).sum())
    ammo_drops = int(((df['ammo_bullets_delta'] < 0) | (df['ammo_shells_delta'] < 0) |
                      (df['ammo_cells_delta'] < 0) | (df['ammo_rockets_delta'] < 0)).sum())
    damage_attempts = int(df['damage_attempts'].sum())
    shots_fired = int(df['shots_fired'].sum())
    speed_max = df['speed'].max()

    signals = []
    if speed_max > 30:
        signals.append('speedhack')
    if damage_attempts >= 10 and health_drops == 0:
        signals.append('godmode')
    if shots_fired >= 20 and ammo_drops == 0:
        signals.append('infammo')
    return signals


def detect(csv_file):
    print(f"=== Detekcija varanja u: {csv_file} ===\n")

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

    #Random forest - primarna odluka
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

    #Prosjecna pouzdanost modela za pobjednicku klasu
    classes = list(model.classes_)
    avg_conf = probabilities.max(axis=1).mean()

    #Konacna odluka -vecinsko glasanje Random Foresta
    rf_decision = pred_counts.idxmax()
    rf_decision_pct = 100 * pred_counts.iloc[0] / len(predictions)

    print(f"\n=== ODLUKA MODELA (Random Forest) ===")
    print(f"Prosjecna pouzdanost modela: {avg_conf:.1%}")

    if rf_decision == 'normal':
        print(f"=> CISTA IGRA")
        print(f"   Random Forest je klasificirao {rf_decision_pct:.0f}% prozora kao normalnu igru.")
    else:
        print(f"=> DETEKTIRANO VARANJE: {rf_decision.upper()}")
        print(f"   Random Forest je klasificirao {rf_decision_pct:.0f}% prozora kao '{rf_decision}'.")

    #Sigurnosna provjera po pravilima
    safety_signals = safety_check(df)
    print(f"\n=== Sigurnosna provjera (tvrdi dokazi) ===")
    if safety_signals:
        print(f"   Pravila ukazuju na: {', '.join(safety_signals)}")
    else:
        print(f"   Pravila ne nalaze tvrde dokaze cheata.")

    #Usporedba ML odluke i pravila
    rf_says_cheat = (rf_decision != 'normal')
    rules_say_cheat = (len(safety_signals) > 0)

    if rf_says_cheat and rules_say_cheat:
        if rf_decision in safety_signals:
            print(f"   [OK] Model i pravila se slazu ({rf_decision}).")
        else:
            print(f"   [UPOZORENJE] Model kaze '{rf_decision}', pravila kazu '{safety_signals}'.")
            print(f"   Preporuka: rucna provjera.")
    elif rf_says_cheat and not rules_say_cheat:
        print(f"   [UPOZORENJE] Model detektira '{rf_decision}' ali nema tvrdih dokaza.")
        print(f"   Moguc lazni alarm - preporuka rucne provjere.")
    elif not rf_says_cheat and rules_say_cheat:
        print(f"   [UPOZORENJE] Model kaze cisto, ali pravila nalaze {safety_signals}.")
        print(f"   Moguce da je model promasio - preporuka rucne provjere.")
    else:
        print(f"   [OK] Model i pravila se slazu (cista igra).")

    output_file = csv_file.replace('.csv', '_predictions.csv')
    windows.to_csv(output_file, index=False)
    print(f"\nRezultati po prozorima: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Koristenje: python detect_cheats.py <gameplay_log.csv>")
        sys.exit(1)
    detect(sys.argv[1])
