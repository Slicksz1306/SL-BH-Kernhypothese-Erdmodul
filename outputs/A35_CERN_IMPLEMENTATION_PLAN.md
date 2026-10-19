# A35/CERN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Der vorliegende Auftrag erlaubt nur Spezifikation und Planung: Alle Implementierungsschritte bleiben bis zum Review unausgeführt.

**Goal:** Ein lokal überprüfbares Vertrags-, Quellen-, Normalisierungs- und Default-Deny-Mappingpaket bauen, ohne A35-Simulation, neue Produktionsphysik oder Recast vorzutäuschen.

**Architecture:** Zwei getrennte Teilprojekte teilen nur Typen, Einheiten und Provenienz. A35 validiert Material-/Operatorverträge und konservative Buchhaltung; Collider verarbeitet unveränderte Quellen in versionierte Constraints und prüft deren Anwendbarkeit. Keine Abhängigkeit vom Collider in die Earth-/Stage-Solver.

**Tech Stack:** Python 3.12, Standardbibliothek (`unittest`, `decimal`, `hashlib`, `json`, `pathlib`, `dataclasses`), vorhandenes NumPy für kleine Matrixprüfungen. Vorgesehene einzige zusätzliche Laufzeitabhängigkeit: `jsonschema` mit Draft-2020-12-Unterstützung für die tatsächlich auszuliefernden Schemas; sie vermeidet einen selbstgebauten unvollständigen Schema-Interpreter. Keine Installation in dieser Phase. In P01 wird nach Freigabe eine konkrete kompatible Version in einer isolierten Umgebung festgeschrieben; keine globale Änderung. Keine pytest-/Webframework-/ML-Abhängigkeit.

**Spec:** Die vier Dateien im selben Verzeichnis:

- A35_PHYSICAL_CLOSURE_SPEC.md
- A35_MATERIAL_CONTRACT_SPEC.md
- CERN_LHC_CONSTRAINT_LAYER_SPEC.md
- SL_COLLIDER_MAPPING_SPEC.md

Stand 2026-10-07; Planversion 1.0.0; Status REVIEW_REQUIRED. Aktuelle Umgebung lesend geprüft: Python 3.12.10, NumPy importierbar, jsonschema und pytest nicht vorhanden. Das ist keine Prüfung einer künftigen Buildumgebung.

## Global Constraints

- `CERN_CONSTRAINT_SNAPSHOT_DATE = 2026-10-07`.
- `INSUFFICIENT_MODEL_DEFINITION` und `sigma_SL_project = UNDEFINED` bleiben der heutige SL-Ausgangsstand.
- `SOURCE_UNAVAILABLE` wird nie als leerer erfolgreicher Datensatz ausgegeben.
- Stage 3.95B/C ist verbindliche Ausgangsbasis; keine Änderung bestehender Stage-Skripte.
- Q_bullet und Q_m getrennt; S−1 Diffusionsmoden; Vollmischungs-Massenkompatibilität obligatorisch.
- Unbekannte Koeffizienten bleiben offen, auch wenn Verträge und Tests PASS liefern.
- Ausschließlich öffentliche Quellen abrufen; lokale Forschung/Secrets nicht hochladen.
- Keine QE-Rechnung, kein mixing_beta, keine A35-Simulation, kein Recast, kein Parameterscan, kein ML-Fitting.
- Keine automatische Git-Initialisierung, keine Commits/Staging im vorhandenen Forschungsrepository. Reviewfähige kleine Änderungen; ein später autorisierter Paket-Commit darf nur Paketdateien enthalten.
- Der aktuelle Arbeitsschritt erzeugt genau fünf Markdown-Dokumente und stoppt. Alle unten genannten Code-/Schema-/Datenpfade sind zukünftige Ziele, keine existierenden Lieferungen.

## Review Focus

1. Matchingfläche vs. echte Absorption: innere Speicherung darf im zeitabhängigen Ledger nicht verschwinden; P04 testet A05/A06.
2. Richtiges JSON mit falscher Physik: Einheiten, Matrixbasis und gemeinsame Materialdomäne müssen zusätzlich zum Schema geprüft werden; P03 testet M05/M07/M16.
3. Fehlerseite mit HTTP 200 und manipulierte Pfade: keine falsche Quellenaufnahme oder Fremddatei lesen; P02 testet C24/M15.
4. Unvollständige gleiche Vergleichshashes: null oder vom Benutzer erfundene Gruppe darf keinen Vergleich autorisieren; P05/P09 testen C14/C15/S11.
5. Versionsrennen und historischer Stichtag: kein Überschreiben, kein Einmischen späterer Daten; P10 testet C01–C03/C17/C18.

---

## 1. Zielstruktur und Verantwortlichkeiten

Nach Review vorgeschlagener Paketroot:
`C:\Users\xfire\Documents\Codex\2026-10-07\files-pasted-by-the-user-sl\outputs\a35_cern_layer`.
Alle folgenden Pfade sind relativ zu diesem Root. Keine Datei dieses Pakets wird jetzt angelegt.

```text
pyproject.toml, dependency-lock.txt, README.md
sl_constraints/
  __init__.py
  common/types.py, common/units.py, common/provenance.py, common/schema.py
  a35/material.py, a35/readiness.py, a35/ledger.py
  collider/source_store.py, collider/extraction.py, collider/normalize.py
  collider/benchmark.py, collider/applicability.py, collider/compare.py
  collider/snapshot.py
  cli.py
schemas/
  common.schema.json, material.schema.json, inner_contract.schema.json
  ledger.schema.json, source.schema.json, extraction.schema.json
  constraint.schema.json, mapping.schema.json, snapshot.schema.json
tests/
  test_contracts_units.py, test_source_store.py, test_material.py
  test_ledger.py, test_benchmark_schema.py, test_normalize.py
  test_source_ingestion.py, test_applicability.py, test_compare.py
  test_snapshot_cli.py
  fixtures/ [ausschließlich kleine lizenzierte oder synthetische Fixtures]
data/
  raw/<sha256>/..., extracted/<artifact_id>.json
  normalized/<artifact_id>.json, mappings/<artifact_id>.json
  derived/<artifact_id>.json, snapshots/<snapshot_id>/manifest.json
```

`raw` wird ausschließlich aus Originalbytes befüllt. Onlinezugriff ist ein ausdrücklich aufgerufener Beschaffungsschritt; sämtliche Tests laufen offline mit lokalen Fixtures. Extraktion aus Original-PDFs ist keine Voraussetzung für einen allgemeinen PDF-Parser: reviewed table transcripts sind erlaubt, wenn jede Zelle Locator und gesicherten Parenthash hat. Vorhandene HEPData-Tabellen haben Vorrang.

Teilprojekt A: P01→P03→P04. Teilprojekt B: P01→P02→P05→P06→P07→P08→P09→P10. Nach P01 können die read-only/isolierten A- und B-Arbeiten unabhängig erfolgen, ohne parallele Änderungen an gemeinsamen Typen. Vertragliche Änderung benötigt zuerst aktualisierte Specs und Cross-Tests.

## 2. Gemeinsamer Interfacevertrag

Die folgenden Typnamen sind nach P01 kanonisch. Sie werden in `common/types.py` als unveränderliche Dataclasses/Enums oder validierte TypedDicts mit den Feldern der referenzierten Specs definiert; keine unvalidierten Dictionaries im numerischen Kern.

| Typ | Festgelegter Inhalt / Eigentümer |
|---|---|
| QuantityRecord | Wert/Einheit/Definition/Unsicherheit/Domain/Provenienz, Material Spec §2 |
| Issue | code, json_pointer, severity, message, source_refs |
| GateResult | gate_id, branch_id, status, reason_codes, evidence_refs, dependency_ids |
| ValidationReport | valid_structure, issues, gates, schema_version |
| SourceRecord, IngestionReceipt | Source-/Abrufstatus aus CERN Spec §3 |
| ExtractionRecord | unveränderte Originalzelle/Locator und parse status |
| MaterialPackage, BranchRequirements | Material Spec §§3–6, branchabhängige Pflichtinterfaces |
| InnerContracts | MatchingContract, SinkContract, EnergyMatchingContract |
| Transfer | transfer_id, event_id, from_reservoir, to_reservoir, species_delta, charge_C, energy_J, boundary_id, provenance_refs |
| LedgerReport | mass/element/charge/energy residuals, scales, issues; keine Zeitintegration |
| ColliderConstraint, SemanticKey | CERN Spec §§4–5 |
| SLModelParameters, ColliderMapping, ApplicabilityResult | Mapping Spec §§2–4 |
| ComparisonResult | allowed, mode, reasons, context_differences, ordered_values/null; kein neuer CL |
| SnapshotManifest, SnapshotResult | Snapshot/Coveragestatus, Parenthashes, Auditissues |

`Transfer.species_delta` ist der am Empfänger gewonnene Vektor; Sender verliert denselben Vektor. Ladung folgt bei materiellen Transfers aus diesem Vektor und dient zusätzlich als geprüfte Redundanz, nicht als freier zweiter Wert. Nichtmaterielle/innere Umwandlungskanäle brauchen eine ausdrücklich andere Transferart und Bilanzdefinition. Ein event_id darf verschiedene disjunkte Teiltransfers haben; dieselbe physische Transfer-ID darf nicht doppelt verbucht werden.

## 3. Aufgaben

### P01 — Typen, Einheiten, Schema-Grundlage

**Ziel:** Gemeinsame sichere Datentypen; reproduzierbare Testumgebung ohne Forschungscodeimporte.

**Dateien:** `pyproject.toml`, `dependency-lock.txt`, Paket-`__init__.py`-Dateien, `common/types.py`, `common/units.py`, `common/schema.py`, `schemas/common.schema.json`, `tests/test_contracts_units.py`.

**Interfaces:** `convert_quantity(q: QuantityRecord, target_unit: str) -> QuantityRecord`; `validate_schema(payload: object, schema_id: str) -> ValidationReport`. Schema-Resolver nur lokal im Paket, keine Netzwerk-$refs.

**Eingaben:** Specs, explizite synthetische Quantity-Fixtures, nach Freigabe lokal isolierte Pythonumgebung.
**Ausgaben:** validierte Typen, deterministische Einheitentransformation mit DerivationRecord.
**Schemas:** Draft 2020-12, geschlossene Objektfelder, kontrollierte Enums und Nullregeln.
**Tests:** C04/C05/C26, M01/M02/M09/M13/M14; 1000 GeV→1 TeV, 1 pb→1000 fb, 1000 pb^-1→1 fb^-1; bool/NaN/Infinity abweisen.
**Abhängigkeiten:** keine Implementierungsvorläufer; zusätzliche jsonschema-Abhängigkeit ist in diesem Plan begründet, Installation erst nach Freigabe und ggf. Netzwerkberechtigung.
**Fehlerfälle:** unbekannte Version/Einheit, externe $ref, fehlende Provenienz, ungültige Decimal-Konversion.
**Trust Boundaries:** fremdes JSON→validierte Typen; kein automatisches eval/Import.
**Akzeptanzkriterien:** Konversionen erhalten Quellenreferenzen und transformieren Kovarianzen quadratisch; Testimporte starten weder Netzwerk noch QE.

- [ ] Test `test_energy_conversion` schreiben: `convert_quantity(q(1000,'GeV'),'TeV').value == 1` und unveränderte Parentreferenz.
- [ ] `python -m unittest discover -s tests -p test_contracts_units.py -v` ausführen; fehlende Implementierung muss als RED dokumentiert werden.
- [ ] Typen/Schema und ausschließlich die in Specs benötigten Einheitentransformationen implementieren; installierte Paketversionen im Lock festhalten, keine globale Installation.
- [ ] Gleichen Testbefehl ausführen: GREEN, null ungewollte Nebeneffekte.
- [ ] Diff/Dependencybegründung reviewen; erst dann die Interfaces für P02/P03/P05 einfrieren.

### P02 — Unveränderliche Quellenaufnahme und Provenienz

**Ziel:** Originalbytes und Fehlerreceipts strikt trennen.
**Dateien:** `common/provenance.py`, `collider/source_store.py`, `schemas/source.schema.json`, `tests/test_source_store.py`.
**Interfaces:** `ingest_local(source: SourceRecord, payload: bytes, root: Path) -> IngestionReceipt`; `acquire_public(source: SourceRecord, root: Path) -> IngestionReceipt`; `verify_source(source: SourceRecord, root: Path) -> ValidationReport`.
**Eingaben:** explizite Quellen-URL bzw. lokale Originalbytes, freigegebener Paketroot.
**Ausgaben:** gehashte Raw-Datei oder SOURCE_UNAVAILABLE/FORMAT_UNSUPPORTED/RESOURCE_LIMIT-Receipt.
**Schemas:** SourceRecord mit getrennten DOI/arXiv/INSPIRE/HEPData-Namespaces; lokaler Pfad/Hash und echte Abrufzeit.
**Tests:** M03/M15; C07/C16/C23/C24; zwei URLs derselben Quelle erzeugen keine unabhängigen Messungen.
**Abhängigkeiten:** P01.
**Fehlerfälle:** Timeout, Redirect auf unzulässiges Ziel, Login-HTML, Hashabweichung, Traversal/Symlink, übergroße Daten, fehlende historische Version.
**Trust Boundaries:** öffentliches Netz→untrusted Raw; keine Projektuploads, keine Ressourcen-Ausführung.
**Akzeptanzkriterien:** Fehler kann nicht als ACQUIRED mit leerem Inhalt erscheinen; existierende Hashobjekte werden nicht überschrieben; Host/Contenttype/Limits geprüft.

- [ ] `test_http_error_is_not_empty_success` mit simuliertem Timeout schreiben: Receipt.status=SOURCE_UNAVAILABLE, keine Raw-Datei; `test_traversal_rejected` ergänzt Fremdpfadfixture.
- [ ] `python -m unittest discover -s tests -p test_source_store.py -v` RED prüfen.
- [ ] Lokale Ingestion/Hashprüfung und explizite öffentliche Beschaffung implementieren; Netzwerk im Test mocken, Originalbytes nie durch aufbereiteten Text ersetzen.
- [ ] Gleichen Testbefehl GREEN prüfen und Raw-Byteidentität assertieren.
- [ ] Dateischreibziele und Offline-Default reviewen.

### P03 — Materialverträge und Readiness

**Ziel:** Syntaktische Gültigkeit von physischer Verwendbarkeit trennen.
**Dateien:** `a35/material.py`, `a35/readiness.py`, `schemas/material.schema.json`, `schemas/inner_contract.schema.json`, `tests/test_material.py`.
**Interfaces:** `validate_material(package: MaterialPackage, requirements: BranchRequirements) -> ValidationReport`; `assess_readiness(material_report: ValidationReport, inner: InnerContracts | None, requirements: BranchRequirements) -> tuple[GateResult,...]`.
**Eingaben:** Materialpaket, festgelegter Branch, separate Innenverträge.
**Ausgaben:** GateResult mit stabilen Codes und Feldlocators; keine Koeffizienten-Schätzung.
**Schemas:** vollständige Material-/Innenverträge aus Material Spec.
**Tests:** M04–M18; A09–A15/A17/A19/A20. Matrix-PSD/Nullraum nur im dokumentierten skalierten Raum prüfen.
**Abhängigkeiten:** P01; gehashte Quellen können zunächst ausschließlich synthetische lokale Fixtures sein. Reale Akquisition ist nicht erforderlich, um Ablehnung zu testen.
**Fehlerfälle:** Ni fehlt, falscher Frame, Matrixachse vertauscht, fehlender Wärmeblock, statische Response als dynamisch, offene M_Q.
**Trust Boundaries:** Forschungsdaten→Solverreadiness; Quellenhash ist kein Physiknachweis.
**Akzeptanzkriterien:** Offenes Material bleibt strukturell repräsentierbar, aber RELEASE blockiert. Keine Stage-3.96-Freigabe durch erfolgreiche Vertrags-Unit-Tests.

- [ ] `test_feosi_does_not_close_feniosi` und `test_material_pass_does_not_close_sink` schreiben; letzterer erwartet Gate A35.RELEASE=BLOCKED bei fehlendem InnerContracts.
- [ ] `python -m unittest discover -s tests -p test_material.py -v` RED prüfen.
- [ ] Validatoren, Projektor-/Frame-/Domänen-/Matrix-/Wärmeblockprüfungen implementieren; keine Datenreparatur.
- [ ] Gleichen Testbefehl GREEN prüfen, negative Eigenwertfixture explizit enthalten.
- [ ] Gates gegen die neun 3.95K-Jobs und Physical Spec §8 reviewen.

### P04 — Konservative Transferbuchhaltung, kein Simulationssolver

**Ziel:** Massen-/Element-/Ladungs-/Energiebilanzen einzelner diskreter Transfers auditieren.
**Dateien:** `a35/ledger.py`, `schemas/ledger.schema.json`, `tests/test_ledger.py`.
**Interfaces:** `audit_transfers(transfers: tuple[Transfer,...], species_basis: SpeciesBasis, requirements: BranchRequirements) -> LedgerReport`; SpeciesBasis ist die validierte `MaterialPackage.species_basis` aus P03.
**Eingaben:** benannte Reservoirs OUTER/INNER/SEED/RADIATION/BATH/EXTERNAL und einzelne Transfers.
**Ausgaben:** Residuen/Fehler, keine Zeitlösung, kein physisches Q_eq/Mdot.
**Schemas:** eindeutige Transfer- und Ereignis-IDs, Restmasse-/Wärmekonvention.
**Tests:** A01–A08/A16/A18 sowie Duplikate und unabhängige Teiltransfers eines Ereignisses.
**Abhängigkeiten:** P01/P03.
**Fehlerfälle:** gleiche Transfer-ID doppelt, Ladung nicht aus Spezies erhalten, innerer Speicher ignoriert, isothermes Bad fehlt, positive Vollmischungsakkretion bei u=0.
**Trust Boundaries:** deklarierte Transfers→Bilanzergebnis; Ledger-PASS ist kein Beleg für die physische Existenz der Transferrate.
**Akzeptanzkriterien:** 7-J-Transfer plus 2-J-Weitergabe ergibt exakt (−7,+5,+2) J; Rückführung auf stationäres Innengebiet ausdrücklich geprüft.

- [ ] `test_inner_storage_energy_balance`: Differenzen outer=−7, inner=+5, seed=+2; Gesamtresiduum=0. `test_duplicate_transfer_fails`: DUPLICATE_TRANSFER.
- [ ] `python -m unittest discover -s tests -p test_ledger.py -v` RED prüfen.
- [ ] Algebraischen Auditor implementieren, keine PDE/ODE-Integration oder Naturkonstanten-Fitwerte.
- [ ] Gleichen Testbefehl GREEN prüfen, Kanal-Signaturen und Einheitenfehler einschließen.
- [ ] Source/Sink-Vorzeichen und äußere/innere Grenzflächen auditieren.

### P05 — Benchmark- und Constraint-Schema

**Ziel:** Physikalisch inkompatible Zahlen können nicht denselben gültigen Vergleichsraum erhalten.
**Dateien:** `collider/benchmark.py`, `schemas/constraint.schema.json`, `tests/test_benchmark_schema.py`.
**Interfaces:** `validate_constraint(record: ColliderConstraint) -> ValidationReport`; `semantic_key(record: ColliderConstraint) -> SemanticKey | None`; `comparison_group(key: SemanticKey) -> str`.
**Eingaben:** typisierte synthetische Constraints mit vollständigen/fehlenden Annahmen.
**Ausgaben:** validierter Record und reproduzierbarer Key/Hash oder null mit Lücken.
**Schemas:** alle Objekttypen, Observable-Union, erwartete/beobachtete Grenzen, Datensatz-/CL-/Kanalmetadaten.
**Tests:** C05–C15/C19/C26/C28; Massengrenze nicht mit M_D-Wert verwechseln.
**Abhängigkeiten:** P01.
**Fehlerfälle:** RS/ADD gemischt, dimensionslose BR als Querschnitt, expected nach observed kopiert, Feld fehlt, gefälschte Gruppe.
**Trust Boundaries:** extrahierte Angaben→kanonische Semantik; Gruppenstrings aus Eingaben werden nie vertraut.
**Akzeptanzkriterien:** fehlende relevante Definition erzeugt group=null; dieselbe Quelle darf viele eindeutige Constraints stützen.

- [ ] `test_add_dimensions_split_groups`: vollständig definierte n2/n6-Fixtures ergeben verschiedene Keys. `test_unknown_never_gets_group`: null.
- [ ] `python -m unittest discover -s tests -p test_benchmark_schema.py -v` RED prüfen.
- [ ] Typ-/Schema-/Keylogik implementieren; Observable-Typen und Vergleichsmodi aus Spec exakt übernehmen.
- [ ] Gleichen Testbefehl GREEN prüfen; zu jedem erlaubten Beispiel eine mutierte Negativfixture.
- [ ] Fingerprintfelder und fehlende Definitionen einzeln reviewen.

### P06 — Extraktion und Normalisierung mit Locatorerhalt

**Ziel:** Tabellenformate in überprüfbare Records umsetzen, ohne Modellannahmen zu erraten.
**Dateien:** `collider/extraction.py`, `collider/normalize.py`, `schemas/extraction.schema.json`, `tests/test_normalize.py`.
**Interfaces:** `extract_table(payload: bytes, source: SourceRecord, format_id: str) -> tuple[ExtractionRecord,...]`; `normalize(extracted: tuple[ExtractionRecord,...], benchmark: BenchmarkDefinition) -> tuple[ColliderConstraint,...]`. BenchmarkDefinition enthält den vollständigen festen Teil des SemanticKey plus benannte Scanachsen, Quellen und RequiredFieldSet.
**Eingaben:** HEPData-JSON oder kontrollierte reviewed-CSV-Tabelle mit Sidecar-Metadaten; keine willkürlichen PDF-Heuristiken.
**Ausgaben:** getrennte Extraction-/Constraint-Artefakte mit Parenthashes und Zelllocators.
**Schemas:** ExtractionRecord, Constraint, Source; feste Format-Adapterversion.
**Tests:** C04/C06/C08/C19/C24/C25; asymmetrische Fehler, fehlende Qualifier, gleiche Überschrift in verschiedenen Kanälen, malformte Zellzahlen.
**Abhängigkeiten:** P01/P02/P05.
**Fehlerfälle:** FORMAT_UNSUPPORTED, AMBIGUOUS_TABLE, REQUIRED_QUALIFIER_MISSING, UNIT_MISMATCH; keine leere Erfolgsliste bei Parserfehler.
**Trust Boundaries:** Quellzelle→Interpretation; AI-Transkript benötigt menschlich/regelbasiert überprüfbaren Source-Locator.
**Akzeptanzkriterien:** jede numerische Ausgabe rückführbar; acht ATLAS-Zeilen bleiben acht; keine Bilddigitalisierung bei vorhandenen Tabellen.

- [ ] `test_atlas_channel_rows_preserved`: acht Referenzzeilen aus CERN Spec §1.2, acht IDs und passende observed/expected-Paare; keine Änderung des Inputbytehashes.
- [ ] `python -m unittest discover -s tests -p test_normalize.py -v` RED prüfen.
- [ ] Eng begrenzte JSON/CSV-Adapter und explizite semantische Normalisierung implementieren; fehlende Tabellen bleiben Fehler/Gap.
- [ ] Gleichen Testbefehl GREEN prüfen; Originalzellen/Qualifier bleiben erhalten.
- [ ] Stichproben und komplette kleine Referenztabelle gegen Quelle reviewen.

### P07 — Primärquellen-Freeze und Coverage-Audit

**Ziel:** Die tatsächlichen Daten, nicht nur Parserfixtures, auf dem Stichtagsstand nachweisen.
**Dateien:** ausschließlich neue Objekte unter `data/raw`, `data/extracted`, `data/normalized`; `tests/test_source_ingestion.py`; Coverage-Draft als zukünftiges Snapshotobjekt.
**Interfaces:** konsumiert P02/P06; `audit_coverage(records: tuple[ColliderConstraint,...], required_scope: CoverageSpec) -> ValidationReport` in `collider/normalize.py`. CoverageSpec listet erforderliche Analyse/Benchmark/Kanal/Observable/Tabellen-Artefakte und deren Status, keine bloße Gesamtzahl.
**Eingaben:** Quellenregister CERN Spec §1; autorisierte explizite öffentliche Beschaffung.
**Ausgaben:** vollständige gehashte Sourceketten oder präzise SOURCE_UNAVAILABLE-/Versions-/Coverage-Lücken.
**Schemas:** Source/Extraction/Constraint und Coverage-Teil des Snapshot-Schemas.
**Tests:** C08/C16/C17/C18/C22/C23/C25; keine Live-Netzwerkabhängigkeit der Regressionstests.
**Abhängigkeiten:** P02/P05/P06; Netzwerkzugriff nur für Beschaffung, nicht für Tests. Netzwerk-/Quellenblocker dürfen P08-Negativtests nicht verhindern.
**Fehlerfälle:** HEPData nicht abrufbar, ungültiger Recordalias, spätere Version, Paper-v2/Verlagsabweichung, fehlende CMS-Benchmarkkurven.
**Trust Boundaries:** publizierter Text vs. richtige Version vs. richtige Tabelle sind drei unabhängige Prüfungen.
**Akzeptanzkriterien:** COMPLETE nur bei erfüllter Scope-Matrix; anderenfalls ehrlich PARTIAL mit fehlenden Tabellen. Keine Ersatzwerte aus Plots/LLM.

- [ ] `test_missing_hepdata_blocks_complete` und `test_wrong_source_version_rejected` schreiben; Sourceausfall darf keine leere grüne Coverage erzeugen.
- [ ] `python -m unittest discover -s tests -p test_source_ingestion.py -v` RED prüfen.
- [ ] ATLAS-v2 und Verlagsversion sichern/abgleichen; HEPData-IDs und Tableversions verifizieren. CMS-v2 samt B1–B3/C1–C6, SB, Sphaleronen und modellunabhängigen Kurven benchmarkweise erfassen. PDF/Scaledefinitionen/Generatorannahmen nicht aus Labels inferieren.
- [ ] Gesamte kleine ATLAS-Tabelle, CMS-Referenzpunkte und jede Tabellenachse kontrollieren; Hashketten und Coverageaudit laufen lassen. Gleicher Testbefehl muss GREEN sein, auch wenn reale Coverage korrekt PARTIAL meldet.
- [ ] Tatsächliche Quellenlücken reviewen. Das Dokumentations-Review dieses Plans ist keine Garantie erfolgreicher späterer HEPData-Beschaffung.

### P08 — SL-Mapping und Applicability

**Ziel:** Fehlende Produktionsphysik und echte Modellkonflikte deterministisch unterscheiden.
**Dateien:** `collider/applicability.py`, `schemas/mapping.schema.json`, `tests/test_applicability.py`, später `data/mappings`.
**Interfaces:** `assess_applicability(model: SLModelParameters, constraint: ColliderConstraint, mapping: ColliderMapping | None) -> ApplicabilityResult`.
**Eingaben:** heutiger unvollständiger SL-Record, vollständige synthetische Benchmarks, ggf. akzeptierte reale Constraints.
**Ausgaben:** genau einer der fünf Statuswerte plus stabile Gründe; numerical_verdict NOT_EVALUATED.
**Schemas:** SLModelParameters, ColliderMapping, CompatibilityEvidence, ApplicabilityResult.
**Tests:** S01–S10/S12–S18; insbesondere all-known-match als positiver Gegenfall und genau ein unbekanntes Pflichtfeld als Negativfall.
**Abhängigkeiten:** P01/P05; reale P07-Daten optional, entscheidende Tests synthetisch/offline.
**Fehlerfälle:** fehlender σhat-/Decay-/Lifetime-/Skalenbezug, vorgeschlagenes nichtreviewtes Mapping, etablierter Regimekonflikt.
**Trust Boundaries:** LLM-Mappingvorschlag→regelbasierte Freigabe; ein Benchmarkübernehmen ist keine neue SL-Herleitung.
**Akzeptanzkriterien:** heute INSUFFICIENT_MODEL_DEFINITION und σ_SL=UNDEFINED; DIRECTLY_APPLICABLE nur bei vollständiger positiver Evidenz, ohne Ausschlussbehauptung.

- [ ] `test_current_sl_stays_undefined`: Status und UNDEFINED-Rate exakt prüfen; `test_one_missing_field_denies_direct` parametrisch für jedes Pflichtfeld.
- [ ] `python -m unittest discover -s tests -p test_applicability.py -v` RED prüfen.
- [ ] Prüfprioritäten aus Mapping Spec §4 implementieren; kein LLM/Netzwerkaufruf im Entscheider.
- [ ] Gleichen Testbefehl GREEN prüfen, Gründe/Semantik stabil sortieren.
- [ ] Domain-/Mismatch-/Recast-Grenzen fachlich reviewen.

### P09 — Vergleichsschutz, keine neue Statistik

**Ziel:** Ausschließlich semantisch zulässige Gegenüberstellungen.
**Dateien:** `collider/compare.py`, `tests/test_compare.py`.
**Interfaces:** `compare_limits(left: ColliderConstraint, right: ColliderConstraint, mode: ComparisonMode=SAME_DATASET) -> ComparisonResult`.
**Eingaben:** validierte Constraints, expliziter Modus SAME_DATASET oder REACH_COMPARISON.
**Ausgaben:** erlaubte Wertegegenüberstellung mit Kontextdifferenzen oder COMPARISON_REFUSED. Keine likelihoodbasierte Kombination.
**Schemas:** ComparisonResult verwendet common-Typen und vollständigen SemanticKey.
**Tests:** C09–C15/C20/C21, S11/S14; Nullgruppen, unterschiedliche Energien, unterschiedliche CL-Verfahren, Acceptance-Doppelzählung.
**Abhängigkeiten:** P05/P06; P08 erklärt SL-Anwendbarkeit, ersetzt die Gruppenprüfung nicht.
**Fehlerfälle:** inkompatible Objekte, Kanäle, Observable, Werteorientierung, Datensätze oder gefälschte Keys.
**Trust Boundaries:** validierte Metadaten→numerischer Vergleich; gleiche Einheit ist nicht gleiche Messgröße.
**Akzeptanzkriterien:** ATLAS-QBH vs CMS-semiklassisch wird verweigert, nicht nach Grenzmasse gerankt. Kein globales "CMS strenger".

- [ ] `test_qbh_vs_semiclassical_refused`: allowed=False, reason enthält COMPARISON_GROUP_MISMATCH bzw. OBJECT_CLASS_MISMATCH; `test_same_group_same_dataset_allowed` als positiver Test.
- [ ] `python -m unittest discover -s tests -p test_compare.py -v` RED prüfen.
- [ ] Minimalen Guarded-Comparator implementieren, ohne Interpolation, Cross-Section-Generator oder Statistikfit.
- [ ] Gleichen Testbefehl GREEN prüfen, Datensatzmodi getrennt testen.
- [ ] Ergebnisformulierungen gegen die Aussagegrenzen reviewen.

### P10 — Snapshot, Offline-CLI und Gesamtprüfung

**Ziel:** Überprüfbares Paket mit unveränderlichem Snapshot und ehrlichem Teilstatus ausliefern.
**Dateien:** `collider/snapshot.py`, `cli.py`, `schemas/snapshot.schema.json`, `tests/test_snapshot_cli.py`, `README.md`; neue `data/snapshots` nur nach positivem Freeze-Audit.
**Interfaces:** `freeze_snapshot(manifest: SnapshotManifest, root: Path) -> SnapshotResult`; `verify_snapshot(snapshot_id: str, root: Path) -> ValidationReport`; `main(argv: list[str] | None=None) -> int`.
**Eingaben:** akzeptierte Artefakte und Coverage aus P07, Mapping aus P08, explizites Partial-/Complete-Ziel.
**Ausgaben:** neues Manifest mit Hash-/Versionskette, konsolenlesbarer Report oder verweigerter Freeze.
**Schemas:** SnapshotManifest mit Stichtag, Revision, Scope, Sourceversionen, Coverage und supersedes.
**Tests:** C01–C03/C17/C18/C22/C23/C27/C28 sowie Offline-End-to-End und schreibgeschützte Sourcefixtures.
**Abhängigkeiten:** P01–P09; bei SOURCE_UNAVAILABLE muss der Offline-Teil trotzdem testbar sein, wissenschaftliche Coverage bleibt partiell.
**Fehlerfälle:** Race/Name existiert, Hashmutation, Datumsverletzung, unterbrochener Schreibvorgang, unerlaubter Complete-Status.
**Trust Boundaries:** Audit→Publikation eines Snapshots; Freeze niemals automatisch beim Parsen/Start.
**Akzeptanzkriterien:** gesamter Offline-Testlauf GREEN; produktive Datenqualität separat ausgewiesen; Originalrepo unverändert; kein physischer Solver/Recast mitgeliefert.

- [ ] `test_concurrent_freeze_is_exclusive` mit zwei unabhängigen Prozessen schreiben; exakt ein Erfolg, vorheriger Snapshot unverändert. `test_offline_cli_does_not_fetch` ergänzt explizit blockierten Netzwerkzugriff.
- [ ] `python -m unittest discover -s tests -p test_snapshot_cli.py -v` RED prüfen.
- [ ] Snapshot/CLI implementieren. Befehle: `validate-material`, `validate-constraints`, `assess-applicability`, `compare-limits`, `verify-snapshot`, `freeze-snapshot`; Netzwerk nur im separat aufgerufenen `acquire-source`. Exitcodes: 0=voller angeforderter Erfolg, 2=Validierungsfehler, 3=blockiert/partiell, 4=Quellen-/I/O-Fehler.
- [ ] `python -m unittest discover -s tests -v` und `python -m compileall -q sl_constraints tests` ausführen; `python -m pip check` in isolierter Umgebung. Testberichte dürfen Daten-PARTIAL nicht in wissenschaftliches PASS umdeuten.
- [ ] READMEs, CLI-Hilfe, Beispielaufrufe, Dependencylock und Scope prüfen; nur tatsächlich verifizierte Snapshotdateien ausweisen. STOP zur Ergebnisreview, keine weitergehende Rechnung.

## 4. Abnahme- und Testmatrix

| Spezifikationsanforderung | Implementierungsschritt |
|---|---|
| Spezies/Masse/Ladung/Energie, Doppelbuchung, Innenstorage | P03/P04, A01–A08/A16/A18 |
| S−1/Frame/Zustands-/Transportkonsistenz | P03, A09–A15/A17/A19/A20 |
| Material-Provenienz/Domäne/Ungewissheit | P01/P02/P03, M01–M18 |
| Raw→Extraction→Normalized mit Sourceversion | P02/P06/P07, C03/C07/C08/C16–C19/C23–C26 |
| Einheiten/CL/Nullwerte/Enums | P01/P05/P06, C04–C06/C19/C26 |
| Kanal-/Regime-/Observable-/Gruppentrennung | P05/P08/P09, C09–C15/C20/C21, S01–S18 |
| Snapshot-Immutability und Stichtag | P10, C01–C03/C17/C18/C22/C23/C27/C28 |
| HEPData/Verlagsabgleich, CMS-Benchmarkcoverage | P07, kontrollierter Datenreview zusätzlich zu Unit-Tests |
| keine A35-/Collider-Überdehnung | P03/P08/P09/P10 plus fachliche Review |

Produktive Interpolation, eigene Cross Sections, Integrationen, Monte Carlo, Recasts, Likelihoodkombination und physische PDE/DAE-Zeitlösungen bleiben FUTURE_SEPARATE_AUTHORIZATION. Die entsprechenden Eingabeverträge sind vorbereitet, keine dieser Funktionen ist für die jetzige Softwareabnahme erforderlich oder heimlich durch Proxycode zu ersetzen.

## 5. Interne Konsistenzprüfung der fünf Dokumente

Prüfung in dieser Dokumentationsphase: Datei-/Scopeprüfung und inhaltlicher Abgleich, keine implementierten Tests. Kontrollpunkte:

- Stage-3.95B/C-Konventionen, Hashes und unverändertes Quellrepository.
- Kein freies rho zusätzlich zu vollständigen n_s, keine freie T zusätzlich zu vollständiger Energie-EOS, phi elliptisch statt erfundener zusätzlicher Ladungszustand.
- Q_m enthält innere Ladung; Strom über r_m ist nur im passenden Grenzfall Seedabsorption.
- Nichtisotherme Wärme-/Stoffkräfte haben eine explizite konjugierte Flusskonvention.
- Massen-, Ladungs- und Energieüberträge mit Gegenbuchung; Restmasse und Wärme getrennt.
- Readiness != Schema-PASS; applicability != numerischer Ausschluss; Quellenabruf != eingefrorener Snapshot.
- Die acht ATLAS-Referenzzeilen sind Online-Tabellenprüfung, keine gehashte Produktionsdatenbank; CMS bleibt punktweise unvollständig.
- HEPData-Ausfälle bleiben SOURCE_UNAVAILABLE; beide Analysen haben FROZEN_NORMALIZED_COUNT=0.
- Jede vorgegebene Testklasse hat mindestens einen konkreten Negativ-/Positivfall und einen zuständigen Schritt.
- Spezifische mathematische Gültigkeit, Well-posedness und Quellencoverage bleiben fachliche Reviewpunkte, keine durch Dokumentenprüfung bewiesenen Eigenschaften.

Tatsächlich ausgeführte Dokumentprüfung am 2026-10-07: fünf Dateien vorhanden, Codeblock-Begrenzer in allen fünf Dateien ausgeglichen; zehn Planschritte mit jeweils allen elf geforderten Rubriken; 20 A35-, 18 Material-, 28 Collider- und 18 Mapping-Testfälle mit eindeutigen IDs, insgesamt 84 spezifizierte Fälle. Keine produktiven Tests ausgeführt. Die vier Referenzhashes aus Physical Spec §1 und Repository-HEAD sind nach der Dokumenterstellung unverändert; der sichtbare Git-Status zeigt dieselben vorher bestehenden Änderungen. Drei bereits vorhandene temporäre Repository-Unterordner sind nicht lesbar und wurden nicht untersucht. Das geplante Codeverzeichnis `outputs/a35_cern_layer` existiert nicht. Eine erste rein lesende PowerShell-Strukturprüfung hatte einen Pipeline-Syntaxfehler; die korrigierte Prüfung lief mit Exitcode 0. Es wurden keine weiteren Ergebnisdateien für diese Prüfung erzeugt.

## 6. Review und Stop

Jetzt geliefert werden ausschließlich die fünf Spezifikations-/Planungsdokumente. Es gibt keine neuen Parser, Schemas als Softwaredateien, Recasts, QE-Läufe oder normalisierten Produktionssnapshots. Der bestehende mixing_beta-Test bleibt geparkt.

Empfohlene nächste Reihenfolge nach Freigabe: P01 gemeinsame Verträge; P02 Quellenintegrität und P03 Materialgates; P04 Bilanzen; P05/P06 Colliderstruktur und Normalisierung; P07 Primärdaten/Coverage; P08 Mapping; P09 Vergleichsschutz; P10 unveränderlicher Snapshot und Gesamtprüfung.

Für die spätere Umsetzung ist eine schrittweise Umsetzung mit unabhängiger Review je Vertragsgrenze vorzuziehen, weil Fehler in Einheiten, Quellenversionen oder Modellzuordnung unbemerkt wissenschaftliche Aussagen verändern könnten. Alternativ native Umsetzung in dieser Sitzung mit abschließender unabhängiger Review. Die Ausführungsart wird erst nach Dokumentenreview gewählt; dieser Plan löst keine Implementierung aus.
