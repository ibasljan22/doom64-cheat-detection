# Otkrivanje varanja u videoigri Doom 64 korištenjem metoda umjetne inteligencije

Završni rad - sustav za otkrivanje odabranih oblika varanja u videoigri Doom 64
temeljen na analizi gameplay podataka pomoću strojnog učenja (Random Forest).

## Opis

Sustav detektira tri oblika varanja:
- **God mode** - igrač prima napade ali ne gubi health
- **Infinite ammo** - igrač puca ali ne troši municiju
- **Speed hack** - igrač se kreće jako brzo, brže od default brzine u igri

Projekt je izgrađen na [Doom64EX-Plus](https://github.com/atsb/Doom64EX-Plus)
engineu, koji je proširen logging sustavom za prikupljanje gameplay podataka.

## Struktura projekta

```
.
├── src/engine/
│   ├── cheat_logger.c / .h    # Logging sustav (vlastiti dodatak)
│   ├── p_inter.c              # Izmijenjeno: brojac damage_attempts
│   ├── p_pspr.c               # Izmijenjeno: brojac shots_fired
│   ├── p_tick.c               # Izmijenjeno: poziv loggera
│   └── m_cheat.c              # Izmijenjeno: cheat komande (exi, exs)
│
└── AI/
    ├── merge_logs.py          # Spaja vise CSV logova
    ├── prepare_data.py        # Priprema dataset s labelama
    ├── train_model.py         # Trenira Random Forest model
    ├── detect_cheats_ai.py    # Detekcija varanja na cijeloj sesiji
    ├── detect_cheats_ai_segments.py  # Detekcija varanja na segmentima
    ├── data/                  # Prikupljeni gameplay podaci (CSV)
    └── cheat_detector_model.pkl  # Istrenirani model
```

## Prikupljene znacajke

Logger svakih 5 tickova zapisuje 30 znacajki: health, armor, municija (4 tipa),
pozicija, momentum, brzina, delta vrijednosti, damage_attempts (pokusaji
napada na igraca), shots_fired (ispaljeni hici oruzjem koje trosi ammo) itd.

## Koristenje AI sustava

```bash
# 1. Spoji logove po kategoriji
python merge_logs.py "data/test/gameplay_log_*.csv" test_gameplay.csv

# 2. Pripremi dataset
python prepare_data.py

# 3. Treniraj model
python train_model.py

# 4. Detektiraj varanje na snimljenom logu
python detect_cheats_ai.py test_gameplay.csv ili python detect_cheats_ai_segments.py test_gameplay.csv

```

## Metoda

1. **Random Forest klasifikator** na prozorima gameplay-a (~30 sekundi)


## Zahtjevi

- Python 3.x
- pandas, scikit-learn, matplotlib, joblib
- Za build enginea: Visual Studio 2022, FMOD SDK, vcpkg (zlib, libpng, SDL3)

## Napomena o licenci

Engine kod je baziran na Doom64EX-Plus pod GNU GPL v2 licencom.
Game asset datoteke (DOOM64.WAD, DOOMSND.DLS) NISU ukljucene jer su
vlasnistvo nositelja autorskih prava - potrebna je legalna kopija igre.
FMOD SDK takodjer nije ukljucen.
