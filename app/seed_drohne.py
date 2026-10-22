"""Startdaten der UVV-Unterweisung Drohnenbetrieb.

Wird nur beim ersten Start in die Datenbank übernommen (Migration der bisherigen
Einzel-App). Danach werden Inhalte und Fragen in der Verwaltung gepflegt;
Änderungen an dieser Datei wirken sich dann nicht mehr aus.
"""

QUESTIONS = [
    {
        "id": "q01",
        "text": "Wie oft muss die UVV-Unterweisung zum Drohnenbetrieb mindestens stattfinden?",
        "options": {
            "a": "Vor der ersten Tätigkeit und danach mindestens einmal jährlich",
            "b": "Nur einmal bei der Ausbildung zum Fernpiloten",
            "c": "Alle fünf Jahre",
            "d": "Nur nach einem Unfall",
        },
        "correct": "a",
        "explain": "DGUV Vorschrift 1 (§ 4) und DGUV Vorschrift 49 verlangen die Unterweisung vor Aufnahme der Tätigkeit und danach mindestens jährlich.",
    },
    {
        "id": "q02",
        "text": "Wer erteilt im Einsatz den Flugauftrag für die Drohne?",
        "options": {
            "a": "Der Fernpilot entscheidet selbst",
            "b": "Die Einsatzleitung",
            "c": "Die Leitstelle",
            "d": "Jede Führungskraft an der Einsatzstelle",
        },
        "correct": "b",
        "explain": "Die Drohne ist ein Einsatzmittel – ohne Auftrag der Einsatzleitung wird nicht geflogen.",
    },
    {
        "id": "q03",
        "text": "Bis zu welcher Startmasse ist der Drohnenbetrieb durch die Feuerwehr nach § 21k LuftVO genehmigungsfrei?",
        "options": {
            "a": "Unter 250 g",
            "b": "Unter 2 kg",
            "c": "Unter 25 kg",
            "d": "Ohne Gewichtsgrenze",
        },
        "correct": "c",
        "explain": "§ 21k LuftVO: Drohnen unter 25 kg Startmasse benötigen beim Betrieb durch oder unter Aufsicht von BOS keine Betriebsgenehmigung.",
    },
    {
        "id": "q04",
        "text": "Ein Kamerad fliegt in seiner Freizeit mit seiner privaten Drohne über ein Wohngebiet. Gilt das BOS-Privileg?",
        "options": {
            "a": "Ja, als Feuerwehrangehöriger immer",
            "b": "Ja, wenn er seine Einsatzkleidung trägt",
            "c": "Nein, das Privileg gilt nur im dienstlichen Einsatz und bei dienstlichen Übungen",
            "d": "Ja, wenn die Drohne unter 25 kg wiegt",
        },
        "correct": "c",
        "explain": "Das Privileg ist an die dienstliche Aufgabe gebunden. Privat gelten die normalen EU-Regeln.",
    },
    {
        "id": "q05",
        "text": "Während des Flugs nähert sich ein Rettungshubschrauber. Was tust du?",
        "options": {
            "a": "Weiterfliegen, die Drohne ist für den Hubschrauber gut sichtbar",
            "b": "Sofort sinken, Abstand schaffen und landen",
            "c": "Höher steigen, um über dem Hubschrauber zu sein",
            "d": "Die Drohne in der Position halten",
        },
        "correct": "b",
        "explain": "Bemannte Luftfahrt hat immer Vorrang – auch für BOS-Drohnen.",
    },
    {
        "id": "q06",
        "text": "Was ist die Hauptaufgabe des Luftraumbeobachters?",
        "options": {
            "a": "Die Kamera bedienen und Fotos machen",
            "b": "Sichtkontakt halten, vor Luftfahrzeugen und Hindernissen warnen, Startplatz sichern",
            "c": "Die Akkus während des Flugs laden",
            "d": "Den Flugauftrag erteilen",
        },
        "correct": "b",
        "explain": "Der Luftraumbeobachter unterstützt den Fernpiloten und achtet auf Gefahren im Luftraum und am Boden.",
    },
    {
        "id": "q07",
        "text": "Darf die Drohne längere Zeit direkt über arbeitenden Einsatzkräften schweben?",
        "options": {
            "a": "Ja, das liefert die besten Bilder",
            "b": "Ja, wenn die Einsatzkräfte einen Helm tragen",
            "c": "Nein – Arbeitsbereiche seitlich anfliegen und Überflüge kurz halten",
            "d": "Ja, ab einer Höhe von 50 m",
        },
        "correct": "c",
        "explain": "Herabfallende Drohnen oder Teile können Einsatzkräfte schwer verletzen.",
    },
    {
        "id": "q08",
        "text": "Wie hoch muss die Return-to-Home-Höhe eingestellt sein?",
        "options": {
            "a": "Immer genau 30 m",
            "b": "Über dem höchsten Hindernis im Fluggebiet",
            "c": "So niedrig wie möglich, um Akku zu sparen",
            "d": "Das ist egal, die Drohne weicht automatisch aus",
        },
        "correct": "b",
        "explain": "Sonst kann die Drohne beim automatischen Rückflug z. B. mit Bäumen, Leitungen oder der Drehleiter kollidieren.",
    },
    {
        "id": "q09",
        "text": "Bei der Kontrolle vor dem Start stellst du fest, dass ein Akku leicht aufgebläht ist. Was tust du?",
        "options": {
            "a": "Trotzdem verwenden, wenn er voll geladen ist",
            "b": "Nur noch für kurze Flüge verwenden",
            "c": "Sofort aussortieren und nicht mehr verwenden",
            "d": "Kräftig zusammendrücken und dann verwenden",
        },
        "correct": "c",
        "explain": "Aufgeblähte oder beschädigte LiPo-Akkus können in Brand geraten und werden sofort aussortiert.",
    },
    {
        "id": "q10",
        "text": "Ein LiPo-Akku fängt Feuer. Was ist richtig?",
        "options": {
            "a": "Abstand halten, Rauch nicht einatmen, mit viel Wasser kühlen, danach im Wasser- oder Sandbehälter beobachten",
            "b": "Mit einem kleinen Glas Wasser ablöschen und weiterverwenden",
            "c": "Den Akku mit der Hand vom Gerät abziehen",
            "d": "Abwarten, bis er von selbst ausgeht, und ihn in den Hausmüll werfen",
        },
        "correct": "a",
        "explain": "LiPo-Brände können sich wieder entzünden – deshalb großzügig kühlen und danach beobachten.",
    },
    {
        "id": "q11",
        "text": "Welche besondere Gefahr besteht beim Flug über einer Brandstelle?",
        "options": {
            "a": "Keine, die Drohne ist hitzefest",
            "b": "Thermik, Aufwind und Hitze können die Drohne unkontrollierbar machen",
            "c": "Nur die Kamera kann beschlagen",
            "d": "Die Drohne wird automatisch langsamer",
        },
        "correct": "b",
        "explain": "Heiße Gase und Aufwinde über dem Brand beeinflussen die Flugstabilität und können Bauteile schädigen.",
    },
    {
        "id": "q12",
        "text": "Was kann die Funk- oder GPS-Verbindung der Drohne stören?",
        "options": {
            "a": "Stahlkonstruktionen, Hochspannungsleitungen und Abschattung durch Gebäude",
            "b": "Nur starker Regen",
            "c": "Das Blaulicht der Fahrzeuge",
            "d": "Nichts, die Verbindung ist störungsfrei",
        },
        "correct": "a",
        "explain": "Metall, elektromagnetische Felder und Abschattung können zu Kontrollverlust führen.",
    },
    {
        "id": "q13",
        "text": "Während des Flugs bricht die Verbindung zur Drohne ab. Was tust du?",
        "options": {
            "a": "Den Landeplatz verlassen und die Drohne suchen gehen",
            "b": "Return-to-Home abwarten und den Landeplatz freihalten",
            "c": "Die Fernsteuerung neu starten und dabei laufen",
            "d": "Einen zweiten Akku in die Fernsteuerung stecken",
        },
        "correct": "b",
        "explain": "Die meisten Drohnen fliegen bei Verbindungsverlust automatisch zum Startpunkt zurück – der Landeplatz muss frei sein.",
    },
    {
        "id": "q14",
        "text": "Du hast Drohnenaufnahmen von einem Einsatz gemacht. Darfst du sie in sozialen Medien teilen?",
        "options": {
            "a": "Ja, Einsatzbilder sind öffentlich",
            "b": "Ja, wenn keine Kennzeichen zu sehen sind",
            "c": "Nein – Aufnahmen sind einsatzbezogen und werden nur nach Freigabe weitergegeben",
            "d": "Ja, nach 24 Stunden",
        },
        "correct": "c",
        "explain": "Drohnenbilder zeigen oft Personen und Grundstücke. Datenschutz und Persönlichkeitsrechte sind zu wahren.",
    },
]

# Inhalte der Unterweisung (erscheinen auf der Startseite und im PDF)
CONTENT = [
    ("Rechtsrahmen", [
        "Pflicht zur Unterweisung: DGUV Vorschrift 1 (§ 4) und DGUV Vorschrift 49 – vor der ersten Tätigkeit und mindestens jährlich.",
        "§ 21k LuftVO: Drohnen unter 25 kg sind im Einsatz und bei dienstlichen Übungen genehmigungsfrei; die geografischen Beschränkungen (§§ 21h, 21i) gelten nicht.",
        "Trotzdem: Bemannte Luftfahrt hat immer Vorrang. Das Privileg gilt nur im Dienst, nicht privat.",
    ]),
    ("Rollen", [
        "Einsatzleitung erteilt den Flugauftrag – kein Flug ohne Auftrag.",
        "Fernpilot: nur ausgebildete und benannte Kräfte; verantwortlich für Gerät, Flug und Abbruch.",
        "Luftraumbeobachter: hält Sichtkontakt, warnt vor Hubschraubern und Hindernissen, sichert den Startplatz.",
        "Drohneneinsatz der Leitstelle melden (nach örtlicher Regelung).",
    ]),
    ("Gefährdungen", [
        "Rotoren (Schnittverletzungen), Absturz und herabfallende Teile.",
        "LiPo-Akkus: Brand bei Beschädigung, Über- oder Tiefentladung.",
        "Wetter, Thermik und Hitze über Brandstellen.",
        "Funk- und GPS-Störungen durch Stahl, Hochspannung und Abschattung.",
        "Luftverkehr: Rettungs- und Polizeihubschrauber, Löschflugzeuge.",
    ]),
    ("Vor dem Start", [
        "Sichtprüfung von Rahmen, Propellern und Kamera; Firmware und Kompass in Ordnung.",
        "Akkus geladen, unbeschädigt, warm genug.",
        "Wind und Wetter innerhalb der Herstellergrenzen.",
        "Start-/Landeplatz frei und abgesperrt, Hindernisse erkannt.",
        "Return-to-Home-Höhe über dem höchsten Hindernis.",
        "Absprache mit Einsatzleitung und Luftraumbeobachter.",
    ]),
    ("Im Flug", [
        "Sichtverbindung halten.",
        "Nicht über Einsatzkräften schweben – seitlich anfliegen.",
        "Hubschrauber in Sicht: sofort sinken, Abstand schaffen, landen.",
        "Akku-Reserve einplanen und Rückflug rechtzeitig einleiten.",
    ]),
    ("Akkus", [
        "Laden nur unter Aufsicht, auf nicht brennbarer Unterlage oder in LiPo-Tasche.",
        "Beschädigte oder aufgeblähte Akkus sofort aussortieren.",
        "Lagern mit Lagerspannung, kühl und trocken; Transport im geeigneten Behälter.",
        "Brand: Abstand halten, Rauch nicht einatmen, mit viel Wasser kühlen, danach beobachten.",
    ]),
    ("Störungen und Notfall", [
        "Verbindungsverlust: Return-to-Home abwarten, Landeplatz freihalten.",
        "Absturz: Absturzstelle sichern, Akku auf Brand prüfen.",
        "Einsatzleitung sofort informieren.",
        "Dokumentieren: Flugbuch, Schaden, bei Verletzten Unfallmeldung.",
    ]),
    ("Bilder und Datenschutz", [
        "Nur einsatzbezogen aufnehmen.",
        "Keine Weitergabe oder Veröffentlichung ohne Freigabe.",
        "Sicher speichern und nach Regelung der Wehr löschen.",
    ]),
]

TRAINING = {
    "slug": "drohne",
    "title": "UVV-Unterweisung Drohnenbetrieb (UAS)",
    "short_name": "Drohnenbetrieb",
    "headline": "Sicherer Umgang mit Drohnen",
    "description": "Sicherer Umgang mit Drohnen (UAS) im Einsatz- und Übungsdienst",
    "subtitle": "Drohnenbetrieb (UAS) · gemäß DGUV Vorschrift 1 und DGUV Vorschrift 49",
    "legal": "DGUV Vorschrift 1 (§ 4), DGUV Vorschrift 49 „Feuerwehren“, "
             "DGUV Information 208-058 „Sicherer Umgang mit Multikoptern (Drohnen)“, § 21k LuftVO, "
             "DFV/AGBF-Fachempfehlung „Drohnen und UAV in den Feuerwehren“.",
    "content": CONTENT,
    "questions": QUESTIONS,
}
