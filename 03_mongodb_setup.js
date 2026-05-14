// ============================================================
// MINI-KOOLI INFOSUSTEEM -- MongoDB kollektsioonid
// Käivita: mongosh < 03_mongodb_setup.js
//
// Miks MongoDB siin?
// Suhtlusandmed (teated, sõnumid, kommentaarid) ei ole alati
// ühesuguse struktuuriga. Ühel teatel võib olla manus,
// teisel mitte. Ühes kommentaaris on vastused, teises mitte.
// MongoDB ei nõua et kõik dokumendid oleksid ühesugused --
// iga dokument võib olla erinev. See on tema tugevus siin.
//
// Tähtis: MongoDB-s EI hoia me opilaste ega kursuste põhiandmeid.
// courseId, teacherId, studentId on viited MySQL-i kirjetele.
// ============================================================

use("kool_suhtlus");

// Puhasta arenduse ajal -- tootmises seda ei tee
db.teated.drop();
db.sonumid.drop();
db.vestlused.drop();
db.kommentaarid.drop();

// ============================================================
// Kollektsioon 1: teated
// Opetaja saadab teate kursusele või grupile.
//
// readBy on massiiv -- iga opilane kes on lugenud lisatakse sinna.
// See on nn "embedded" struktuur: lugemise info on otse dokumendis,
// mitte eraldi tabelis. MongoDB-s on see tavaline ja mugav.
//
// attachments on samuti embedded -- manus on osa teatest,
// mitte eraldi kogus. Kuna iga teade võib olla erineva arvu
// manustega (või üldse mitte), sobib see hästi MongoDB-sse.
// ============================================================
db.teated.insertMany([
  {
    type: "course_announcement",
    courseId: 2,        // viide MySQL kursused.id = 2 (Fusika)
    teacherId: 2,       // viide MySQL opetajad.id = 2 (Margo Sepp)
    title: "Kontrolltoo esmaspäeval",
    body: "Korrake vahelduvvoolu ja trafosid. Valemileht lubatud.",
    createdAt: new Date("2026-05-12T10:30:00Z"),
    target: { type: "course", id: 2 },
    attachments: [],
    readBy: [
      { studentId: 3, readAt: new Date("2026-05-12T11:05:00Z") },
      { studentId: 5, readAt: new Date("2026-05-12T12:20:00Z") }
    ]
  },
  {
    type: "course_announcement",
    courseId: 4,        // Programmeerimine
    teacherId: 4,
    title: "Kodutoo tahtaeg pikendatud",
    body: "Projekti esitamise tahtaeg on nuud 20. mai kell 23:59.",
    createdAt: new Date("2026-05-13T08:00:00Z"),
    target: { type: "course", id: 4 },
    // See teade erineb eelmisest -- siin on manus.
    // MySQL-is peaks see olema eraldi tabel. MongoDB-s lisame lihtsalt välja.
    attachments: [
      { filename: "projekti_juhend_v2.pdf", size: 204800, mimeType: "application/pdf" }
    ],
    readBy: [
      { studentId: 1, readAt: new Date("2026-05-13T09:10:00Z") },
      { studentId: 3, readAt: new Date("2026-05-13T09:45:00Z") },
      { studentId: 4, readAt: new Date("2026-05-13T10:00:00Z") }
    ]
  },
  {
    type: "course_announcement",
    courseId: 1,        // Matemaatika
    teacherId: 1,
    title: "Lisakonsultatsioon reedel",
    body: "Ruumis 201, kell 14:00-15:30. Koik on oodatud.",
    createdAt: new Date("2026-05-13T07:30:00Z"),
    target: { type: "course", id: 1 },
    attachments: [],
    readBy: []          // keegi ei ole veel lugenud
  },
  {
    // See on grupiteade, mitte kursuseteade -- type on erinev.
    // MySQL-is peaks see olema täiesti eraldi tabel.
    // MongoDB-s lisame lihtsalt erineva type väärtuse.
    type: "group_announcement",
    teacherId: 3,
    title: "11A grupi ekskursioon",
    body: "Reedel 16. mail soIdame Tartu Ulikooli. Kogunemine kell 7:45 koolimaja ees.",
    createdAt: new Date("2026-05-11T15:00:00Z"),
    target: { type: "group", id: 3 },   // viide MySQL grupid.id = 3 (11A)
    attachments: [],
    readBy: [
      { studentId: 5, readAt: new Date("2026-05-11T16:00:00Z") },
      { studentId: 6, readAt: new Date("2026-05-11T17:30:00Z") }
    ]
  }
]);

// ============================================================
// Kollektsioon 2: sonumid
// Isiklikud sõnumid opetajalt opilasele või grupile.
// saatjaTyyp ja saajaTyyp ütlevad kas tegu on opetaja või opilasega.
// ============================================================
db.sonumid.insertMany([
  {
    saatjaId: 1,
    saatjaTyyp: "opetaja",
    saajaTyyp: "opilane",
    saajaId: 2,         // viide MySQL opilased.id = 2 (Liis Oja)
    tekst: "Liis, sinu referaat oli väga hea. Moned soovitused lisasin faili.",
    saadetudKell: new Date("2026-05-12T14:20:00Z"),
    loetud: true,
    loetudKell: new Date("2026-05-12T15:05:00Z"),
    manused: [
      { filename: "liis_referaat_kommentaarid.docx", size: 35000 }
    ]
  },
  {
    saatjaId: 4,
    saatjaTyyp: "opetaja",
    saajaTyyp: "grupp",
    saajaId: 4,         // viide MySQL grupid.id = 4 (11B)
    tekst: "11B grupp -- palun kõik tooge homme kaasa kalkulaator.",
    saadetudKell: new Date("2026-05-13T07:00:00Z"),
    loetud: false,      // grupisõnum -- lugemise staatus on umbkaudne
    manused: []
  },
  {
    saatjaId: 1,
    saatjaTyyp: "opilane",
    saajaTyyp: "opetaja",
    saajaId: 1,
    tekst: "Tere. Kas saan homme konsultatsioonile tulla kell 14:30?",
    saadetudKell: new Date("2026-05-13T10:00:00Z"),
    loetud: false,
    manused: []
  }
]);

// ============================================================
// Kollektsioon 3: vestlused
// Grupichat -- mitme inimese omavaheline kirjavahetus.
//
// Sonumid on embedded -- otse vestluse dokumendi sees.
// See tähendab ühe MongoDB päringu korraga saab kätte
// kogu vestluse koos kõigi sõnumitega.
// Kui sõnumid oleksid eraldi kogus, peaks tegema JOIN-i --
// aga MongoDB-s JOIN-e ei soovitata.
// ============================================================
db.vestlused.insertMany([
  {
    pealkiri: "Matemaatika abi grupp -- 10A",
    tyyp: "grupp",
    liikmed: [
      { id: 1, tyyp: "opilane" },
      { id: 2, tyyp: "opilane" },
      { id: 1, tyyp: "opetaja" }
    ],
    loodudKell: new Date("2026-05-01T10:00:00Z"),
    sonumid: [
      {
        saatjaId: 1, saatjaTyyp: "opilane",
        tekst: "Kas keegi sai ules 5b aru?",
        kell: new Date("2026-05-13T16:00:00Z"),
        reaktsioonid: [{ emoji: "+1", kasutajaId: 2 }]
      },
      {
        saatjaId: 2, saatjaTyyp: "opilane",
        tekst: "Jah. Kasuta valemit sin2+cos2=1 ja siis tuleb lihtne.",
        kell: new Date("2026-05-13T16:05:00Z"),
        reaktsioonid: []
      },
      {
        saatjaId: 1, saatjaTyyp: "opetaja",
        tekst: "Täpne vastus. Jaan, proovi uuesti -- Liis on oigel teel.",
        kell: new Date("2026-05-13T16:10:00Z"),
        reaktsioonid: []
      }
    ]
  },
  {
    pealkiri: "Programmeerimise projekt -- meeskond Alpha",
    tyyp: "projekt",
    liikmed: [
      { id: 1, tyyp: "opilane" },
      { id: 3, tyyp: "opilane" },
      { id: 7, tyyp: "opilane" }
    ],
    loodudKell: new Date("2026-05-05T12:00:00Z"),
    sonumid: [
      {
        saatjaId: 1, saatjaTyyp: "opilane",
        tekst: "Teen andmebaasi osa, Mart teeb API ja Tonu frontend?",
        kell: new Date("2026-05-13T18:00:00Z"),
        reaktsioonid: []
      },
      {
        saatjaId: 3, saatjaTyyp: "opilane",
        tekst: "Sobib. Mul on API pool juba pooleli.",
        kell: new Date("2026-05-13T18:15:00Z"),
        reaktsioonid: []
      }
    ]
  }
]);

// ============================================================
// Kollektsioon 4: kommentaarid
// Kommentaarid tunnile, teatele või kursusele.
//
// Vastused on samuti embedded -- iga kommentaar kannab
// oma vastused endas kaasas. See on MongoDB tüüpiline muster.
// Alternatiiv oleks eraldi "vastused" kogu -- aga siis peaks
// alati kaks päringut tegema.
// ============================================================
db.kommentaarid.insertMany([
  {
    sihtTyyp: "tund",
    sihtId: 6,          // viide MySQL tunnid.id = 6
    kasutajaId: 1,
    kasutajaTyyp: "opilane",
    tekst: "Kas rekursioon tuleb ka eksamile?",
    loodudKell: new Date("2026-05-13T14:00:00Z"),
    vastused: [
      {
        kasutajaId: 4, kasutajaTyyp: "opetaja",
        tekst: "Jah, aga ainult lihtsemad naited.",
        kell: new Date("2026-05-13T14:30:00Z")
      }
    ],
    meeldimised: 3
  },
  {
    sihtTyyp: "teade",
    sihtId: "kontrolltoo_fusika",
    kasutajaId: 3,
    kasutajaTyyp: "opilane",
    tekst: "Mitu ulesan kontrolltoos on?",
    loodudKell: new Date("2026-05-12T11:30:00Z"),
    vastused: [
      {
        kasutajaId: 2, kasutajaTyyp: "opetaja",
        tekst: "Viis ulesan, igauks 20 punkti.",
        kell: new Date("2026-05-12T12:00:00Z")
      }
    ],
    meeldimised: 1
  },
  {
    sihtTyyp: "kursus",
    sihtId: 4,          // viide MySQL kursused.id = 4
    kasutajaId: 4,
    kasutajaTyyp: "opilane",
    tekst: "Väga huvitav kursus. Eriti meeldis funktsioonide teema.",
    loodudKell: new Date("2026-05-10T20:00:00Z"),
    vastused: [],
    meeldimised: 5
  }
]);

// Indeksid -- ilma indeksiteta on suurem andmebaas aeglane.
// courseId + createdAt: sageli otsitakse "viimased teated kursusel X"
db.teated.createIndex({ courseId: 1, createdAt: -1 });
// target: otsitakse teate sihtmärgi järgi
db.teated.createIndex({ "target.type": 1, "target.id": 1 });
// sonumid: otsitakse "loetud/lugemata sonumid kasutajale X"
db.sonumid.createIndex({ saajaId: 1, saajaTyyp: 1, loetud: 1 });
db.sonumid.createIndex({ saatjaId: 1, saadetudKell: -1 });
// kommentaarid: otsitakse "kommentaarid tundi X kohta"
db.kommentaarid.createIndex({ sihtTyyp: 1, sihtId: 1 });
// vestlused: otsitakse "millistes vestlustes kasutaja X osaleb"
db.vestlused.createIndex({ "liikmed.id": 1 });

print("MongoDB seadistus valmis.");
print("Kollektsioonid: teated, sonumid, vestlused, kommentaarid");
