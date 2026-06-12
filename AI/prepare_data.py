import pandas as pd
import os, sys

DATASETS = {
    'normal_gameplay.csv': 'normal',
    'godmode_gameplay.csv': 'godmode',
    'infammo_gameplay.csv': 'infammo',
    'speedhack_gameplay.csv': 'speedhack'
}

all_dfs = []
for filename, label in DATASETS.items():
    if not os.path.exists(filename):
        print(f"UPOZORENJE: {filename} ne postoji")
        continue
    df = pd.read_csv(filename)
    df['label'] = label
    all_dfs.append(df)
    print(f"  {filename}: {len(df)} -> '{label}'")

dataset = pd.concat(all_dfs, ignore_index=True)
dataset = dataset.sample(frac=1, random_state=42).reset_index(drop=True)
dataset.to_csv('training_dataset.csv', index=False)
print(f"\nUkupno: {len(dataset)} redova")
