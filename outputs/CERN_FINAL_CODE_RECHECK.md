# CERN/A35-Abschluss: unabhängige Code-Nachprüfung

Stand: 18.10.2026. Frische Read-only-Prüfung durch eine getrennte
Subagent-Instanz. Sie hat den eingefrorenen Bestand nicht geändert und keine
Quellen abgerufen. Ergebnis: sieben gezielt geprüfte frühere Befunde bestehen;
zusätzlich wurde eine eng umrissene Provenienzlücke gefunden und mit Regressionen
geschlossen.

| Prüfpunkt | Ergebnis der Nachprüfung |
|---|---|
| Verbindliche Soll-Coverage, Freeze, Receipts | PASS |
| EXPECTED und OBSERVED | PASS |
| HEPData-Identität, Version und Tabellen-ID | PASS |
| Koordinatenbindung / Ablehnung nicht unterstützter Mehrpunktnormalisierung | PASS |
| Extraktionseltern in Constraint-Provenienz | PASS |
| Dezimalwerte und Einheitengültigkeit | PASS |
| HTTP `IncompleteRead`-Fehlerbeleg | PASS |
| Schemaform der SourceRecord- und Constraint-Felder | PASS |
| Hashintegrität der eingefrorenen Manifestartefakte | PASS |
| Allgemeine Auflösung der `source_relationships` | Korrektur umgesetzt; Regressionen PASS |

## Neu gefundener und behobener Befund

Die frühere Freeze-Prüfung löste `historical_evidence` auf, aber prüfte nicht,
ob jede deklarierte `source_relationships`-Referenz im Snapshot tatsächlich auf
eine Quelle mit übereinstimmender ID, Version und SHA-256 zeigte. Eine fehlende
oder widersprüchliche Relationship konnte dadurch wie belegte Provenienz wirken.

`EvidenceStore.freeze()` weist solche Beziehungen jetzt als
`PROVENANCE_MISMATCH` zurück und liest die referenzierte Quelle nochmals über den
Hash-/Size-Check des Stores. Zwei gezielte Regressionstests decken fehlende Ziele,
falsche Versionen/Hashes und die gültige Referenz ab. Sie liefen erst fehlschlagend
gegen die alte Logik und danach erfolgreich mit der Korrektur.

Für die sechs im eingefrorenen Manifest gespeicherten Quellen sind die
Relationships auflösbar. Der vorhandene Snapshot und sein Manifest wurden nicht
neu geschrieben; ihr gespeicherter Datei-Hash bleibt identisch.

## Test- und Bewertungsgrenzen

Die vorherige vollständige **210er-Baseline** wurde im Abschlusslauf erneut als
exakte Menge ihrer gespeicherten Test-IDs ausgeführt. Die zwei neuen Tests erhöhen
die aktuelle Suite auf 212. Das unabhängige Review ist die neue Code-Nachprüfung;
die Tests der Korrektur führte der Implementierer aus. Ein zusätzlicher
unabhängiger Freigabelauf nach dieser Korrektur fand nicht statt.

Verbleibender kleiner Befund: `SCAN`-Koordinaten sind Bestandteil des
Vergleichsgruppenschlüssels und können künftige Punkte einer Scanreihe aufteilen.
Im vorliegenden Bestand sind alle Vergleichsgruppen null. Vor einer tatsächlichen
Vergleichsnutzung korrigieren.

Eine Manifestprüfsumme belegt Konsistenz gegenüber den gespeicherten Hashwerten,
aber keine externe Signatur. Das Review beurteilt die geprüfte Software- und
Provenienzlogik, nicht die physikalische Wahrheit der CMS/ATLAS-Annahmen.

## Abschluss-Gates

- **PASS:** 212er-Suite; exakte gespeicherte 210er-Baseline.
- **PASS:** sieben frühere Fixes; neue Relationship-Korrektur.
- **PASS:** alle 332 Snapshot-Artefakte und alle sechs SourceRecords lokal geprüft.
- **PASS:** zugängliche offizielle Exportmöglichkeit gesucht und durch benannte
  Endpunkte getestet; kein nutzbarer Export für die zwei Analysen erhalten.
- **OPEN:** wissenschaftliche Quellenfragen und fehlende Originaldaten.
- **OPEN:** kleiner Scan-Gruppenbefund.
- **OPEN:** unabhängige Nachabnahme der letzten kleinen Korrektur.
- **PARTIAL:** Snapshot bleibt unverändert `FROZEN_PARTIAL`; keine wissenschaftliche
  Vollständigkeitsfreigabe oder Physik-Closure.
