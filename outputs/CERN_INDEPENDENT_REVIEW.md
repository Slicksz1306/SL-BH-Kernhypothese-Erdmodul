# Unabhängige Codeprüfung und Behandlung der Befunde

Datum: 18.10.2026. Prüfer: separater Review-Agent Carson,
ID `01a14e8d-be1a-7291-a28d-f5b8e91f25cb`. Umfang: gesamte Ergänzung P05–P07,
einschließlich der neuen HTTP-Diagnosebelege. Read-only; keine Netzabrufe,
Quelldateiänderungen oder Snapshot-Veröffentlichung durch den Prüfer.

## Tatsächliches Review-Ergebnis

**Änderungen erforderlich; keine Freigabe vor Korrektur.** Sechs wichtige
und zwei kleinere Befunde. Kein im geprüften Umfang nachgewiesener kritischer
Fehler mit Codeausführung, Pfadausbruch oder Datenabfluss. Dies ist keine
umfassende Sicherheitszertifizierung.

Der Prüfer führte 41 schreibfreie Tests erfolgreich aus und eigene Gegenproben
im Speicher durch. Er bestätigte: 24 Foundation-Dateien bytegleich, sechs
Schema-Exporte konsistent, sechs Quellen, 26 Extraktionen, 262 Records mit
korrekter lokaler Hash-/Elternkette. Reproduktion der acht ATLAS- und 254 CMS-
Records identisch; zwölf observed-Werte und neun Paare, alle Vergleichsgruppen
null. Die beiden neuen HTTP-403-Belege und ihre Originalbodys waren hashkonsistent.
Das finale Snapshot-Manifest existierte zum Prüfzeitpunkt noch nicht.

## Eine Korrekturrunde mit Regressionen

| Nr. | Befund des unabhängigen Reviews | Behandlung / Nachweis |
|---|---|---|
| 1, P1 | FROZEN_COMPLETE trotz PARTIAL-Coverage/fehlender Quelle; stale missing_fields; Soll aus Ist abgeleitet | Freeze revalidiert Coverage, wissenschaftliche Annahmen/Status/Purpose und tatsächliche Receipts. Fehlender Sollumfang sperrt COMPLETE. Separates `declared_scope()`; gespeicherte Fehler können nicht durch Weglassen des Arguments versteckt werden. RED→GREEN einschließlich realer Dateitests. |
| 2, P1 | Expected als observed gespeichert | Explizite Rolle OBSERVED/EXPECTED, unbekannte Rollen abgewiesen. Expected bleibt ausschließlich expected. RED→GREEN. |
| 3, P2 | Unbekannte oder widersprüchliche HEPData-Identität akzeptiert | Nichtleere IDs/Versionen und Übereinstimmung mit SourceRecord und bestätigter Tabellenliste erforderlich. RED→GREEN. |
| 4, P2 | Achsenkoordinaten gehen verloren | Explizite Einzelpunkt-Achsenbindung und Koordinate in Punkt-ID; Mehrpunkttabellen in der Normalisierung ausdrücklich MULTIPOINT_UNSUPPORTED. Kein vorgetäuschter Kurvenimport. RED→GREEN. |
| 5, P2 | Fremde Extraktion unter Constraint-Provenienz zulässig | Jedes Extraktionseltern-Tupel muss in genau diesem Constraint stehen. RED→GREEN. |
| 6, P2 | bool/Float/NaN/ungeprüfte Einheiten bei Konversion | Exakte Dezimalzeichenfolgen und erlaubte Einheiten werden vor jeder Rückgabe geprüft. RED→GREEN. |
| 7, P3 | Scanwert ist Teil der Vergleichsgruppe | **OPEN / zurückgestellt.** Kann später eine Scanreihe zu stark aufteilen; keine falsche Freigabe im jetzigen Bestand mit ausschließlich null-Gruppen. Vor jeder späteren Vergleichsnutzung beheben. |
| 8, ursprünglich P3 | IncompleteRead lässt HTTP-Fehlerbeleg verloren gehen | Als wichtig neu eingestuft: zuverlässige Fehlerbelege sind Teil des aktuellen Auftrags. Status und begrenzte Teilbytes bleiben erhalten, Truncation wird gesetzt. RED→GREEN. |

Die Review-Regressionsdatei enthält 17 eigenständige Tests. Bestehende Tests
wurden weder entfernt noch abgeschwächt. Anfangs versehentlich mitimportierte/
geerbte Tests wurden nicht doppelt gezählt; nur Setup/Cleanup werden wiederverwendet.
Nach der Korrekturrunde besteht die gesamte Suite aus **210 unterschiedlichen Tests**.
Zusätzlich wird die ursprüngliche 185er-Teilmenge und die 140er-Foundation separat
ausgeführt; tatsächliche Ergebnisse und eindeutige Test-IDs stehen in
`CERN_TEST_RESULTS.json` und den drei zugehörigen Logs.

**Keine zweite unabhängige Abnahme behauptet:** Die Korrekturen wurden vom
Implementierer durch reproduzierte Fehler und Regressionen geprüft. Der Reviewer
hat die korrigierte Fassung und den späteren Freeze nicht erneut freigegeben.
Der Ablauf folgt der vorgesehenen einzelnen Review-/Korrekturrunde.

## Nicht beurteilte Bereiche und Entscheidung

- Wissenschaftliche Wahrheit der Publikationen/Generatorannahmen: bleibt OPEN;
  Quellenbindung und Codeprüfung ersetzen keine fachliche Abnahme.
- Unzugängliche HEPData-/Verlagsdaten: bleiben SOURCE_MISSING/OPEN; keine Proxies.
- Physikalische Vergleichbarkeit, numerischer Recast, SL-Anwendung: außerhalb
  des freigegebenen Umfangs; `sigma_SL_project = UNDEFINED`.
- Allgemeines P08–P10-System/CLI und Schutz gegen lokale Administratoren:
  nicht implementiert oder behauptet. Nur der ausdrücklich benannte Freeze.
- Vollsuite/Linter/Typecheck/Build: Der Reviewer führte keine solchen Komplett-
  Checks aus. Der Implementierer protokolliert die vollständigen Testläufe und
  Syntax-/Schema-/Integritätschecks separat; nicht konfigurierte Checks bleiben
  als nicht ausgeführt gekennzeichnet.

**Gatebewertung:** Unabhängige Befundaufnahme PASS; ursprünglicher Code-Review-
Freigabestatus FAIL; Behandlung der sieben wichtigen Befunde durch Regressionen
PASS; erneute unabhängige Freigabe OPEN/nicht erfolgt; Minor Nr. 7 OPEN.
Ein eingefrorener Datenstand darf ausschließlich FROZEN_PARTIAL heißen.
