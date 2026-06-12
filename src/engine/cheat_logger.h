// cheat_logger.h
// Logging sustav za prikupljanje gameplay podataka
// Koristi se za AI detekciju varanja (Random Forest)

#ifndef __CHEAT_LOGGER__
#define __CHEAT_LOGGER__

#include "doomdef.h"
#include "d_player.h"

// Inicijalizira logger - otvara CSV datoteku
void CL_Init(void);

// Zapisuje podatke o igracu u CSV - poziva se svaki tick
void CL_LogTick(player_t* player, int gametic);

// Primjenjuje efekte cheatova (infinite ammo, speedhack)
void CL_ApplyCheats(player_t* player);

// Zatvara CSV datoteku
void CL_Close(void);

// Globalni brojac pokusaja damage-a na igraca
// Povecava se u P_DamageMobj cak i ako god mode blokira damage.
// Kljucno za razlikovanje god mode-a od vjestog igraca koji ne prima damage.
extern int g_damageAttempts;

// Globalni brojac ispaljenih hitaca oruzjem koje trosi ammo
// Povecava se u P_FireWeapon. Chainsaw/fist se ne broje (am_noammo).
// Kljucno za razlikovanje infinite ammo od chainsaw igre.
extern int g_shotsFired;

#endif
