# Otkrivanje varanja u videoigri Doom 64 korištenjem metoda umjetne inteligencije

Završni rad - sustav za otkrivanje odabranih oblika varanja u videoigri Doom 64,
temeljen na analizi gameplay podataka pomoću strojnog učenja (Random Forest).

## Opis

Sustav detektira tri oblika varanja isključivo na temelju ponašanja igrača,
bez pristupa memoriji ili sustavu korisnika:

- **God mode** - igrač prima napade, ali ne gubi health - Cheat code: iddqd
- **Infinite ammo** - igrač puca, ali ne troši municiju - Cheat code: exi
- **Speed hack** - igrač se kreće mnogo brže od najveće brzine predviđene igrom - Cheat code: exs

Projekt je izgrađen na engineu [Doom64EX-Plus](https://github.com/atsb/Doom64EX-Plus),
koji je proširen vlastitim logging sustavom za prikupljanje gameplay podataka.
Model na testnom skupu postiže **93 % točnosti** (jednako i pri 5-strukoj unakrsnoj
provjeri), oblici infinite ammo i speed hack prepoznaju se bez pogreške.

## Struktura projekta

```
.
├── src/engine/
│   ├── cheat_logger.c / .h           # Logging sustav (vlastiti dodatak)
│   ├── p_inter.c                     # Izmijenjeno: brojač damage_attempts
│   ├── p_pspr.c                      # Izmijenjeno: brojač shots_fired
│   ├── p_tick.c                      # Izmijenjeno: poziv loggera
│   └── m_cheat.c                     # Izmijenjeno: cheat komande (exi, exs)
│
└── AI/
    ├── merge_logs.py                 # Spaja više CSV logova u jedan
    ├── prepare_data.py               # Spaja kategorije i dodaje labele
    ├── train_model.py                # Trenira Random Forest model
    ├── detect_cheats_ai.py           # Detekcija na cijeloj sesiji (većinsko glasanje)
    ├── detect_cheats_ai_segments.py  # Segmentna detekcija (varanje u dijelu igre)
    ├── data/                         # Prikupljeni gameplay podaci (CSV)
    └── cheat_detector_model.pkl      # Istrenirani model
```

## Prikupljeni podaci

Logger približno 12 puta u sekundi zapisuje redak s 30 stupaca: health, armor, municija
(4 tipa), pozicija, momentum, brzina, delta vrijednosti u odnosu na prethodni
zapis, `damage_attempts` (pokušaji nanošenja štete igraču), `shots_fired`
(ispaljeni pucnjevi oružjem koje troši municiju) itd. Zastavice o aktivnim
cheatovima zapisuju se samo radi labeliranja pri treniranju i nikada se ne
koriste kao ulaz modela.

## Metoda

1. Sirovi logovi dijele se na vremenske prozore od 200 tickova (~17 sekundi).
2. Za svaki prozor izračunava se 16 ponašajnih značajki (npr. omjer ispaljenih
   pucnjeva bez pada municije, omjer primljenih napada bez pada healtha,
   maksimalna brzina i udio visokih brzina).
3. Random Forest klasifikator (200 stabala, max_depth=15) razvrstava svaki
   prozor u jedan od razreda: `normal`, `godmode`, `infammo`, `speedhack`.
4. Odluke po prozorima sažimaju se u konačnu ocjenu sesije na dva načina:
   većinskim glasanjem (cijela sesija) ili segmentno (prijavljuje se svaki
   cheat prisutan u dovoljnom broju prozora, s vremenskim segmentima pojave).

## Korištenje AI sustava

```bash
cd AI

# 1. Spoji logove po kategoriji (nazivi datoteka koje prepare_data.py očekuje)
python merge_logs.py "data/normal/gameplay_log_*.csv"    normal_gameplay.csv
python merge_logs.py "data/godmode/gameplay_log_*.csv"   godmode_gameplay.csv
python merge_logs.py "data/infammo/gameplay_log_*.csv"   infammo_gameplay.csv
python merge_logs.py "data/speedhack/gameplay_log_*.csv" speedhack_gameplay.csv

# 2. Pripremi labelirani dataset (stvara training_dataset.csv)
python prepare_data.py

# 3. Treniraj model (stvara cheat_detector_model.pkl + grafove evaluacije)
python train_model.py

# 4. Detektiraj varanje na novom snimljenom logu
python detect_cheats_ai.py test_gameplay.csv
# ili segmentno, ako je varanje moglo biti aktivno samo u dijelu igre:
python detect_cheats_ai_segments.py test_gameplay.csv
```

Skripte za detekciju očekuju `cheat_detector_model.pkl` u radnom direktoriju.

## Zahtjevi

- Python 3.x
- pandas, scikit-learn, matplotlib, joblib
- Za build enginea: Visual Studio 2022, FMOD SDK, vcpkg (zlib, libpng, SDL3)

## Napomena o licenci

Engine kod baziran je na Doom64EX-Plus pod licencom GNU GPL v2.
Game asset datoteke (DOOM64.WAD, DOOMSND.DLS) **nisu uključene** jer su
vlasništvo nositelja autorskih prava — potrebna je legalna kopija igre
(npr. putem Steama). FMOD SDK također nije uključen.
