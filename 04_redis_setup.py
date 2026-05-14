#!/usr/bin/env python3
"""
MINI-KOOLI INFOSUSTEEM -- Redis kiirinfo kiht
Käivita: python 04_redis_setup.py

Redis asub WSL-i Ubuntus, ühendus localhost:6379 kaudu.

Miks Redis siin?
Redis on võtme-väärtuse andmebaas mis hoiab andmeid mälus.
See teeb ta väga kiireks -- ta ei kirjuta kõvaketasse
(või teeb seda harva). Seetõttu sobib ta hästi:
  - sessioonide hoidmiseks (kas kasutaja on sisse logitud)
  - loendurite jaoks (mitu lugemata teadet)
  - ajutise vahemälu jaoks (tunniplaan, mis uueneb iga 15 min)
  - online-staatuse jaoks (kas kasutaja on aktiivselt lehel)

Tähtis: Redis EI ole kolmas koht kus hoida kooli põhiandmeid.
Kui Redis taaskäivitada, kaovad ajutised andmed -- see on OK
sest need on sessioonid ja vahemälu, mitte tegelikud andmed.
"""

import redis
import json
from datetime import datetime

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

try:
    r.ping()
    print("Redis ühendus OK")
except redis.ConnectionError:
    print("Redis ei vasta.")
    print("Käivita WSL-is: sudo service redis-server start")
    raise SystemExit(1)

# Arenduse ajal puhastame kogu Redis andmebaasi
# Tootmises seda ei tee
r.flushdb()
print("Redis puhastatud (flushdb)\n")


# ============================================================
# 1. Sessioonid  võti: session:user:<id>
#
# Kui kasutaja logib sisse, salvestatakse tema info Redis-sse.
# TTL (time to live) = 3600 sekundit = 1 tund.
# Pärast seda aegub sessioon automaatselt -- Redis teeb seda ise,
# me ei pea ise aegunud andmeid kustutama.
#
# Väärtus on JSON string -- Redis ei tea mis sees on,
# ta hoiab lihtsalt stringi. Meie kood parsib selle tagasi.
# ============================================================
sessions = {
    "session:user:1": json.dumps({"userId": 1, "roll": "opilane", "nimi": "Jaan Magi",  "grupp_id": 1}),
    "session:user:2": json.dumps({"userId": 2, "roll": "opilane", "nimi": "Liis Oja",   "grupp_id": 1}),
    "session:user:3": json.dumps({"userId": 3, "roll": "opilane", "nimi": "Mart Paju",  "grupp_id": 2}),
    "session:user:4": json.dumps({"userId": 4, "roll": "opetaja", "nimi": "Andres Kask","ainekood": "INF101"}),
    "session:user:5": json.dumps({"userId": 5, "roll": "opilane", "nimi": "Peeter Soo", "grupp_id": 3}),
    "session:user:6": json.dumps({"userId": 6, "roll": "opilane", "nimi": "Kadri Vesi", "grupp_id": 3}),
}
for key, val in sessions.items():
    r.setex(key, 3600, val)
print("Sessioonid seatud (TTL 1h):")
for k in sessions:
    print(f"  {k}")


# ============================================================
# 2. Lugemata teadete arv  võti: unread:student:<id>
#
# Iga kord kui opetaja saadab teate, suurendatakse selle
# opilase loendurit (r.incr). Kui opilane avab teate,
# väheneb loendur (r.decr).
#
# Miks mitte MongoDB-st loendada?
# Saaks küll, aga see nõuaks iga lehelaadimisega aggregatsiooni
# päringut MongoDB-s. Redis-is on see ühe käsu asi: r.get(key).
# ============================================================
unread = {
    "unread:student:1": 2,
    "unread:student:2": 0,
    "unread:student:3": 1,
    "unread:student:4": 3,
    "unread:student:5": 5,
    "unread:student:6": 1,
    "unread:student:7": 4,
    "unread:student:8": 2,
}
for key, val in unread.items():
    r.set(key, val)
print("\nLugemata teated:")
for k, v in unread.items():
    print(f"  {k} = {v}")


# ============================================================
# 3. Online staatus  võti: online:<roll>:<id>
#
# TTL = 300 sekundit = 5 minutit.
# Iga kord kui kasutaja teeb midagi lehel (klõpsab, kirjutab),
# uuendatakse TTL. Kui 5 minutit ei tee midagi, aegub
# kirje automaatselt -- kasutaja on "offline".
# See on lihtsam kui eraldi "logout" logika kirjutada.
# ============================================================
online = {
    "online:opetaja:2": "true",
    "online:opetaja:4": "true",
    "online:opilane:1": "true",
    "online:opilane:3": "true",
    "online:opilane:6": "true",
}
for key, val in online.items():
    r.setex(key, 300, val)
print("\nAktiivsed kasutajad (TTL 5min):")
for k in online:
    print(f"  {k}")


# ============================================================
# 4. Viimati vaadatud kursused  võti: recent:courses:<student_id>
#
# Redis List -- järjestatud nimekiri.
# rpush lisab elemendi lõppu, lrange loeb nimekirja.
# Kui tahta ainult 5 viimast, saab kasutada ltrim.
# TTL = 24h.
# ============================================================
recent_courses = {
    1: [4, 1, 2],
    2: [3, 1, 5],
    3: [4, 2],
    4: [1, 3, 4],
    5: [2, 5],
}
for student_id, courses in recent_courses.items():
    key = f"recent:courses:{student_id}"
    r.delete(key)
    for course_id in courses:
        r.rpush(key, course_id)
    r.expire(key, 86400)
print("\nViimati vaadatud kursused (TTL 24h):")
for sid, cl in recent_courses.items():
    print(f"  recent:courses:{sid} = {cl}")


# ============================================================
# 5. Kursuse teadete loendurid  võti: course:<id>:announcement_count
#
# Lihtne number -- mitu teadet kursusel kokku on.
# Seda kasutatakse näiteks badges kuvamiseks ("8 teadet").
# Kasvab iga uue teatega (r.incr), ei aegu (TTL puudub).
# ============================================================
counts = {
    "course:1:announcement_count": 3,
    "course:2:announcement_count": 8,
    "course:3:announcement_count": 2,
    "course:4:announcement_count": 5,
    "course:5:announcement_count": 1,
}
for key, val in counts.items():
    r.set(key, val)
print("\nKursuse teadete loendurid:")
for k, v in counts.items():
    print(f"  {k} = {v}")


# ============================================================
# 6. Tunniplaani vahemälu  võti: cache:tunniplaan:<grupp_id>
#
# TTL = 900 sekundit = 15 minutit.
# Tunniplaan muutub harva. Kui iga opilane iga lehelaadimisega
# MySQL-ist küsiks, teeks see serveri ülekoormatud.
# Selle asemel: MySQL -> Redis (15min) -> kui aegub, MySQL uuesti.
# Seda nimetatakse cache-aside mustrik.
# ============================================================
tunniplaan_cache = {
    "cache:tunniplaan:1": json.dumps([
        {"tund_id": 1, "kell": "2026-05-14 08:00", "kursus": "Matemaatika", "ruum": "201"},
        {"tund_id": 3, "kell": "2026-05-14 09:00", "kursus": "Fusika",      "ruum": "301"},
        {"tund_id": 5, "kell": "2026-05-14 11:00", "kursus": "Inglise keel","ruum": "105"},
    ]),
    "cache:tunniplaan:3": json.dumps([
        {"tund_id": 4, "kell": "2026-05-15 10:00", "kursus": "Fusika",          "ruum": "301"},
        {"tund_id": 6, "kell": "2026-05-15 13:00", "kursus": "Programmeerimine","ruum": "404"},
    ]),
}
for key, val in tunniplaan_cache.items():
    r.setex(key, 900, val)
print("\nTunniplaani vahemälu (TTL 15min):")
for k in tunniplaan_cache:
    print(f"  {k}")


total_keys = r.dbsize()
print(f"\nRedis seadistus valmis -- kokku {total_keys} voit.")
print("""
Votmete struktuur kokkuvotes:
  session:user:<id>               kasutaja sessioon, aegub 1h järel
  unread:student:<id>             lugemata teadete arv
  online:opetaja/opilane:<id>     online staatus, aegub 5min järel
  recent:courses:<student_id>     viimati vaadatud kursused
  course:<id>:announcement_count  teadete loendur kursusel
  cache:tunniplaan:<grupp_id>     vahemälus tunniplaan, aegub 15min järel
""")
