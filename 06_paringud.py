#!/usr/bin/env python3
"""
MINI-KOOLI INFOSUSTEEM -- täiendavad mustrid ja päringud
Näitab kuidas andmebaasid koos töötavad -- ristpäringud,
cache invalideerumine ja MongoDB agregatsioonikonveier.

Käivitus: python 06_paringud.py
"""

import mysql.connector
import pymongo
import redis
import json
from datetime import datetime

MYSQL_CFG = dict(host="localhost", port=3306, user="root", password="", database="kool")
MONGO_URI  = "mongodb://localhost:27017/"
REDIS_CFG  = dict(host="localhost", port=6379, decode_responses=True)


def sektsioon(pealkiri):
    print(f"\n{'='*58}")
    print(f"  {pealkiri}")
    print('='*58)


# ============================================================
# Muster 1: Cache-Aside
#
# Küsimus: kas me peame MySQL-ist iga kord lugema?
# Vastus: ei, kui andmed muutuvad harva.
#
# Cache-aside töötab nii:
#   1. Kas Redis-is on olemas?
#   2. Jah -> tagasta Redis-ist (kiire, MySQL-i ei puudutata)
#   3. Ei  -> loe MySQL-ist, salvesta Redis-i, tagasta
#
# Puudus: andmed võivad olla kuni TTL jooksul vananenud.
# Selleks valida TTL mõistlik -- tunniplaan 10 min, hinne 0 min.
# ============================================================
def cache_aside_demo(mysql_conn, redis_conn):
    sektsioon("Muster 1: Cache-Aside (opetaja tunniplaan)")

    def hankige_opetaja_tunnid(opetaja_id):
        cache_key = f"cache:opetaja:{opetaja_id}:tunnid"
        ttl = 600  # 10 minutit

        raw = redis_conn.get(cache_key)
        if raw:
            print(f"  CACHE HIT: opetaja #{opetaja_id} tunnid Redis-ist")
            return json.loads(raw)

        print(f"  CACHE MISS: paring MySQL-ist...")
        cur = mysql_conn.cursor(dictionary=True)
        cur.execute("""
            SELECT tu.id, tu.toimub_kell, tu.ruum, tu.teema, k.nimi AS kursus
            FROM tunnid tu
            JOIN kursused k ON k.id = tu.kursus_id
            WHERE k.opetaja_id = %s
            ORDER BY tu.toimub_kell
        """, (opetaja_id,))
        tunnid = cur.fetchall()
        for t in tunnid:
            if isinstance(t.get("toimub_kell"), datetime):
                t["toimub_kell"] = t["toimub_kell"].strftime("%Y-%m-%d %H:%M")
        redis_conn.setex(cache_key, ttl, json.dumps(tunnid))
        print(f"  Salvestatud Redis-i (TTL {ttl}s)")
        return tunnid

    tunnid = hankige_opetaja_tunnid(2)   # esimene kord -- MySQL-ist
    print(f"  Leitud {len(tunnid)} tundi.")

    tunnid2 = hankige_opetaja_tunnid(2)  # teine kord -- peaks tulema Redis-ist
    print(f"  Teine päring tagastas {len(tunnid2)} tundi.")


# ============================================================
# Muster 2: Write-Through ehk kirjutamine läbi
#
# Kui andmed muutuvad, peame:
#   1. Kirjutama MySQL-i (allikas tõde)
#   2. Kustutama Redis cache-i (et vananenud andmeid ei kuvataks)
#
# Seda nimetatakse cache invalideerimiseks.
# Alternatiiv oleks ka Redis-i kohe uuendada -- aga lihtsam on
# lihtsalt kustutada ja lasta järgmisel päringul uuesti laadida.
# ============================================================
def registreeru_kursusele(mysql_conn, redis_conn, opilane_id, kursus_id):
    sektsioon(f"Muster 2: Write-Through -- opilane #{opilane_id} registreerub kursusele #{kursus_id}")

    cur = mysql_conn.cursor()

    # Kontrolli duplikaati enne sisestamist
    cur.execute(
        "SELECT id FROM registreerumised WHERE opilane_id=%s AND kursus_id=%s",
        (opilane_id, kursus_id)
    )
    if cur.fetchone():
        print("  See opilane on juba sellele kursusele registreeritud.")
        return

    # Kirjuta MySQL-i
    cur.execute(
        "INSERT INTO registreerumised (opilane_id, kursus_id, staatus) VALUES (%s, %s, 'aktiivne')",
        (opilane_id, kursus_id)
    )
    mysql_conn.commit()
    print(f"  MySQL: registreerumine lisatud")

    # Invaliideeri grupi tunniplaan cache -- see opilane on nüüd uuel kursusel
    # Järgmine kord kui tunniplaan laetakse, loetakse MySQL-ist uuesti
    cur.execute("SELECT grupp_id FROM opilased WHERE id=%s", (opilane_id,))
    row = cur.fetchone()
    if row:
        grupp_id = row[0]
        deleted = redis_conn.delete(f"cache:tunniplaan:{grupp_id}")
        print(f"  Redis: cache:tunniplaan:{grupp_id} kustutatud (invaliideeritud: {deleted})")

    redis_conn.incr(f"course:{kursus_id}:announcement_count")
    print(f"  Redis: kursuse #{kursus_id} loendur suurendatud")


# ============================================================
# Muster 3: MongoDB agregatsioonikonveier
#
# Agregatsioonikonveier on MongoDB viis keerulisemaks andmete
# töötlemiseks. See sarnaneb SQL-i GROUP BY + COUNT-ga.
#
# $match -- filtreeri (nagu WHERE)
# $project -- vali väljad ja arvuta (nagu SELECT)
# $sort -- järjesta (nagu ORDER BY)
#
# Siin loendame: mitu opilast on iga teate lugenud?
# ============================================================
def teadete_statistika(mongo_db):
    sektsioon("Muster 3: MongoDB agregatsioonikonveier -- lugemisstatistika")

    pipeline = [
        # Ainult kursuseteated (mitte grupiteated)
        {"$match": {"type": "course_announcement"}},
        # Arvuta mitu lugejat on ja kas manuseid on
        {"$project": {
            "courseId": 1,
            "title": 1,
            "lugejaCount": {"$size": "$readBy"},
            "onManuseid": {"$gt": [{"$size": "$attachments"}, 0]}
        }},
        # Enim loetud esimesena
        {"$sort": {"lugejaCount": -1}}
    ]

    tulemused = list(mongo_db.teated.aggregate(pipeline))
    print(f"  {'Kursus':>8} | {'Lugejaid':>9} | {'Manused':>8} | Pealkiri")
    print("  " + "-"*60)
    for t in tulemused:
        manused = "jah" if t.get("onManuseid") else "ei"
        print(f"  {t['courseId']:>8} | {t['lugejaCount']:>9} | {manused:>8} | {t['title'][:35]}")


# ============================================================
# Muster 4: Teate märkimine loetuks
#
# See muster uuendab kahte andmebaasi korraga:
#   1. MongoDB: lisa opilane teate readBy massiivi
#   2. Redis: vähenda unread loendurit
#
# Tähtis: Redis-i loendur peab peegeldama tegelikku olukorda.
# Kui MongoDB uuendamine õnnestub aga Redis ei -- tekib ebakõla.
# Sellises süsteemis peaks olema ka "sync" loogika, mis
# aeg-ajalt MongoDB-st loendab ja Redis-i parandab.
# ============================================================
def märgi_loetuks(mongo_db, redis_conn, opilane_id, kursus_id):
    sektsioon(f"Muster 4: Teate lugemismärgis -- opilane #{opilane_id}, kursus #{kursus_id}")

    # Leia viimane teade mida see opilane pole lugenud
    teade = mongo_db.teated.find_one({
        "courseId": kursus_id,
        "readBy.studentId": {"$ne": opilane_id}
    }, sort=[("createdAt", -1)])

    if not teade:
        print("  Koik teated on loetud.")
        return

    print(f"  Leitud lugemata teade: \"{teade['title']}\"")

    # Lisa readBy kirje MongoDB-sse
    # $push lisab massiivi uue elemendi
    mongo_db.teated.update_one(
        {"_id": teade["_id"]},
        {"$push": {"readBy": {
            "studentId": opilane_id,
            "readAt": datetime.utcnow()
        }}}
    )
    print(f"  MongoDB: readBy uuendatud")

    # Vähenda Redis loendurit -- aga ära mine alla nulli
    unread_key = f"unread:student:{opilane_id}"
    current = int(redis_conn.get(unread_key) or 0)
    if current > 0:
        new_val = redis_conn.decr(unread_key)
        print(f"  Redis: unread:student:{opilane_id} = {current} -> {new_val}")
    else:
        print(f"  Redis: loendur on juba 0, ei vähenda")


# ============================================================
# Muster 5: Online kasutajate nimekiri
#
# Redis teab kes on online (TTL aegub kui ei ole aktiivne).
# Aga Redis ei tea nime -- ainult id-d.
# MySQL teab nime -- aga ei tea kes on online.
# Seetõttu kasutame mõlemat koos.
# ============================================================
def online_kasutajad(mysql_conn, redis_conn):
    sektsioon("Muster 5: Online kasutajad (Redis + MySQL)")

    # Loe Redis-ist kõik online võtmed
    opetaja_keys = redis_conn.keys("online:opetaja:*")
    opilane_keys = redis_conn.keys("online:opilane:*")

    opetaja_ids = [int(k.split(":")[-1]) for k in opetaja_keys]
    opilane_ids = [int(k.split(":")[-1]) for k in opilane_keys]

    cur = mysql_conn.cursor(dictionary=True)

    if opetaja_ids:
        fmt = ",".join(["%s"] * len(opetaja_ids))
        cur.execute(f"SELECT id, CONCAT(eesnimi,' ',perenimi) AS nimi FROM opetajad WHERE id IN ({fmt})", opetaja_ids)
        print("  Online opetajad:")
        for row in cur.fetchall():
            ttl = redis_conn.ttl(f"online:opetaja:{row['id']}")
            print(f"    {row['nimi']:<25}  (TTL: {ttl}s)")

    if opilane_ids:
        fmt = ",".join(["%s"] * len(opilane_ids))
        cur.execute(f"SELECT id, CONCAT(eesnimi,' ',perenimi) AS nimi FROM opilased WHERE id IN ({fmt})", opilane_ids)
        print("  Online opilased:")
        for row in cur.fetchall():
            ttl = redis_conn.ttl(f"online:opilane:{row['id']}")
            print(f"    {row['nimi']:<25}  (TTL: {ttl}s)")

    print(f"\n  Kokku online: {len(opetaja_ids)} opetajat, {len(opilane_ids)} opilast")


# ============================================================
# Muster 6: Ristpäring -- MongoDB teade + MySQL kontekst
#
# MongoDB hoiab ainult courseId ja teacherId viiteid.
# Kursuse nime ja opetaja nime saame MySQL-ist.
# See on tüüpiline muster sellises süsteemis.
#
# Tähtis: ühendame andmed Python koodis, mitte andmebaasis.
# Kahel andmebaasil ei saa JOIN-i teha -- seetõttu teeme
# kõigepealt kõik MySQL päringud, seejärel kõik MongoDB päringud
# ja kombineerime tulemused mälus.
# ============================================================
def ristpäring(mysql_conn, mongo_db):
    sektsioon("Muster 6: Ristpäring -- MongoDB + MySQL")

    teated = list(mongo_db.teated.find({}, sort=[("createdAt", -1)]))
    if not teated:
        print("  Teateid pole.")
        return

    # Kogume kokku kõik unikaalsed id-d
    course_ids  = list({t["courseId"]  for t in teated if "courseId"  in t})
    teacher_ids = list({t["teacherId"] for t in teated if "teacherId" in t})

    cur = mysql_conn.cursor(dictionary=True)

    # Üks päring kõigi kursuste jaoks (mitte N eraldi päringut)
    fmt_c = ",".join(["%s"] * len(course_ids))
    cur.execute(f"SELECT id, nimi FROM kursused WHERE id IN ({fmt_c})", course_ids)
    kursused = {r["id"]: r["nimi"] for r in cur.fetchall()}

    fmt_t = ",".join(["%s"] * len(teacher_ids))
    cur.execute(f"SELECT id, CONCAT(eesnimi,' ',perenimi) AS nimi FROM opetajad WHERE id IN ({fmt_t})", teacher_ids)
    opetajad = {r["id"]: r["nimi"] for r in cur.fetchall()}

    # Kombineeri Python sõnastikest
    print(f"  {'Kursus':<22} {'Opetaja':<18} {'Lugejaid':>9} | Pealkiri")
    print("  " + "-"*70)
    for t in teated:
        kursus  = kursused.get(t.get("courseId"), "?")
        opetaja = opetajad.get(t.get("teacherId"), "?")
        lugejaid = len(t.get("readBy", []))
        print(f"  {kursus:<22} {opetaja:<18} {lugejaid:>9} | {t['title'][:30]}")


# ============================================================
# Peaprogramm
# ============================================================
if __name__ == "__main__":
    print("=" * 58)
    print("  MINI-KOOLI INFOSUSTEEM -- täiendavad mustrid")
    print("=" * 58)

    try:
        mysql_conn   = mysql.connector.connect(**MYSQL_CFG)
        mongo_client = pymongo.MongoClient(MONGO_URI)
        mongo_db     = mongo_client["kool_suhtlus"]
        redis_conn   = redis.Redis(**REDIS_CFG)
        print("Koik ühendused OK.\n")

        cache_aside_demo(mysql_conn, redis_conn)
        registreeru_kursusele(mysql_conn, redis_conn, opilane_id=2, kursus_id=2)
        teadete_statistika(mongo_db)
        märgi_loetuks(mongo_db, redis_conn, opilane_id=5, kursus_id=2)
        online_kasutajad(mysql_conn, redis_conn)
        ristpäring(mysql_conn, mongo_db)

        print("\nKoik mustrid demonstreeritud edukalt.")

    except mysql.connector.Error as e:
        print(f"MySQL viga: {e}")
    except pymongo.errors.ConnectionFailure as e:
        print(f"MongoDB viga: {e}")
    except redis.ConnectionError as e:
        print(f"Redis viga: {e}")
        print("WSL-is: sudo service redis-server start")
    finally:
        try:
            mysql_conn.close()
            mongo_client.close()
        except Exception:
            pass
