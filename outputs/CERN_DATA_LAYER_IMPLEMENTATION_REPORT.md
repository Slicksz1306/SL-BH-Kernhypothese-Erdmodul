# CERN-Datenebene — Implementierungsbericht P05–P07

Arbeitsdatum: 18. Oktober 2026. Quellenstichtag: 7. Oktober 2026.
**Gesamtstatus: PARTIAL.** Der autorisierte Softwareumfang P05–P07 ist umgesetzt,
die Abschlussprüfungen sind durchgeführt und der vorhandene Datenbestand ist
unveränderlich als **FROZEN_PARTIAL** gesichert. Vollständige CERN-Evidenz bleibt
wegen nicht verfügbarer HEPData-/Verlagsdaten und fehlender wissenschaftlicher
Abnahme offen. Keine P08–P10-Freigabe; keine neue A35-/QE-Rechnung.

Abschlussbelege im selben Ausgabeordner: `CERN_TEST_RESULTS.json`,
`CERN_TEST_full_212.log`, `CERN_TEST_prior_full_baseline_210.log`,
`CERN_FINAL_VERIFICATION.json`, `CERN_INDEPENDENT_REVIEW.md`,
`CERN_FINAL_CODE_RECHECK.md`, `CERN_GITHUB_SYNC_PREPARATION.md` und
`HEPDATA_RETRIEVAL_DIAGNOSIS.md`. `CERN_CODE_MANIFEST.json` hält zusätzlich die
SHA-256 der gelieferten Code-, Schema-, Dokumentations- und Reproduktionsdateien
fest. Reproduktionsanweisungen in Abschnitt 8.

## 1. Dateien

Die abgenommene Foundation bleibt unverändert. Neue Module liegen ausschließlich
unter `a35_cern_layer/sl_constraints/collider`, neue Schemata unter `schemas`,
neue Tests unter `tests`. Hinzu kommen `COLLIDER_README.md`, ein eigenständiger
Dependency-Lock/Audit und `data/cern_lhc_snapshot_2026_10_07`.
Alle 24 Dateien der gesicherten P01–P04-Baseline sind abschließend bytegleich.
Die vier referenzierten Forschungsartefakte einschließlich A35-Charge-Spec,
Closure-Architektur, Inventar und Acquisition-Jobs haben unveränderte SHA-256.
Die konkreten Hashes stehen in `CERN_FINAL_VERIFICATION.json`.

Im Abschluss-Patch verändert: `contracts.py`, `extraction.py`, `normalize.py`,
`sources.py` sowie das synthetische Binding in `tests/test_normalize.py`.
Neu: HTTP-Receipt-Regressionen, `tests/test_collider_review.py`, die unabhängige
Sollmatrix `coverage.py`, Diagnose-/Review-/Testberichte. Arbeitshelfer für den
eng begrenzten Freeze und die Offline-Abschlussprüfung liegen unter `work/`.
Originaldaten, bisherige Kataloge und Coverage wurden nicht überschrieben;
`COVERAGE_REVIEWED.json` ergänzt die ursprüngliche `COVERAGE.json`.

## 2. Schema

Explizite Typen: SourceRecord, DatasetRecord, BenchmarkDefinition, ConstraintRecord,
ObservableDefinition und SnapshotManifest. Pflichtfelder dürfen nicht fehlen;
unbekannte Werte bleiben null. Geschlossene Objekte weisen unbekannte Felder ab.
Zahlen sind exakte Dezimalzeichenfolgen, CL liegt strikt zwischen 0 und 1.
Observable und Einheit werden zusätzlich semantisch geprüft. MASS_THRESHOLD,
SIGMA, SIGMA_TIMES_BR, SIGMA_TIMES_ACCEPTANCE, SPHALERON_FRACTION, EVENT_FRACTION,
DIMENSIONLESS_PARAMETER, OTHER und EXCLUSION_CONTOUR bleiben unterscheidbar.
Konturen werden nicht in Skalarwerte umgedeutet.

Vergleichsidentität berücksichtigt Modell/Dimensionen/Annahmen, Parameter,
Observable, Datensatz, Energie, Selektion/Kanal und statistische Definition.
Unvollständige Semantik erhält keine gültige Gruppe. Fremde Gruppenhashes werden
erneut gegen den Inhalt geprüft. Es ist kein numerischer Vergleich implementiert.

Die Standardbibliothek enthält keine vollständige JSON-Schema-Engine. Deshalb
wurde statt eines selbstgebauten Interpreters `jsonschema==4.26.0` lokal isoliert
verwendet. Transitive Pins: attrs 25.4.0, jsonschema-specifications 2025.9.1,
referencing 0.37.0, rpds-py 0.30.0 und typing-extensions 4.15.0. Die fünf ersten
Pakete nennen MIT, typing-extensions PSF-2.0. Keine optionalen Format-Extras.
Die sechs Wheel-SHA-256 stehen im Lock; Paketmetadaten, URLs und Abhängigkeiten
im Audit. Foundation-Metadaten und globale Python-Installation wurden nicht geändert.

## 3. Quellen

Originalbytes wurden am 18.10.2026 mit tatsächlicher UTC-Abrufzeit gesichert.
Sechs inhaltlich zugeordnete Quellen: zwei Versionshistorien, zwei v2-Paper,
zwei offizielle Ergebnisübersichten. Die Paper sind über separate arXiv-
Versionshistorien auf den Stichtag zurückführbar; die heutigen dynamischen Seiten
selbst gelten nicht als historisch eingefrorene Fassungen vom 7. Oktober.

| Analyse | Aktuelle arXiv-Fassung beim Abruf | Original-HTML-SHA-256 |
|---|---|---|
| ATLAS EXOT-2024-32 | v2, 24.09.2026 | `6871595fe1a737fb5cdcc57f322626d870b24a7afc3060feb3ec4a9186c10444` |
| CMS EXO-24-028 | v2, 26.08.2026 | `7fadcfce5fce60055ccd817d98d05c9d09e4c759f1691022a0d3f4f7cf2be955` |

Primärbelege: [ATLAS v2](https://arxiv.org/html/2604.19495v2),
[ATLAS Versionshistorie](https://arxiv.org/abs/2604.19495),
[CMS v2](https://arxiv.org/html/2604.10732v2),
[CMS Versionshistorie](https://arxiv.org/abs/2604.10732).
Verlagsabgleich ist **nicht abgeschlossen**: ATLAS-Redirect außerhalb der
Hostliste; CMS liefert eine JavaScript-Challenge statt des Papers. Der Challenge-
Body ist als abgewiesene Roh-Evidenz erhalten, nicht als akzeptierte Publikation.

## 4. ATLAS

Die vollständige kleine Tabelle 2 wurde aus dem gehashten HTML extrahiert und
gegen ihre Modell-, Dimensions-, Kanal- und Expected/Observed-Header geprüft.
Keine Kanalzusammenführung. Kontext: 13,6 TeV, 164 fb^-1, 2022–2024, 95 % CL.

| Modell | n | Kanal | Beobachtet / erwartet, TeV |
|---|---:|---|---|
| RS | 1 | e+j | 7,2 / 7,1 |
| RS | 1 | mu+j | 6,6 / 6,6 |
| ADD | 2 | e+j | 8,6 / 8,5 |
| ADD | 2 | mu+j | 8,2 / 8,1 |
| ADD | 4 | e+j | 9,1 / 9,1 |
| ADD | 4 | mu+j | 8,7 / 8,7 |
| ADD | 6 | e+j | 9,4 / 9,4 |
| ADD | 6 | mu+j | 9,0 / 9,0 |

Generator/PDF, J=0, Schwellenrelation Mth=MD, Erzeugungsmassenintervall und
flavourabhängige BR sind getrennt dokumentiert. Nicht belegte Annahmen werden
nicht aus Generatornamen abgeleitet. Daher sind die acht numerisch vollständigen
Zeilen noch keine vollständig abgenommene oder universell vergleichbare Evidenz.

## 5. CMS

13 TeV, 138 fb^-1, 2016–2018, 95 % CL; nichtasymptotisches CLs laut Paper.
Keine globale Zahl „CMS BH=11,4 TeV“ im Datenmodell.

| Familie | Deklarierte Plätze | Tatsächlich vorhandene numerische Angaben |
|---|---:|---|
| B1–B3/C1–C6 | 216 = 9 Modelle × 3 n × 8 MD | B1,n2: 11,0 TeV bei MD2; 10,4 TeV bei MD4; expected jeweils null |
| String Balls | 21 = 7 MS × 3 gs | Grenzwerte null; keine Werte aus Plots geschätzt |
| Sphaleron-Vorfaktor | 15 = 5 Esph × 3 p(NCS=+1) | E9,p0,5: 0,0034 beobachtet, 0,0035 erwartet |
| Abstract-Anteilsaussage | 1 | 0,0034 beobachtet; Definition/Zuordnung offen, expected null |
| Modellunabhängiges sigma*A, N>=4 | 1 | Kurvenwerte null |

Die 254 CMS-Einträge sind Benchmark-/Observable-Kontexte einschließlich offener
Rasterplätze, **nicht 254 veröffentlichte Zahlenwerte**. Maßgeblich sind `null`,
`missing_fields` und `validation_status`. Alle Generatorvarianten bleiben separat.
Abstract-Anteil und dimensionsloser Vorfaktor werden nicht gleichgesetzt.
Zusätzlich besteht ein Widerspruch im Text zu C2: Abschnitt 3 definiert nichtrotierend,
Abschnitt 9 nennt C2 in einer rotierenden Gruppe. Die Modell-Definition wird
beibehalten und die Unstimmigkeit als offene Quellenfrage dokumentiert.

## 6. HEPData

ATLAS-Link ins3147718 aus offizieller Übersicht; CMS-Link ins3144373 aus offizieller
Übersicht, DOI 10.17182/hepdata.165871 aus Paper. Linkkennungen sind keine unabhängig
bestätigten Record-/Tabellenversionen. Die JSON-/DOI-Abrufe scheiterten; kein
HEPData-Dataset wird als erfolgreich ingestiert ausgegeben. Recordversion,
Tabellen-IDs, Units-/Struktur-/Benchmarkprüfung bleiben unbestätigt. Der
Paper/HEPData-Crosscheck lautet `SOURCE_MISSING`, nicht MATCH.

Die alten Fehlversuche protokollierten nur `HTTPError`; ihre tatsächliche Ursache
ist rückwirkend nicht eindeutig feststellbar. Je ein kontrollierter Wiederholungs-
GET am 18.10.2026 um 19:43 UTC auf
`https://www.hepdata.net/record/ins3147718?format=json` und
`https://www.hepdata.net/record/165871?format=json` lieferte **HTTP 403 Forbidden**,
Server `cloudflare`, HTML-Prüfseite „Just a moment...“ statt JSON.
Das ist für die Wiederholung eine belegte vorgeschaltete Zugriffssperre, kein
nachgewiesener Timeout, HTTP 429 oder 5xx. Konkrete Cloudflare-Regel und dahinter
liegende Record-Verfügbarkeit bleiben unbekannt. Kein Umgehungsversuch.
Antwortbytes, Zeit, Status, ausgewählte Header und Hashes sind dauerhaft erhalten.
Vollständige Einzelbefunde und Hashes: `HEPDATA_RETRIEVAL_DIAGNOSIS.md`.

Zusätzlich wurde die reguläre, im offiziellen HEPData-Projekt dokumentierte
Originalarchiv-Route geprüft: je ein schreibfreier HEAD auf
`/download/submission/ins3147718/original` und
`/download/submission/ins3144373/original`. Beide antworteten ebenfalls
HTTP 403, `text/html`, Server `cloudflare`. Die offizielle HEPData-CLI dokumentiert
die regulären Formate/Download-Befehle; ihre Existenz belegt keine Verfügbarkeit
dieser beiden Einträge. [HEPData-CLI](https://github.com/HEPData/hepdata-cli),
[HEPData-Records-API](https://hepdata.readthedocs.io/en/latest/modules/records.html).
Die gezielte öffentliche Suche nach den beiden Analysen fand keinen alternativen
exportierten Eintrag. Das ist kein Beleg, dass HEPData die Records nicht besitzt.

Die lokale offizielle CMS-Ergebnisseite (im Snapshot gespeichert und gehasht)
listet für die untersuchten Figuren keine aktiven CSV-Hyperlinks; die scheinbaren
CSV-Verweise sind HTML-Kommentare. Für die Abbildungen gibt es Bild/PDF-Ressourcen,
aber sie wurden nicht digitalisiert oder als Datentabellen interpretiert. Es
wurde daher kein alternativer offizieller Zahlenexport ingestiert.

Offline geprüft sind korrekte Tabellenstruktur, fehlende Tabelle, Versionswechsel,
falsche Einheit, fehlende/falsche Qualifier, leere Arrays, doppelte JSON-Schlüssel,
Zensierung und Hashmanipulation. Crosschecks unterscheiden MATCH, ROUNDING_MATCH,
MISMATCH, NOT_COMPARABLE und SOURCE_MISSING. Rundung benötigt explizite Stellenzahl
und Quellenbegründung, keine pauschale numerische Toleranz.

## 7. Snapshot

Eingefrorener Name: `cern_lhc_snapshot_2026_10_07`. Die Zusammenstellung hat 262
Einträge, zwölf observed-Skalare und neun observed/expected-Paare. Tatsächlicher
Erfassungsstatus ist **FROZEN_PARTIAL**, nicht FROZEN_COMPLETE.
Vor dem exklusiven Freeze wurden Quellenhashes, Extraktionseltern und normalisierte
Artefakte revalidiert. Danach wurden alle **332 referenzierten Artefakte** erneut
gegen das Manifest geprüft: PASS. Sechs Quellen, neun Raw-Objekte, sieben
Unavailable-Receipts. 551 Gap-Einträge sind überlappende Scope-, Record-, Quellen-
und Review-Markierungen, **nicht 551 unabhängige Fehler**.

Manifestdatei: `a35_cern_layer/data/cern_lhc_snapshot_2026_10_07/snapshots/cern_lhc_snapshot_2026_10_07.json`.

- SHA-256 der ganzen Manifestdatei einschließlich Envelope:
  `bbc4b1580a3556fc2c4e7adce7c3429127bbe86d7e05f5d118032f221d8b0190`
- SHA-256 des kanonischen Manifestinhalts im Envelope:
  `b52746f773304a67b649d5f47db3fc04eaa92aa286f797175a331e9f322ae710`

Die Namen-/Byte-Unveränderlichkeit und konkurrierende Veröffentlichung sind
mit realen temporären Dateien getestet. Die alten Rohdaten und numerischen
Kataloge wurden beim Abschluss nur gelesen, nicht neu erzeugt.

## 8. Tests und Checks

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Abschließende vollständige Suite nach Relationship-Fix | **212 / 212 PASS**, keine Fehler/Errors/Skips |
| Gespeicherte 210er-Baseline, als exakte Test-ID-Menge erneut ausgeführt | **210 / 210 PASS** |
| Vorherige 185er- und 140er-Teilmenge | Bestandteil der bestandenen 210er-Baseline; separate erfolgreiche Läufe aus dem vorherigen Abschlussstand bleiben protokolliert |
| Unabhängiger Review vor Korrekturen | 41 schreibfreie Tests PASS; sechs wichtige und zwei kleinere Codebefunde |
| Frische gezielte Nachprüfung | sieben behobene Reviewbefunde PASS; zusätzliche Source-Relationship-Lücke gefunden und mit Regression geschlossen |
| Syntaxprüfung | 36 Python-Dateien geparst und im Speicher kompiliert: PASS |
| Schemaexport / Draft-2020-12-Prüfung | alle sechs Collider-Schemata PASS |
| Foundation-/Forschungsreferenzen | 24 bytegleiche Dateien; vier unveränderte Referenzhashes: PASS |
| Freeze-Readback | alle 332 Manifestartefakte: PASS |
| No-index-Whitespace-Diff | PASS, keine Diagnose; Exit 1 wegen vorhandener Unterschiede |

Entwicklung der Testanzahl: 140 Foundation → 158 Schemas → 173 Normalisierung →
185 Source/Freeze → 186 exakter Absatzadapter → 190 Paper-Reproduktion →
193 HTTP-Diagnose → 210 Review-Regressionen → 212 nach Source-Relationship-Fix.
Die gespeicherte 210er-Baseline wird anhand ihrer vollständigen IDs aus der vorherigen
Quittung gebildet und vollständig erneut ausgeführt.
Zwei ergänzende positive/negative Freeze-Gegenproben sichern bereits korrektes
Verhalten; für sie wird kein vorheriger Fehler behauptet.

Unabhängiges Review: ursprüngliches Urteil **Änderungen erforderlich**. Sieben
als wichtig behandelte Befunde wurden in einer Korrekturrunde behoben; ein
kleinerer Scan-Gruppenbefund bleibt OPEN. Die Tests der Korrektur führte der
Implementierer aus. Eine frische read-only Nachprüfung fand zusätzlich fehlende
Validierung allgemeiner `source_relationships`; der Fix besteht drei gezielte
Regressionen. Eine unabhängige Freigabe nach diesem letzten Fix erfolgte nicht.
Einzelbefunde: `CERN_INDEPENDENT_REVIEW.md`; Nachprüfung:
`CERN_FINAL_CODE_RECHECK.md`.

Der No-index-Whitespace-Diff prüft gegen die gesicherte Baseline. Original-Raw-
Bytes sind explizit binär/ohne EOL-Normalisierung gekennzeichnet; ihre Integrität
wird durch Hashes geprüft. Windows-CRLF wird als Zeilenende anerkannt. Exit 1
bedeutet beim No-index-Diff Unterschiede, nicht automatisch Whitespacefehler;
maßgeblich sind fehlende Whitespace-Diagnosen.

Kein konfigurierter Linter, Typecheck oder Wheel-Build: `pyproject.toml` legt
ausdrücklich Source-tree-Ausführung ohne Build-Backend/CLI fest. Diese Checks
wurden nicht als bestanden ausgegeben; die Syntaxprüfung ersetzt keinen Typecheck.

### Reproduktion ohne Netzabrufe

Im Workspace `C:\Users\xfire\Documents\Codex\2026-10-07\files-pasted-by-the-user-sl`:

```powershell
$env:PYTHONPATH = (Resolve-Path 'work/schema-prefix/Lib/site-packages').Path
python -B work/run_collider_final_tests.py
python -B work/verify_collider_delivery.py
```

Dies erzeugt nur abgeleitete Test-/Prüfberichte und synthetische Testdateien.
Das vorhandene wissenschaftliche Snapshot-Manifest wird gelesen, nicht überschrieben.
Der Quellen-Lock, Wheel-Hashes und isolierte Installationspfad sind in
`a35_cern_layer/COLLIDER_README.md` beschrieben. Kein erneuter Live-Abruf nötig.

## 9. Abweichungen und Entscheidungen

1. Kein Git-Init/Commit/Worktree: Das Paket ist projektlos. Diff gegen die gesicherte
   Baseline mit `git diff --no-index --check`; Risiko: keine Commit-Historie dieser Lieferung.
2. Narrow Snapshot-Freeze jetzt, ausdrücklich vom aktuellen Auftrag autorisiert;
   keine allgemeine P10-CLI. Risiko: keine vollständige spätere Systemintegration.
3. P01–P04 bleiben unverändert; Collider-spezifische Wire-Typen ergänzen sie.
   Historischer Quellenstichtag wird getrennt vom Abrufdatum geprüft. Risiko:
   historische Beweisführung benötigt weiterhin Quellenreview.
4. JSON-Schema-Bibliothek statt partieller Eigenentwicklung; sechs lokale Pins.
   Risiko: zusätzliche, explizit isolierte Abhängigkeiten und Plattformbindung des Wheel-Locks.
5. Enger HTML-Adapter für tatsächlich vorhandene Texte statt generischem PDF-/CSV-
   Parser. HEPData nur im geprüften JSON-Format. Risiko: andere Formate bleiben abgewiesen.
6. Nur belegte Skalarwerte; fehlende Kurven bleiben null und Scope-Lücken.
   Risiko: keine Vollständigkeits- oder Forschungsanwendbarkeitsbehauptung möglich.

## 10. Fehlende Daten

- Beide HEPData-Datensätze einschließlich Tabellenversionen, Kurven und Crosschecks.
- Vollständiger Abgleich mit den beiden Verlagsfassungen.
- ATLAS sigma*BR-Kurven und erwartete Bänder.
- CMS vollständige BH-/String-Ball-/Sphaleron-Kurven und erwartete Werte/Bänder.
- CMS alternative nmax-Tabelle: gruppierte Bereiche/Zensierung noch nicht als
  eindeutige Kontur normalisiert; Originalbytes vorhanden.
- Weitere Modellunabhängigkeits-Multiplizitäten aus Abbildungen nicht ausgelesen.
- Vollständige Generatorcards und nicht explizit belegte physikalische Annahmen.
- Auflösung der CMS-Vorfaktor/Anteil- und C2-Textwidersprüche.

## 11. Bekannte Risiken

Ein Bytehash beweist Identität, nicht physikalische Richtigkeit. Die numerischen
CMS-Textpunkte benutzen eine offengelegte, hashgebundene Zuordnung und genaue
Absatzlokatoren, keine semantikfreie Universalextraktion. Menschliches Review
steht aus. Neue HTML-Bytes brauchen eine neue geprüfte Adapterrevision.
Schreibschutz ist auf Anwendungsebene; keine Garantie gegen privilegierte lokale
Manipulation. Ein Abbruch vor dem Manifest kann verwaiste inhaltsadressierte
Artefakte hinterlassen, überschreibt aber keine veröffentlichte Identität.

Pip hinterließ bei der lokalen Installation aufgrund Windows-ACL-Problemen
temporäre Arbeitsordner. Sie wurden nicht per Rechteänderung oder breitem
Löschbefehl entfernt. Es wurde keine Systemkonfiguration geändert.

## 12. Empfehlung für P08

Zuerst P05–P07 als **partielle Evidenzlieferung** prüfen. P08 kann nur nach neuer
Freigabe beginnen und müsste mit nicht definiertem Mapping sowie Ablehnungsfällen
starten. Diese Lieferung behauptet weder eine SL-Ausschließung noch eine Erlaubnis,
Übereinstimmung oder Widerlegung. `sigma_SL_project = UNDEFINED`.

## 13. Wissenschaftliche Aussagegrenzen und Abschluss-Gates

| Ebene / Gate | Bewertung | Reichweite |
|---|---|---|
| Softwaretests / exakte numerische Verarbeitung | PASS | Getestete Verträge, Einheiten, Fehlerfälle und Quellreproduktion; keine Vollständigkeitsgarantie für alle möglichen Inputs |
| Mathematische Modellkonsistenz | OPEN | Geprüfte Foundation-Invarianten sind keine Gesamtprüfung der SL/BH-Theorie |
| Physikalische Closure | OPEN | **F1–F12-Entstehungs- und Transportprobleme sowie A35-Ladungsclosure bleiben offen**; keine neue Solverrechnung |
| Lokale Datenkonsistenz / Provenienz | PASS | Versionierte Originalbytes, Hashketten, beobachtet/erwartet getrennt |
| Erfolgreiche HEPData-Wiederholungsabrufe | FAIL | Beide HTTP 403 statt JSON |
| Vollständige experimentelle Constraint-Ebene | OPEN | Tabellen, Kurven, Annahmen und fachliche Abnahme fehlen; keine gültigen Vergleichsgruppen |
| Unveränderlicher partieller Freeze | PASS | FROZEN_PARTIAL; niemals vollständige wissenschaftliche Abnahme |
| Unabhängige Codebefundaufnahme | PASS | Erste Prüfung fand wichtige Befunde; frische Nachprüfung bestätigte gezielt die Fixes und fand noch einen Beziehungsfall |
| Regressionen der Review-Fixes | PASS | Vollsuite 212; zwei Relationship-Tests decken ungültige und gültige Referenzfälle ab |
| Erneute unabhängige Freigabe | OPEN | Nicht erfolgt; transparenter Review-/Fix-Nachweis vorhanden |
| GitHub-Synchronisation | OPEN | Ziel und lokaler Zustand dokumentiert; Lieferordner kein Git-Checkout, keine GitHub-Änderung ausgeführt |
| Experimenteller Nachweis / Widerlegung der SL/BH-Hypothese | OPEN | Aus dieser Lieferung nicht ableitbar |
| Autorisierter Umfang | PASS | Ende bei P07; P08–P10 nicht begonnen/erweitert |

Bestandene Tests belegen insbesondere **keinen Nachweis mikroskopischer Schwarzer
Löcher**. Veröffentlichte Ausschlussgrenzen gelten nur für die jeweiligen
Benchmarkannahmen. Die begrenzte Datenreproduktion liefert weder SL-Closure noch
einen SL-Querschnitt, und sie überträgt keine LHC-Grenze auf das Erd-/SL-Modell.

### Verbleibender Softwarebefund

**Minor Nr. 7 / OPEN:** Scan-Koordinaten fließen derzeit in die Vergleichsgruppe
ein. Das kann künftig eine Scanreihe zu stark aufteilen. Im eingefrorenen Bestand
sind alle Gruppen null; damit entsteht hier keine falsche Vergleichsfreigabe.
Die Trennung von Scanachsdefinition und Punktkoordinate ist vor späterer
Vergleichsnutzung zu korrigieren. Mehrpunkttabellen werden bis dahin ausdrücklich
abgewiesen und nicht stillschweigend unter falschen Koordinaten normalisiert.

### Nächste Forschungsphase – Empfehlungen, keine Durchführung

1. Offizielle HEPData-JSON-/Tabellenexporte regulär beschaffen, Identität/Version
   und Einheiten bestätigen, Paper-Crosschecks durchführen; keine Cloudflare-Umgehung.
2. Verlagsfassungen, CMS-C2-Widerspruch und Anteil/Vorfaktor-Definition fachlich
   klären; fehlende Generatorannahmen nicht ergänzen, bevor Originalbelege vorliegen.
3. Die als wichtig behandelten Codefixes und den Partial-Freeze bei der nächsten
   Freigabe fachlich/code-seitig abnehmen; Minor Nr. 7 vor Vergleichsnutzung beheben.
4. F1–F12 und A35-Ladungsclosure als eigenen offenen Forschungsstrang behandeln.
5. Erst nach ausdrücklicher neuer Freigabe P08-Anwendbarkeit planen; P09-Recast,
   allgemeine P10-CLI, neue Simulationen oder ML sind nicht aus diesem Bericht autorisiert.

**Gesamturteil PARTIAL:** Der erreichbare autorisierte Abschluss ist reproduzierbar
gesichert. Ein vollständiger Evidenzabschluss wird durch externe Quellenlücken
und ausstehende wissenschaftliche Abnahme verhindert. BLOCKED wäre für den
gesamten Auftrag unzutreffend, da Tests, Diagnose, Korrekturen, Review-Dokumentation
und partieller Freeze tatsächlich abgeschlossen sind. COMPLETED würde die
verbleibenden Evidenz- und Forschungsgrenzen verschleiern.
