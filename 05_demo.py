#!/usr/bin/env python3
"""
MINI-KOOLI INFOSUSTEEM -- peamine demo
Ühendab MySQL, MongoDB ja Redis ning näitab kuidas nad koos töötavad.

Enne käivitamist:
  1. MySQL server peab töötama (Windows)
  2. MongoDB server peab töötama (Windows)
  3. Redis peab töötama WSL-is: sudo service redis-server start
  4. Andmed peavad olema sisestatud: käivita kõigepealt
       mysql < 01_schema.sql
       mysql < 02_testandmed.sql
       mongosh < 03_mongodb_setup.js
       python 04_redis_setup.py

Käivitus: python 05_demo.py
"""

import mysql.connector
import pymongo
import redis
import json
from datetime import datetime

MYSQL_CFG = dict(host="localhost", port=3306, user="root", password="", database="kool")
MONGO_URI  = "mongodb://localhost:27017/"
REDIS_CFG  = dict(host="localhost", port=6379, decode_responses=True)


def uhenda():
    """Loome ühendused kõigi kolme andmebaasiga."""
    mysql_conn   = mysql.connector.connect(**MYSQL_CFG)
    mongo_client = pymongo.MongoClient(MONGO_URI)
    mongo_db     = mongo_client["kool_suhtlus"]
    redis_conn   = redis.Redis(**REDIS_CFG)
    print("Koik kolm andmebaasi ühendatud.\n")
    return mysql_conn, mongo_db, redis_conn


def sektsioon(pealkiri):
    print(f"\n{'='*56}")
    print(f"  {pealkiri}")
    print('='*56)


# ============================================================
# Stsenaarium 1: Opilane logib sisse
#
# Sisselogimisel ei hakka me kohe MySQL-ist andmeid lugema.
# Sessioon on juba Redis-sis -- saame kiirelt kätte.
# Samuti on Redis-sis lugemata teadete arv.
# ============================================================
def login_opilane(redis_conn, opilane_id):
    sektsioon(f"1. Opilane #{opilane_id} logib sisse")

    session_key = f"session:user:{opilane_id}"
    raw = redis_conn.get(session_key)

    if raw:
        session = json.loads(raw)
        print(f"  Sessioon leitud Redis-ist: {session['nimi']} ({session['roll']})")
    else:
        print("  Sessioon puudub -- kasutaja peab uuesti sisse logima.")
        return None

    unread = int(redis_conn.get(f"unread:student:{opilane_id}") or 0)
    print(f"  Lugemata teated: {unread}")

    # Märgi kasutaja online-ks
    # setex seab väärtuse ja TTL korraga
    redis_conn.setex(f"online:opilane:{opilane_id}", 300, "true")
    print(f"  Märgitud online-ks (TTL 5 minutit)")

    return session


# ============================================================
# Stsenaarium 2: Tunniplaan -- Redis vahemälu + MySQL fallback
#
# Cache-aside muster:
#   1. Vaata kas Redis-is on olemas
#   2. Kui on -- tagasta sealt (kiire)
#   3. Kui ei ole -- päri MySQL-ist, salvesta Redis-i, tagasta
#
# Eelis: MySQL ei pea iga kord vastama.
# Risk: andmed võivad olla kuni 15 minutit vananenud.
# See on aktsepteeritav tunniplaani puhul.
# ============================================================
def hankige_tunniplaan(mysql_conn, redis_conn, grupp_id):
    sektsioon(f"2. Tunniplaan grupp #{grupp_id} -- vahemälu strateegia")

    cache_key = f"cache:tunniplaan:{grupp_id}"
    cached = redis_conn.get(cache_key)

    if cached:
        print("  Cache HIT -- andmed Redis-ist (kiire)")
        tunnid = json.loads(cached)
    else:
        print("  Cache MISS -- paring MySQL-ist (aeglasem)")
        cur = mysql_conn.cursor(dictionary=True)
        cur.execute("""
            SELECT tu.id, tu.toimub_kell, tu.kestvus_min, tu.ruum, tu.teema,
                   k.nimi AS kursus,
                   CONCAT(t.eesnimi, ' ', t.perenimi) AS opetaja
            FROM tunnid tu
            JOIN kursused k ON k.id = tu.kursus_id
            JOIN opetajad t ON t.id = k.opetaja_id
            JOIN registreerumised r ON r.kursus_id = tu.kursus_id
            JOIN opilased o ON o.id = r.opilane_id
            WHERE o.grupp_id = %s AND r.staatus = 'aktiivne'
            ORDER BY tu.toimub_kell
        """, (grupp_id,))
        tunnid = cur.fetchall()
        for t in tunnid:
            if isinstance(t.get("toimub_kell"), datetime):
                t["toimub_kell"] = t["toimub_kell"].strftime("%Y-%m-%d %H:%M")
        redis_conn.setex(cache_key, 900, json.dumps(tunnid))
        print("  Salvestatud Redis vahemällu (TTL 15 minutit)")

    print(f"\n  Tunniplaan ({len(tunnid)} tundi):")
    for t in tunnid:
        print(f"    {t['toimub_kell']} | {t.get('kursus','?'):20s} | ruum {t.get('ruum','?')}")


# ============================================================
# Stsenaarium 3: Opetaja saadab teate kursusele
#
# Kirjutame MongoDB-sse (teade ise) ja uuendame Redis-i
# (loendurid ja unread märgised). MySQL-i ei puutu --
# teate sisu ei kuulu MySQL-i, ainult courseId viide.
# ============================================================
def saada_teade(mysql_conn, mongo_db, redis_conn, opetaja_id, kursus_id, title, body):
    sektsioon(f"3. Opetaja #{opetaja_id} saadab teate kursusele #{kursus_id}")

    # Lisa MongoDB-sse
    doc = {
        "type": "course_announcement",
        "courseId": kursus_id,
        "teacherId": opetaja_id,
        "title": title,
        "body": body,
        "createdAt": datetime.utcnow(),
        "target": {"type": "course", "id": kursus_id},
        "attachments": [],
        "readBy": []
    }
    result = mongo_db.teated.insert_one(doc)
    print(f"  Teade lisatud MongoDB-sse (id: {result.inserted_id})")

    # Suurenda kursuse teadete loendurit Redis-is
    new_count = redis_conn.incr(f"course:{kursus_id}:announcement_count")
    print(f"  Teadete arv kursuse #{kursus_id} jaoks: {new_count}")

    # Suurenda iga kursuse opilase unread loendurit
    cur = mysql_conn.cursor()
    cur.execute("""
        SELECT opilane_id FROM registreerumised
        WHERE kursus_id = %s AND staatus = 'aktiivne'
    """, (kursus_id,))
    opilased = cur.fetchall()
    for (oid,) in opilased:
        redis_conn.incr(f"unread:student:{oid}")
    print(f"  unread +1 tehtud {len(opilased)} opilase jaoks")


# ============================================================
# Stsenaarium 4: Opilase toolaud
#
# Tüüpiline näide sellest kuidas kolm andmebaasi koos töötavad:
#   - MySQL annab registreeritud kursused
#   - MongoDB annab viimase teate igalt kursuselt
#   - Redis annab lugemata, viimased kursused, online staatus
# ============================================================
def toolaud(mysql_conn, mongo_db, redis_conn, opilane_id):
    sektsioon(f"4. Opilane #{opilane_id} toolaud -- koik kolm baasi")

    # MySQL: millele on opilane registreerunud
    cur = mysql_conn.cursor(dictionary=True)
    cur.execute("""
        SELECT k.id, k.nimi, CONCAT(t.eesnimi,' ',t.perenimi) AS opetaja
        FROM registreerumised r
        JOIN kursused k ON k.id = r.kursus_id
        JOIN opetajad t ON t.id = k.opetaja_id
        WHERE r.opilane_id = %s AND r.staatus = 'aktiivne'
    """, (opilane_id,))
    kursused = cur.fetchall()
    print(f"\n  Registreeritud kursused (MySQL):")
    for k in kursused:
        print(f"    [{k['id']}] {k['nimi']} -- {k['opetaja']}")

    # MongoDB: viimane teade igalt kursuselt
    print(f"\n  Viimased teated (MongoDB):")
    for k in kursused:
        teade = mongo_db.teated.find_one(
            {"courseId": k["id"]}, sort=[("createdAt", -1)]
        )
        if teade:
            print(f"    Kursus #{k['id']}: \"{teade['title']}\"")

    # Redis: kiirinfo
    unread     = redis_conn.get(f"unread:student:{opilane_id}") or 0
    recent_raw = redis_conn.lrange(f"recent:courses:{opilane_id}", 0, -1)
    is_online  = redis_conn.exists(f"online:opilane:{opilane_id}")
    print(f"\n  Redis kiirinfo:")
    print(f"    Lugemata teated : {unread}")
    print(f"    Viimased kursused: {recent_raw}")
    print(f"    Online           : {'jah' if is_online else 'ei'}")


# ============================================================
# Stsenaarium 5: Kursuse statistika MySQL VIEW-ga
#
# VIEW on defineeritud skeemis. Siin näeme et paring on
# lihtsalt "SELECT * FROM v_kursus_statistika" -- kogu JOIN
# loogika on peidetud vaate sisse.
# ============================================================
def kursuse_statistika(mysql_conn):
    sektsioon("5. Kursuse statistika (MySQL VIEW)")
    cur = mysql_conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM v_kursus_statistika")
    rows = cur.fetchall()
    print(f"  {'Kursus':<25} {'Opetaja':<20} {'Opilasi':>8} {'Aktiivseid':>11}")
    print("  " + "-"*67)
    for r in rows:
        print(f"  {r['kursus']:<25} {r['opetaja']:<20} {r['opilasi_kokku']:>8} {r['aktiivseid']:>11}")


# ============================================================
# Stsenaarium 6: Vestluse lugemine MongoDB-st
#
# Kogu vestlus -- koos kõigi sõnumitega -- tuleb ühe
# find_one päringuga. Sõnumid on embedded dokumendis sees.
# ============================================================
def kuva_vestlus(mongo_db):
    sektsioon("6. Vestlus (MongoDB embedded dokumendid)")
    vestlus = mongo_db.vestlused.find_one({"pealkiri": {"$regex": "Matemaatika"}})
    if not vestlus:
        print("  Vestlust ei leitud.")
        return
    print(f"  Vestlus: {vestlus['pealkiri']}")
    print(f"  Liikmeid: {len(vestlus['liikmed'])}")
    print(f"\n  Sonumid:")
    for s in vestlus["sonumid"]:
        kell = s["kell"].strftime("%H:%M") if isinstance(s["kell"], datetime) else s["kell"]
        print(f"    [{kell}] kasutaja#{s['saatjaId']} ({s['saatjaTyyp']}): {s['tekst'][:60]}")


# ============================================================
# Peaprogramm
# ============================================================
if __name__ == "__main__":
    print("=" * 56)
    print("  MINI-KOOLI INFOSUSTEEM -- Python demo")
    print("  MySQL + MongoDB + Redis")
    print("=" * 56)

    try:
        mysql_conn, mongo_db, redis_conn = uhenda()

        login_opilane(redis_conn, opilane_id=1)
        hankige_tunniplaan(mysql_conn, redis_conn, grupp_id=1)
        saada_teade(mysql_conn, mongo_db, redis_conn,
                    opetaja_id=1, kursus_id=1,
                    title="Demo teade",
                    body="See teade loodi demo skriptist.")
        toolaud(mysql_conn, mongo_db, redis_conn, opilane_id=1)
        kursuse_statistika(mysql_conn)
        kuva_vestlus(mongo_db)

        print("\nDemo lopetatud edukalt.")

    except mysql.connector.Error as e:
        print(f"MySQL viga: {e}")
        print("Kontrolli: MySQL server tootab? Kasutaja ja parool on oiged?")
    except pymongo.errors.ConnectionFailure as e:
        print(f"MongoDB viga: {e}")
        print("Kontrolli: MongoDB server tootab?")
    except redis.ConnectionError as e:
        print(f"Redis viga: {e}")
        print("Käivita WSL-is: sudo service redis-server start")
    finally:
        try:
            mysql_conn.close()
            mongo_db.client.close()
        except Exception:
            pass
