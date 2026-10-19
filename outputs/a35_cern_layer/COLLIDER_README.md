# Collider-Datenebene P05–P07

Ergänzung zur unveränderten Foundation-README. Die alte README beschreibt den
abgenommenen P01–P04-Stand; ihre damalige Sperre für P05–P07 wurde durch den
aktuellen Auftrag aufgehoben. P08–P10 bleiben gesperrt. Keine SL-Interpretation,
keine Simulation, kein Recast, keine Querschnittsberechnung und keine allgemeine CLI.

## Daten richtig lesen

`data/cern_lhc_snapshot_2026_10_07` enthält Originalbytes, Extraktionen,
normalisierte Einträge, Metadaten, Abrufbelege und eine Scope-Matrix.
Die Snapshot-ID bezeichnet den gewünschten Quellenstichtag, **nicht das Abrufdatum**.
Die Originale wurden am 18. Oktober 2026 abgerufen. Die datierten arXiv-v2-Fassungen
lagen nach der separat gesicherten Versionshistorie bereits vor dem 7. Oktober vor.
Veränderliche Metadatenseiten und Ergebnisübersichten sind nur heutige Belege;
ihnen wird kein historischer Veröffentlichungszeitpunkt angedichtet.

- ATLAS: acht getrennte Modell-/Kanalzeilen, beobachtet und erwartet.
- CMS: 216 BH-Rasterplätze, 21 String-Ball-Rasterplätze, 15 Sphaleron-Vorfaktorplätze,
  eine getrennte Abstract-Anteilsaussage und ein modellunabhängiger N>=4-Platz.
- 262 Einträge bedeuten **nicht 262 gemessene Grenzwerte**. Nur zwölf Einträge
  besitzen einen beobachteten Skalar; neun davon besitzen auch einen erwarteten.
  Die übrigen Werte sind `null`. Ein Rasterplatz bezeichnet den aus dem Paper
  deklarierten Benchmark-Kontext, nicht eine erfolgreich erhaltene HEPData-Zeile.
- `PROPOSED`/`INCOMPLETE` ist keine wissenschaftliche Abnahme. Eine agentenseitige
  Quellenprüfung ersetzt kein unabhängiges menschliches Review.
- `comparison_group=null` sperrt die Vergleichbarkeit. Auch zweimal null erlaubt
  keinen Vergleich. Ein vollständiger Hash ist nur eine Identitätsvorprüfung,
  keine Freigabe für Recast oder Anwendung auf ein SL-Modell.

Die HEPData-Abrufe waren nicht erfolgreich. `HEPDATA_STATUS.json` weist keine
bestätigten Tabellen-IDs, Versionen oder numerischen Crosschecks aus. Der
HEPData-Adapter ist offline getestet, aber **nicht an einer erfolgreich bezogenen
Tabelle dieser beiden Analysen live verifiziert**.

## Lokal prüfen

Die Foundation benötigt weiterhin nur ihren bisherigen Bestand. Für die neuen
Collider-Module ist `jsonschema` erforderlich. In dieser Arbeitsumgebung wurde
die Bibliothek ausschließlich unter `../../work/schema-prefix` installiert.

Im Paketverzeichnis:

```powershell
$env:PYTHONPATH = (Resolve-Path '../../work/schema-prefix/Lib/site-packages').Path
python -B -m unittest discover -s tests
```

Für eine andere Umgebung eine eigene virtuelle Umgebung verwenden und
`requirements-collider.lock.txt` mit `--require-hashes` installieren. Der Lock
enthält für `rpds-py` den getesteten Windows-amd64/Python-3.12-Wheel-Hash; eine
andere Plattform braucht einen separat geprüften Wheel-Hash. Keine automatische
Installation oder Netzkommunikation beim Import oder Testlauf.

Die Tests schreiben nur synthetische Dateien in ihre UUID-Unterordner unter
`work/test-tmp`; Regressionen lesen die lokalen, gehashten Veröffentlichungsbytes.
Die wissenschaftlichen Originale werden durch Tests nicht verändert.

## Module und Sicherheitsgrenzen

| Modul | Aufgabe |
|---|---|
| `schema_document.py`, exportierte JSON-Schemata | geschlossene, erforderliche und explizit nullable Felder |
| `contracts.py` | sechs unveränderliche Record-Typen, Draft-2020-12- und semantische Prüfung |
| `benchmark.py` | reproduzierbare, konservative SAME_DATASET-Vergleichsidentität |
| `extraction.py` | HEPData-JSON, benannte HTML-Tabelle, exakter HTML-Absatz mit Byteposition |
| `normalize.py` | exakte Einheitenumrechnung, getrennte Limits und Rundungs-Crosscheck |
| `sources.py` | immutable Quellenidentitäten, Hashprüfung, öffentliches HTTPS-GET, Snapshot-Freeze |
| `reproduce.py` | eng auf zwei überprüfte Originalbytehashes begrenzte ATLAS-/CMS-Rezepte |
| `coverage.py` | unabhängig vom vorhandenen Datenbestand deklarierter Sollumfang |

Schemata werden aus einer deklarativen Quelle erzeugt. Es gibt keine Remote-$ref-
Auflösung. Neue Sourcebytes werden vom analysespezifischen Adapter zurückgewiesen:
Die Semantik ist an genau die geprüften Fassungen gebunden, nicht an eine zufällig
ähnliche Tabellenposition. Eine spätere Fassung erfordert neue Prüfung und Revision.

Raw-Dateien und Source-Metadaten werden nicht überschrieben. Extraktionen und
normalisierte Objekte sind inhaltsadressiert. Das finale Manifest wird exklusiv
und atomar veröffentlicht; erneutes Einfrieren derselben ID schlägt fehl. Beim
Lesen werden die referenzierten Bytes erneut gegen ihre Hashes geprüft. Ein
vertrauenswürdiger Root und ein Dateisystem mit Hardlinks sind erforderlich.
Das ist kein OS-/Administratorschutz gegen jemanden, der den ganzen Datenbestand
und seine Hashbelege gleichzeitig austauscht.

Der Download folgt nur HTTPS-Hosts aus einer expliziten Liste, einschließlich
erneuter Redirect-Prüfung. Kein Archiv-Entpacken, keine Ausführung von Quellen,
keine lokalen Uploads. Eine HTTP-200-Challenge ist keine Publikation: Der bei CMS
gesicherte Verlagsabruf bleibt abgewiesene Roh-Evidenz, nicht SourceRecord des Papers.

## Bewusste Grenzen

Kein allgemeiner PDF-Parser, keine Graphendigitalisierung, kein heuristischer
CSV-Import. Die konkret verfügbaren Quellen verwenden den geprüften HTML-Adapter;
die HEPData-Schnittstelle akzeptiert ausschließlich das festgelegte JSON-Tabellenformat.
Tabellenfehler erzeugen Fehlerstatus, niemals leere erfolgreiche Datensätze.
Der Adapter allein bestätigt weder HEPData-Recordidentität noch Version oder
wissenschaftliche Bedeutung: diese Belege und der Paper-Crosscheck sind separat nötig.

`sigma_SL_project = UNDEFINED` bleibt unverändert.

## Abschlussstand und Review-Grenzen

212 Tests PASS; die zuvor gespeicherte 210er-Baseline wurde als exakte ID-Menge
erneut ausgeführt und besteht ebenfalls 210/210.
Der Snapshot wurde als FROZEN_PARTIAL veröffentlicht, 332 referenzierte Artefakte
wurden nach dem Freeze überprüft. Original-Coverage bleibt erhalten; die ergänzte
`COVERAGE_REVIEWED.json` prüft einen unabhängig deklarierten Sollumfang.
Der Freeze verweigert Vollständigkeit bei unbekanntem Sollumfang, unvollständiger
Coverage oder vorhandenen Fehlerbelegen – auch ohne explizites Receipt-Argument.

Der HEPData-Normalisierer verlangt eine Rolle OBSERVED/EXPECTED, belegte
Record-/Versions-/Tabellenidentität und explizite Achsenzuordnung. Derzeit werden
nur einzelne Punkte normalisiert; Mehrpunkttabellen sind MULTIPOINT_UNSUPPORTED.
Unsicherheiten und Bänder bleiben in der Originaltabelle erhalten und werden
nicht automatisch in normalisierte erwartete Bänder umgedeutet.

Offener kleiner Codebefund: Scanwerte sind derzeit Teil der Vergleichsgruppe.
Vor künftiger Vergleichsnutzung müssen Achsendefinition und Punktkoordinate
getrennt werden. Der aktuelle Bestand hat ausschließlich null-Gruppen.
Die sieben wichtigen Review-Befunde bestehen die frische Code-Nachprüfung.
Eine neu gefundene Lücke bei der Auflösung von SourceRecord-Beziehungen wurde
mit gezielten Regressionen geschlossen; Relationships müssen im Freeze zu einer
Source-ID, Version und SHA-256 aus dem selben Snapshot passen. Der letzte Fix
wurde nicht durch eine zweite unabhängige Freigabe bestätigt.
Die unabhängige Prüfung und alle Aussagegrenzen sind im übergeordneten
`CERN_INDEPENDENT_REVIEW.md` und Abschlussbericht dokumentiert.
