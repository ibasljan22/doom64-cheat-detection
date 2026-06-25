// cheat_logger.c
//Logging sustav za prikupljanje gameplay podataka
//Zapisuje CSV datoteku s podacima o igracu svaki game tick
//Podaci se koriste za treniranje Random Forest modela

#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <math.h>
#include "cheat_logger.h"
#include "doomdef.h"
#include "d_player.h"

static FILE* logFile = NULL;
static int lastHealth = 0;
static int lastAmmo[4] = { 0, 0, 0, 0 };
static fixed_t lastX = 0;
static fixed_t lastY = 0;
static fixed_t lastZ = 0;
static int logInterval = 5;  //logiranje svakih 5 tickova (oko 7 puta/sec)
static int tickCounter = 0;
static int isFirstLog = 1;   //za preskakanje delta racunanja u prvom logu

//Globalni brojaci (definicija)
int g_damageAttempts = 0;
int g_shotsFired = 0;

//Zadnje vrijednosti za delta izracun
static int lastDamageAttempts = 0;
static int lastShotsFired = 0;


//CL_Init
//Otvara CSV datoteku i zapisuje header red
void CL_Init(void) {
    char filename[256];
    time_t t = time(NULL);
    struct tm* tm_info = localtime(&t);

    strftime(filename, sizeof(filename), "gameplay_log_%Y%m%d_%H%M%S.csv", tm_info);

    logFile = fopen(filename, "w");
    if (!logFile) {
        return;
    }

    //Resetiranje stanja za novi log
    isFirstLog = 1;
    tickCounter = 0;

    //CSV header
    fprintf(logFile,
        "tick,"
        "health,"
        "armor,"
        "ammo_bullets,"
        "ammo_shells,"
        "ammo_cells,"
        "ammo_rockets,"
        "pos_x,"
        "pos_y,"
        "pos_z,"
        "mom_x,"
        "mom_y,"
        "mom_z,"
        "speed,"
        "health_delta,"
        "ammo_bullets_delta,"
        "ammo_shells_delta,"
        "ammo_cells_delta,"
        "ammo_rockets_delta,"
        "distance_delta,"
        "damage_count,"
        "attack_down,"
        "cheats_flag,"
        "god_mode,"
        "noclip,"
        "infinite_ammo,"
        "speedhack,"
        "damage_attempts,"
        "shots_fired,"
        "player_state\n"
    );

    fflush(logFile);
}

//CL_ApplyCheats
//Primjenjuje efekte za infinite ammo i speedhack cheatove
//Poziva se iz P_Ticker prije CL_LogTick
void CL_ApplyCheats(player_t* player) {
    int i;
    fixed_t maxMom;
    int isMoving;

    if (!player || !player->mo) {
        return;
    }

    //Infinite ammo: ammo se ne koristi kod pucanja
    if (player->cheats & CF_INFAMMO) {
        for (i = 0; i < NUMAMMO; i++) {
            player->ammo[i] = player->maxammo[i];
        }
    }

    //Speed hack: 1.5x brzina
    if (player->cheats & CF_SPEEDHACK) {
        //Provjera pritisce li igrac tipku za kretanje
        isMoving = (player->cmd.forwardmove != 0) || (player->cmd.sidemove != 0);

        if (isMoving) {
            //Maksimalni momentum
            maxMom = 35 * FRACUNIT;

            player->mo->momx = (player->mo->momx * 3) / 2;
            player->mo->momy = (player->mo->momy * 3) / 2;

            //Limit postavljen da se ne probija kroz zidove
            if (player->mo->momx > maxMom)  player->mo->momx = maxMom;
            if (player->mo->momx < -maxMom) player->mo->momx = -maxMom;
            if (player->mo->momy > maxMom)  player->mo->momy = maxMom;
            if (player->mo->momy < -maxMom) player->mo->momy = -maxMom;
        }
    }
}

//CL_LogTick
//Zapisuje jedan red podataka u CSV
void CL_LogTick(player_t* player, int gametic) {
    fixed_t dx, dy, dz;
    double speed, distance;
    int healthDelta;
    int ammoDelta[4];
    int currentAmmo[4];
    int currentHealth;
    int i;

    if (!logFile) {
        return;
    }

    if (!player || !player->mo) {
        return;
    }

    //Logiranje svakih N tickova za smanjenje velicine datoteke
    tickCounter++;
    if (tickCounter < logInterval) {
        return;
    }
    tickCounter = 0;

    //Trenutni health
    currentHealth = player->mo->health;

    //Trenutni ammo
    for (i = 0; i < 4; i++) {
        if (i < NUMAMMO) {
            currentAmmo[i] = player->ammo[i];
        }
        else {
            currentAmmo[i] = 0;
        }
    }

    //Prvi log: nemamo prethodne vrijednosti, postavi ih i preskoci delte
    if (isFirstLog) {
        lastHealth = currentHealth;
        for (i = 0; i < 4; i++) {
            lastAmmo[i] = currentAmmo[i];
        }
        lastX = player->mo->x;
        lastY = player->mo->y;
        lastZ = player->mo->z;
        lastDamageAttempts = g_damageAttempts;
        lastShotsFired = g_shotsFired;
        isFirstLog = 0;
    }

    //Izracun delta vrijednosti
    healthDelta = currentHealth - lastHealth;

    for (i = 0; i < 4; i++) {
        ammoDelta[i] = currentAmmo[i] - lastAmmo[i];
    }

    //Izracun brzine iz momenta
    dx = player->mo->momx;
    dy = player->mo->momy;
    dz = player->mo->momz;

    speed = sqrt(
        ((double)dx / FRACUNIT) * ((double)dx / FRACUNIT) +
        ((double)dy / FRACUNIT) * ((double)dy / FRACUNIT) +
        ((double)dz / FRACUNIT) * ((double)dz / FRACUNIT)
    );

    //Udaljenost od zadnje pozicije
    distance = sqrt(
        ((double)(player->mo->x - lastX) / FRACUNIT) * ((double)(player->mo->x - lastX) / FRACUNIT) +
        ((double)(player->mo->y - lastY) / FRACUNIT) * ((double)(player->mo->y - lastY) / FRACUNIT)
    );

    //Zapisi CSV red
    fprintf(logFile,
        "%d,"       //tick
        "%d,"       //health
        "%d,"       //armor
        "%d,"       //ammo_bullets
        "%d,"       //ammo_shells
        "%d,"       //ammo_cells
        "%d,"       //ammo_rockets
        "%d,"       //pos_x (fixed point)
        "%d,"       //pos_y
        "%d,"       //pos_z
        "%d,"       //mom_x
        "%d,"       //mom_y
        "%d,"       //mom_z
        "%.4f,"     //speed
        "%d,"       //health_delta
        "%d,"       //ammo_bullets_delta
        "%d,"       //ammo_shells_delta
        "%d,"       //ammo_cells_delta
        "%d,"       //ammo_rockets_delta
        "%.4f,"     //distance_delta
        "%d,"       //damage_count
        "%d,"       //attack_down
        "%d,"       //cheats_flag
        "%d,"       //god_mode
        "%d,"       //noclip
        "%d,"       //infinite_ammo
        "%d,"       //speedhack
        "%d,"       //damage_attempts (delta)
        "%d,"       //shots_fired (delta)
        "%d\n",     //player_state
        gametic,
        currentHealth,
        player->armorpoints,
        currentAmmo[0],
        currentAmmo[1],
        currentAmmo[2],
        currentAmmo[3],
        player->mo->x >> FRACBITS,
        player->mo->y >> FRACBITS,
        player->mo->z >> FRACBITS,
        player->mo->momx,
        player->mo->momy,
        player->mo->momz,
        speed,
        healthDelta,
        ammoDelta[0],
        ammoDelta[1],
        ammoDelta[2],
        ammoDelta[3],
        distance,
        player->damagecount,
        player->attackdown,
        player->cheats,
        (player->cheats & CF_GODMODE) ? 1 : 0,
        (player->cheats & CF_NOCLIP) ? 1 : 0,
        (player->cheats & CF_INFAMMO) ? 1 : 0,
        (player->cheats & CF_SPEEDHACK) ? 1 : 0,
        g_damageAttempts - lastDamageAttempts,
        g_shotsFired - lastShotsFired,
        (int)player->playerstate
    );

    //Spremamnje zadnje vrijednosti za delta izracun
    lastHealth = currentHealth;
    for (i = 0; i < 4; i++) {
        lastAmmo[i] = currentAmmo[i];
    }
    lastX = player->mo->x;
    lastY = player->mo->y;
    lastZ = player->mo->z;
    lastDamageAttempts = g_damageAttempts;
    lastShotsFired = g_shotsFired;

    //Flush svakih 100 zapisa
    if ((gametic / logInterval) % 100 == 0) {
        fflush(logFile);
    }
}

//CL_Close
//Zatvaramo log datoteku
void CL_Close(void) {
    if (logFile) {
        fflush(logFile);
        fclose(logFile);
        logFile = NULL;
    }
}
