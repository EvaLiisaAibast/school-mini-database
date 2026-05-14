# Mini-kooli infosüsteem
## MySQL + MongoDB + Redis + Python

```
kooli_infosusteem/
├── mysql/
│   ├── 01_schema.sql        tabelid ja vaated
│   └── 02_testandmed.sql    naidisandmed
├── mongodb/
│   └── 03_mongodb_setup.js  kollektsioonid ja naidisdokumendid
├── redis/
│   └── 04_redis_setup.py    kiirinfo kiht
└── python/
    ├── 05_demo.py           pohidemonstratsioon
    └── 06_paringud.py       taiendavad mustrid
```

---

## Samm 1 -- MySQL

```bash
mysql -u root -p < mysql/01_schema.sql
mysql -u root -p < mysql/02_testandmed.sql
```

Kontrolli:
```sql
USE kool;
SELECT * FROM v_kursus_statistika;
SELECT * FROM v_opilane_kursused LIMIT 5;
```

---

## Samm 2 -- MongoDB

```bash
mongosh < mongodb/03_mongodb_setup.js
```

Kontrolli mongosh-is:
```js
use("kool_suhtlus")
db.teated.countDocuments()
db.sonumid.countDocuments()
db.vestlused.countDocuments()
db.kommentaarid.countDocuments()
```

---

## Samm 3 -- Redis (WSL Ubuntu)

```bash
sudo service redis-server start
redis-cli ping
```

Windowsi käsurealt:
```bash
python redis/04_redis_setup.py
```

Kontrolli redis-cli-s:
```
redis-cli
GET session:user:1
GET unread:student:5
LRANGE recent:courses:1 0 -1
TTL session:user:1
KEYS online:*
```

---

## Samm 4 -- Python demo

```bash
pip install pymongo mysql-connector-python redis
python python/05_demo.py
python python/06_paringud.py
```

---

## Miks kolm andmebaasi?

| Andmed | Andmebaas | Põhjus |
|--------|-----------|--------|
| Opilased, opetajad, grupid, kursused | MySQL | Tugevad seosed, JOIN-id vajalikud |
| Registreerumised (mitu-mitmele) | MySQL | Relatsiooniline integriteet |
| Tunniplaan, vaated, raportid | MySQL | Keerulised päringud |
| Teated kursusele | MongoDB | Paindlik skeem, readBy massiiv embedded |
| Sonumid opilasele/grupile | MongoDB | Kiire kirjutamine, manused embedded |
| Vestlused | MongoDB | Sonumid otse dokumendis |
| Kommentaarid | MongoDB | Muutuv struktuur, vastused embedded |
| Sessioonid | Redis | Kiire, TTL, ajutine |
| Lugemata teated | Redis | Loendur, incr/decr |
| Online staatus | Redis | TTL = automaatne aegumine |
| Tunniplaani vahemälu | Redis | Cache-aside muster |

---

## Näidispäringud

MySQL -- kes on registreerunud programmeerimisele:
```sql
USE kool;
SELECT o.eesnimi, o.perenimi, g.nimi AS grupp
FROM opilased o
JOIN grupid g ON g.id = o.grupp_id
JOIN registreerumised r ON r.opilane_id = o.id
WHERE r.kursus_id = 4 AND r.staatus = 'aktiivne';
```

MongoDB -- kõik lugemata teated opilasele (courseIds tulevad MySQL-ist):
```js
use("kool_suhtlus")
db.teated.find({
  courseId: { $in: [1, 2, 4] },
  "readBy.studentId": { $ne: 1 }
}).sort({ createdAt: -1 })
```

Redis -- kõik hetkel aktiivsed kasutajad:
```bash
redis-cli KEYS "online:*"
```
