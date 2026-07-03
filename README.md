# Otkrivanje varanja u videoigri Doom 64 koristenjem metoda umjetne inteligencije

Zavrsni rad - sustav za otkrivanje odabranih oblika varanja u videoigri Doom 64
temeljen na analizi gameplay podataka pomocu strojnog ucenja (Random Forest).

## Opis

Sustav detektira tri oblika varanja:
- **God mode** - igrac prima napade ali ne gubi health
- **Infinite ammo** - igrac puca ali ne trosi municiju
- **Speed hack** - igrac se krece jako brzo, brze od default brzine u igri

Projekt je izgradjen na [Doom64EX-Plus](https://github.com/atsb/Doom64EX-Plus)
engineu, koji je prosiren logging sustavom za prikupljanje gameplay podataka.

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
python merge_logs.py "data/normal/gameplay_log_*.csv" normal_gameplay.csv

# 2. Pripremi dataset
python prepare_data.py

# 3. Treniraj model
python train_model.py

# 4. Detektiraj varanje na snimljenom logu
python detect_cheats.py gameplay_log_XXXXX.csv

# 5. Detekcija u stvarnom vremenu (pokrenuti prije igre)
python realtime_monitor.py
```

## Metoda

Sustav koristi hibridni pristup:
1. **Random Forest klasifikator** na prozorima gameplay-a (~15 sekundi)
2. **Session-level pravila** koja koriste tvrde signale (damage_attempts,
   shots_fired) za pouzdano razlikovanje varanja od legitimnih edge-case
   scenarija (npr. vjesti igrac koji ne prima damage, ili koristenje
   chainsaw-a koji ne trosi municiju).

## Zahtjevi

- Python 3.x
- pandas, scikit-learn, matplotlib, joblib
- Za build enginea: Visual Studio 2022, FMOD SDK, vcpkg (zlib, libpng, SDL3)

## Napomena o licenci

Engine kod je baziran na Doom64EX-Plus pod GNU GPL v2 licencom.
Game asset datoteke (DOOM64.WAD, DOOMSND.DLS) NISU ukljucene jer su
vlasnistvo nositelja autorskih prava - potrebna je legalna kopija igre.
FMOD SDK takodjer nije ukljucen.
