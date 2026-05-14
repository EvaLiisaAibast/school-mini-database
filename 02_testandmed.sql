-- ============================================================
-- MINI-KOOLI INFOSUSTEEM -- testandmed
-- Sisestame andmed samasse järjekorda nagu tabelid on loodud.
-- See on oluline -- kui proovid opilast sisestada enne kui
-- grupp on olemas, annab MySQL võõrvõtme vea.
-- ============================================================
USE kool;

-- 4 gruppi
INSERT INTO grupid (nimi, aasta) VALUES
    ('10A', 2025),
    ('10B', 2025),
    ('11A', 2025),
    ('11B', 2025);

-- 4 opetajat
INSERT INTO opetajad (eesnimi, perenimi, email, telefon) VALUES
    ('Tiina',  'Tamm',  'tiina.tamm@kool.ee',  '5551001'),
    ('Margo',  'Sepp',  'margo.sepp@kool.ee',  '5551002'),
    ('Karin',  'Lepp',  'karin.lepp@kool.ee',  '5551003'),
    ('Andres', 'Kask',  'andres.kask@kool.ee', '5551004');

-- 8 opilast, igaüks seotud grupiga
INSERT INTO opilased (eesnimi, perenimi, email, grupp_id) VALUES
    ('Jaan',   'Magi',  'jaan.magi@kool.ee',   1),  -- 10A
    ('Liis',   'Oja',   'liis.oja@kool.ee',    1),  -- 10A
    ('Mart',   'Paju',  'mart.paju@kool.ee',   2),  -- 10B
    ('Anna',   'Rand',  'anna.rand@kool.ee',   2),  -- 10B
    ('Peeter', 'Soo',   'peeter.soo@kool.ee',  3),  -- 11A
    ('Kadri',  'Vesi',  'kadri.vesi@kool.ee',  3),  -- 11A
    ('Tonu',   'Nurm',  'tonu.nurm@kool.ee',   4),  -- 11B
    ('Mari',   'Laas',  'mari.laas@kool.ee',   4);  -- 11B

-- 5 kursust, igaüks seotud opetajaga
INSERT INTO kursused (nimi, kirjeldus, opetaja_id, ainekood) VALUES
    ('Matemaatika',      'Korgkooliks ettevalmistav kursus', 1, 'MAT101'),
    ('Fusika',           'Mehaanika ja elekter',             2, 'FYY101'),
    ('Inglise keel',     'B2 taseme ettevalmistus',          3, 'ING101'),
    ('Programmeerimine', 'Python ja andmebaasid algajatele', 4, 'INF101'),
    ('Keemia',           'Orgaaniline keemia',               2, 'KEE101');

-- Tunnid (konkreetsed tunnid ajakavas)
INSERT INTO tunnid (kursus_id, toimub_kell, kestvus_min, ruum, teema) VALUES
    (1, '2026-05-14 08:00:00', 45, '201', 'Trigonomeetria'),
    (1, '2026-05-16 08:00:00', 45, '201', 'Integraalarvestus'),
    (2, '2026-05-14 09:00:00', 45, '301', 'Elektrivali'),
    (2, '2026-05-15 10:00:00', 45, '301', 'Kondensaator'),
    (3, '2026-05-14 11:00:00', 45, '105', 'Present Perfect'),
    (4, '2026-05-15 13:00:00', 90, '404', 'Python: funktsioonid'),
    (4, '2026-05-19 13:00:00', 90, '404', 'Python: klassid'),
    (5, '2026-05-16 10:00:00', 45, '302', 'Alkuulid');

-- Registreerumised: opilane <-> kursus (mitu-mitmele)
-- Üks opilane võib olla mitmel kursusel, see ongi mõte
INSERT INTO registreerumised (opilane_id, kursus_id, staatus) VALUES
    (1, 1, 'aktiivne'), (1, 2, 'aktiivne'), (1, 4, 'aktiivne'),
    (2, 1, 'aktiivne'), (2, 3, 'aktiivne'), (2, 5, 'aktiivne'),
    (3, 2, 'aktiivne'), (3, 4, 'aktiivne'),
    (4, 1, 'aktiivne'), (4, 3, 'aktiivne'), (4, 4, 'aktiivne'),
    (5, 2, 'aktiivne'), (5, 5, 'aktiivne'),
    (6, 1, 'aktiivne'), (6, 2, 'lopetatud'), (6, 3, 'aktiivne'),
    (7, 4, 'aktiivne'), (7, 5, 'aktiivne'),
    (8, 1, 'aktiivne'), (8, 4, 'aktiivne'), (8, 3, 'aktiivne');
