//cheat_logger.h
//Logging sustav za prikupljanje gameplay podataka

#ifndef __CHEAT_LOGGER__
#define __CHEAT_LOGGER__

#include "doomdef.h"
#include "d_player.h"

//Inicijalizira logger - otvara se CSV datoteka
void CL_Init(void);

//Zapisuje podatke o igracu u CSV - poziva se svaki tick
void CL_LogTick(player_t* player, int gametic);

//Primjenjuje efekte cheatova (infinite ammo, speedhack)
void CL_ApplyCheats(player_t* player);

//Zatvara CSV datoteku
void CL_Close(void);

//Globalni brojac pokusaja damage-a na igraca
//Povecava se u P_DamageMobj cak i ako god mode blokira damage.
//Kljucno za razlikovanje god mode-a od igraca koji izbjegava sav dmg kako igra
extern int g_damageAttempts;

//Globalni brojac shotova oruzjem koje trosi ammo
//Povecava se u P_FireWeapon. Chainsaw/fist se ne broje (am_noammo).
extern int g_shotsFired;

#endif
