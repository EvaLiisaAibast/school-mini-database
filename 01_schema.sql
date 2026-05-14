-- ============================================================
-- MINI-KOOLI INFOSUSTEEM -- MySQL skeem
-- Siin hoiame kooli pohiandmeid: opilased, opetajad, grupid,
-- kursused, tunnid ja registreerumised.
--
-- Miks MySQL? Sellepärast et need andmed on omavahel tugevalt
-- seotud. Näiteks opilane kuulub gruppi, kursus on seotud
-- opetajaga, tund kuulub kursusele jne. Sellist struktuuri
-- on relatsiooniline andmebaas väga hea hoidma.
-- ============================================================

CREATE DATABASE IF NOT EXISTS kool CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE kool;

-- ------------------------------------------------------------
-- Tabel 1: grupid
-- Üks rida = üks klass, näiteks "10A" või "11B"
-- ------------------------------------------------------------
CREATE TABLE grupid (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nimi        VARCHAR(50)  NOT NULL,
    aasta       INT          NOT NULL,   -- mis aastal grupp loodi
    loodud_kell TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabel 2: opetajad
-- Üks rida = üks õpetaja
-- email peab olema unikaalne -- kaks õpetajat ei saa sama emaili kasutada
-- ------------------------------------------------------------
CREATE TABLE opetajad (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    eesnimi     VARCHAR(60)  NOT NULL,
    perenimi    VARCHAR(60)  NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    telefon     VARCHAR(20),
    loodud_kell TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------
-- Tabel 3: opilased
-- Iga opilane kuulub ühte gruppi (grupp_id on võõrvõti)
-- Kui gruppi ei ole olemas, siis MySQL annab vea -- see ongi hea,
-- nii ei saa "rippuvaid" andmeid tekkida.
-- ------------------------------------------------------------
CREATE TABLE opilased (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    eesnimi     VARCHAR(60)  NOT NULL,
    perenimi    VARCHAR(60)  NOT NULL,
    email       VARCHAR(120) NOT NULL UNIQUE,
    grupp_id    INT          NOT NULL,
    loodud_kell TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_opilane_grupp FOREIGN KEY (grupp_id) REFERENCES grupid(id)
);

-- ------------------------------------------------------------
-- Tabel 4: kursused
-- Igal kursusel on üks vastutav opetaja.
-- ainekood on lühike tunnus nagu "MAT101" -- mugav viidata
-- ------------------------------------------------------------
CREATE TABLE kursused (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nimi        VARCHAR(100) NOT NULL,
    kirjeldus   TEXT,
    opetaja_id  INT          NOT NULL,
    ainekood    VARCHAR(20),
    loodud_kell TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_kursus_opetaja FOREIGN KEY (opetaja_id) REFERENCES opetajad(id)
);

-- ------------------------------------------------------------
-- Tabel 5: tunnid
-- Üks rida = üks konkreetne tund kindlal ajal kindlas ruumis.
-- Näiteks "Füüsika, 14. mai kell 09:00, ruum 301"
-- kestvus_min on minutites, vaikimisi 45
-- ------------------------------------------------------------
CREATE TABLE tunnid (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    kursus_id    INT          NOT NULL,
    toimub_kell  DATETIME     NOT NULL,
    kestvus_min  INT          NOT NULL DEFAULT 45,
    ruum         VARCHAR(20),
    teema        VARCHAR(200),
    CONSTRAINT fk_tund_kursus FOREIGN KEY (kursus_id) REFERENCES kursused(id)
);

-- ------------------------------------------------------------
-- Tabel 6: registreerumised
-- See on MITU-MITMELE tabel opilaste ja kursuste vahel.
-- Üks opilane saab olla mitmel kursusel.
-- Ühel kursusel saab olla mitu opilast.
-- Ilma selle tabelita peaks kumbki pool tundma teist poolt --
-- see läheks segaseks. Vahepealne tabel lahendab selle.
--
-- UNIQUE(opilane_id, kursus_id) tagab et sama opilane
-- ei saa sama kursusele kahte korda registreeruda.
-- ------------------------------------------------------------
CREATE TABLE registreerumised (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    opilane_id      INT       NOT NULL,
    kursus_id       INT       NOT NULL,
    registr_kell    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    staatus         ENUM('aktiivne','lopetatud','katkestatud') DEFAULT 'aktiivne',
    UNIQUE KEY uq_reg (opilane_id, kursus_id),
    CONSTRAINT fk_reg_opilane FOREIGN KEY (opilane_id) REFERENCES opilased(id),
    CONSTRAINT fk_reg_kursus  FOREIGN KEY (kursus_id)  REFERENCES kursused(id)
);

-- ============================================================
-- Vaated (VIEW)
--
-- VIEW on nagu salvestatud paring -- ta ei hoia andmeid ise,
-- vaid iga kord kui vaadata, käib ta andmed jooksvalt kokku.
-- See on mugav kui sama JOIN-i paring kordub palju.
-- ============================================================

-- Vaade: iga opilane koos oma grupi ja kursustega
-- Näitab kes millisel kursusel käib ja mis staatuses on
CREATE OR REPLACE VIEW v_opilane_kursused AS
SELECT
    o.id            AS opilane_id,
    CONCAT(o.eesnimi, ' ', o.perenimi) AS opilane,
    g.nimi          AS grupp,
    k.id            AS kursus_id,
    k.nimi          AS kursus,
    CONCAT(t.eesnimi, ' ', t.perenimi) AS opetaja,
    r.staatus
FROM opilased o
JOIN grupid           g ON g.id = o.grupp_id
JOIN registreerumised r ON r.opilane_id = o.id
JOIN kursused         k ON k.id = r.kursus_id
JOIN opetajad         t ON t.id = k.opetaja_id;

-- Vaade: järgmise 7 paeva tunniplaan
-- Kasulik kui tahad näidata "mis tunnid on tulemas"
CREATE OR REPLACE VIEW v_tunniplaan_nadal AS
SELECT
    tu.id,
    tu.toimub_kell,
    tu.kestvus_min,
    tu.ruum,
    tu.teema,
    k.nimi          AS kursus,
    CONCAT(t.eesnimi, ' ', t.perenimi) AS opetaja
FROM tunnid tu
JOIN kursused k ON k.id = tu.kursus_id
JOIN opetajad t ON t.id = k.opetaja_id
WHERE tu.toimub_kell BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)
ORDER BY tu.toimub_kell;

-- Vaade: kursuse statistika
-- Näeb kiiresti mitu opilast igal kursusel on ja mis staatuses
CREATE OR REPLACE VIEW v_kursus_statistika AS
SELECT
    k.id,
    k.nimi                                          AS kursus,
    CONCAT(t.eesnimi, ' ', t.perenimi)              AS opetaja,
    COUNT(r.id)                                     AS opilasi_kokku,
    SUM(r.staatus = 'aktiivne')                     AS aktiivseid,
    SUM(r.staatus = 'lopetatud')                    AS lopetanuid
FROM kursused k
JOIN opetajad t          ON t.id = k.opetaja_id
LEFT JOIN registreerumised r ON r.kursus_id = k.id
GROUP BY k.id, k.nimi, t.eesnimi, t.perenimi;
