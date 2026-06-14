"""
train_model.py (v8 - Random Forest kao primarni klasifikator)
Window-based Random Forest s prosirenim feature setom ukljucujuci
binarne indikatore cheat-signatura. Veci prozor (200 tickova ~30s) daje
modelu vecu sansu da uhvati kljucne dogadjaje (napad na igraca, pucanje).
"""

import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    classification_report, confusion_matrix,
    ConfusionMatrixDisplay, accuracy_score
)

INPUT_FILE = 'training_dataset.csv'
MODEL_FILE = 'cheat_detector_model.pkl'
WINDOW_SIZE = 200  # tickova po prozoru (~30 sekundi)


def extract_window_features(chunk):
    """Iz prozora podataka izvlaci znacajke za detekciju cheatova."""
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
        # === Brzina (speedhack) ===
        'speed_max': chunk['speed'].max(),
        'speed_mean': chunk['speed'].mean(),
        'speed_std': chunk['speed'].std() if len(chunk) > 1 else 0,
        'high_speed_ratio': (chunk['speed'] > 25).sum() / len(chunk),

        # === God mode signatura ===
        'damage_attempts': damage_attempts,
        'health_drops': health_drops,
        'damage_absorbed_ratio': (
            (damage_attempts - health_drops) / max(damage_attempts, 1)
        ) if damage_attempts > 0 else 0,

        # === Infinite ammo signatura ===
        'shots_fired': shots_fired,
        'ammo_drops': ammo_drops,
        'shots_without_ammo_loss_ratio': (
            (shots_fired - ammo_drops) / max(shots_fired, 1)
        ) if shots_fired > 0 else 0,

        # === Opcenite aktivnosti ===
        'attacks': n_attacks,
        'distance_total': chunk['distance_delta'].sum(),
        'health_std': chunk['health'].std() if len(chunk) > 1 else 0,
        'ammo_total_std': total_ammo.std() if len(chunk) > 1 else 0,

        # === Binarni indikatori (jaki signali za model) ===
        # Bilo napada na igraca, ali health nije pao -> god mode signatura
        'has_damage_no_health_loss': 1 if (damage_attempts > 0 and health_drops == 0) else 0,
        # Pucao oruzjem s ammo, ali ammo nije pao -> infinite ammo signatura
        'has_shots_no_ammo_loss': 1 if (shots_fired > 5 and ammo_drops == 0) else 0,
    }


def windowize(df, window_size):
    n_windows = len(df) // window_size
    rows = []
    for i in range(n_windows):
        chunk = df.iloc[i * window_size:(i + 1) * window_size]
        feats = extract_window_features(chunk)
        if 'label' in chunk.columns:
            feats['label'] = chunk['label'].mode().iloc[0]
        rows.append(feats)
    return pd.DataFrame(rows)


def train():
    print("=== Ucitavanje podataka ===")
    df = pd.read_csv(INPUT_FILE)
    print(f"Ukupno tickova: {len(df)}")

    df = df.sort_values(['label', 'tick']).reset_index(drop=True)

    print(f"\nDijelim na prozore od {WINDOW_SIZE} tickova (~30 sek)...")
    windows_dfs = []
    for label in df['label'].unique():
        sub = df[df['label'] == label].copy()
        win_df = windowize(sub, WINDOW_SIZE)
        windows_dfs.append(win_df)
        print(f"  {label}: {len(sub)} tickova -> {len(win_df)} prozora")

    dataset = pd.concat(windows_dfs, ignore_index=True)
    dataset = dataset.sample(frac=1, random_state=42).reset_index(drop=True)

    print(f"\nUkupno prozora: {len(dataset)}")
    print(f"Distribucija:\n{dataset['label'].value_counts()}")

    feature_cols = [c for c in dataset.columns if c != 'label']
    X = dataset[feature_cols].fillna(0)
    y = dataset['label']

    print(f"\nZnacajke ({len(feature_cols)}): {feature_cols}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"\nTrening: {len(X_train)}, Test: {len(X_test)}")

    print("\n=== Treniranje Random Forest ===")
    model = RandomForestClassifier(
        n_estimators=200, max_depth=15, min_samples_split=5,
        random_state=42, n_jobs=-1
    )
    model.fit(X_train, y_train)

    cv_scores = cross_val_score(model, X_train, y_train, cv=5, n_jobs=-1)
    print(f"CV tocnost: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"\nTest tocnost: {accuracy:.4f}\n")
    print(classification_report(y_test, y_pred))

    cm = confusion_matrix(y_test, y_pred, labels=model.classes_)
    print(f"Matrica zabune ({list(model.classes_)}):")
    print(cm)

    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print("\n=== Vaznost znacajki ===")
    print(importances.to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=model.classes_)
    disp.plot(ax=ax, cmap='Blues', values_format='d')
    plt.title('Matrica zabune - Random Forest')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png', dpi=150)
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(importances['feature'][::-1], importances['importance'][::-1])
    ax.set_xlabel('Vaznost')
    ax.set_title('Vaznost znacajki za detekciju varanja')
    plt.tight_layout()
    plt.savefig('feature_importance.png', dpi=150)
    plt.close()

    joblib.dump({
        'model': model, 'features': feature_cols,
        'classes': list(model.classes_), 'window_size': WINDOW_SIZE
    }, MODEL_FILE)
    print(f"\nModel spremljen u: {MODEL_FILE}")


if __name__ == "__main__":
    train()
