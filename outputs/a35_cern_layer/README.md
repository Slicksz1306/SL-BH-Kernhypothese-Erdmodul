# A35 Foundation — Phase 1, Reviewfassung

Isoliertes Python-Paket für P01–P04: semantische Größen, lokale Quellenidentität,
Materialverträge und exakte Transferbuchhaltung. **Keine Simulation und keine
physikalische Closure.** Keine Importe aus dem Forschungsrepository, keine
Netzzugriffe, kein QE/WSL, kein CERN-Parser, kein Recast und keine CLI.

## Lokal prüfen

Im Paketverzeichnis mit dem vorhandenen Python 3.12.10 und NumPy 2.5.2:

```powershell
python -B -m unittest discover -s tests -v
```

Keine Installation nötig. Das Paket ist direkt aus diesem Verzeichnis
importierbar. `pyproject.toml` dokumentiert die Laufzeitmetadaten; ein
Wheel-/Installationsworkflow gehört **nicht** zu dieser Lieferung.
`dependency-lock.txt` hält den getesteten Bestand fest, nicht die Hashes
heruntergeladener Wheels. Keine automatische Dependency-Beschaffung.

Die Source-Store-Tests erzeugen ausschließlich synthetische Daten in
`../../work/test-tmp/source-test-<UUID>` relativ zum Paketroot und entfernen
ihre eigenen Unterordner. Der Pfad wird vor dem rekursiven Test-Cleanup
auf dieses Elternverzeichnis beschränkt. Windows-Testverzeichnisse erben
Workspace-Rechte, um die eingeschränkte Codex-Testidentität zu erhalten.

## Öffentliche Kerninterfaces

| Modul | Zweck |
|---|---|
| `common.types` | Immutable `QuantityRecord`, `SourceRef`, `Uncertainty`, `StateNode`, `Domain`, `SnapshotInfo`, Status/Fehler |
| `common.units` | Geschlossenes Einheitenregister, explizites `convert_quantity` |
| `common.schema` | `parse_json`, `quantity_from_dict`, `validate_schema`, `to_wire` |
| `common.provenance` | `SourceRecord`, `DerivationRecord`, `LocalSourceStore`, `SourceSnapshot` |
| `common.numerics` | Zentrale, skalierte Matrix-Toleranzpolitik |
| `a35.material` | `Species`, `TensorRecord`, `MaterialState`, `MaterialPackage`, `validate_material`, `validate_transport`, `validate_flux` |
| `a35.readiness` | `BranchRequirements`, `assess_readiness`, `validate_full_mixture_boundary` |
| `a35.ledger` | `Transfer`, `SpeciesMovement`, `TransferLedger`, `species_transfer`, `Balance`, `LedgerAudit` |

### Zahlen und Wire-Vertrag

Physikalische Eingaben verwenden `QuantityRecord`, keine nackten Floats.
Zahlen werden als `Decimal`, Integer oder explizite Dezimalzeichenfolge
angenommen; Bool, Float und nichtendliche Zahlen werden abgewiesen.
`parse_json` erlaubt physikalische Dezimalwerte nur als Zeichenfolge, lehnt
doppelte Schlüssel und NaN/Infinity ab und begrenzt Text auf 1 MiB.

Einheit und semantischer Typ müssen passen. Kerngrenzen verlangen ausdrücklich
SI-Einheiten; ein `g`-Wert wird nicht ungefragt zu `kg`. `J/mol` wird nicht ohne
explizite Stoffmengen-/Teilchenkonvention zu `J`. Umrechnungen erzeugen neue
Objekte mit erhaltenen Quellen und exaktem rationalem `ConversionStep`.
Standardabweichungen skalieren linear, Varianzen quadratisch. Eine nicht
terminierende Dezimalumrechnung erzeugt `ROUNDING_REQUIRED`; es existiert
keine versteckte Rundungs- oder Unsicherheitspolitik.

`schemas/common.schema.json` beschreibt den begrenzten skalaren Wire-Vertrag
mit geschlossenen Feldern. Die Laufzeit benutzt konkrete typisierte Validatoren,
**keinen allgemeinen Draft-2020-12-Interpreter**. Der JSON-Schema-Metacheck mit
`jsonschema` wurde mangels installierter Bibliothek nicht ausgeführt.
`validate_schema` unterstützt `quantity` und `snapshot_info`; andere Schemata
werden abgewiesen. Material, Tensoren, Quellen und Ledger werden in Phase 1
über ihre Python-Dataclasses und semantischen Validatoren konsumiert.

Aktive Wertstatus sind `KNOWN` und `OPEN`; offene Werte benötigen einen Grund.
Matrixwerte verwenden `TensorRecord` mit expliziten Achsen und vollständig
eingehüllten Zellen. Gemeinsame Kovarianzmatrizen, Intervalle und die weiteren
Statusvarianten der ausführlichen Material-Spezifikation sind noch nicht Teil
dieser begrenzten Wire-Schnittstelle. Sie werden nicht approximiert.

### Quellen und Vertrauen

`LocalSourceStore(root).ingest_bytes(record, raw)` übernimmt nur bereits
vorliegende Bytes. Der SHA-256 muss vorab im Record stehen und wird geprüft.
Keine URL wird aufgerufen oder interpretiert. Lokatoren und Quelleninhalte
werden nie ausgeführt. Identitäten werden aus `(source_id, source_version)`
gehasht, auch zum Schutz vor Windows-Groß-/Kleinschreibkollisionen.

Originalbytes und Identitäten werden mit atomarer, nicht überschreibender
Hardlink-Veröffentlichung abgelegt. Gleiches Objekt ist idempotent; eine
Neubelegung derselben Identität ist `IMMUTABLE_CONFLICT`. Lesen prüft die Bytes
erneut. Fehlende Quellen ergeben `SOURCE_UNAVAILABLE`, nicht einen leeren Erfolg.
Minimale lokale Quellenindex-Snapshots sind datiert und unveränderlich;
später abgerufene Quellen dürfen nicht in einen früheren Stichtag eingehen.

Der Store benötigt einen **vertrauenswürdigen, vom Aufrufer kontrollierten
Root auf einem Dateisystem mit Hardlinks**. Vorhandene Symlinks/Reparse Points
und Traversal werden abgewiesen. Das ist kein Schutz gegen einen privilegierten
lokalen Angreifer, der gleichzeitig ganze Verzeichnisse austauscht. Ein Absturz
zwischen Blob- und Identitätsveröffentlichung kann einen unreferenzierten Blob
zurücklassen; vorhandene Quellen werden nicht überschrieben. Kein Garbage
Collector, Downloader oder komplettes Snapshot-System ist enthalten.

Ein Hash belegt Byteidentität, nicht die Richtigkeit der Physik. Ein
`CheckEvidence(PASS, ...)` muss auf überprüfbare Quellen verweisen; das Paket
reproduziert die dort beschriebenen wissenschaftlichen Experimente nicht.

### Material und Readiness

Unabhängige Koordinaten des unterstützten Zustands sind `T` und die `n_s`.
`rho = sum(m_s*n_s)` wird exakt geprüft. Eine zusätzliche Dichte ist nur als
abgeleiteter/Validierungswert erlaubt. Andere EOS-Koordinatenwahlen und
Frame-Transformationen werden nicht stillschweigend ergänzt.

Domänen sind exakte Knotenlisten mit optionalen `StateNode`-Koordinaten.
Unbekannte Knoten, falsche Phase und falsche Koordinaten sind Fehler;
ein Knotenname ohne Koordinaten ist `NODE_COORDINATES_UNVERIFIED`.
`BranchRequirements` kann benötigte Elemente/Spezies ausdrücklich fordern;
ohne diese Angaben wird keine bestimmte Fe/Ni/O/Si-Coverage behauptet.

Sieben separate Gates: `thermodynamics_ready`, `composition_ready`,
`charge_state_ready`, `transport_ready`, `screening_input_ready`,
`capture_ready`, `charge_matching_ready`.
Quellenbytes werden nur mit dem ausdrücklich übergebenen `LocalSourceStore`
verifiziert; ohne ihn bleibt `SOURCE_BYTES_UNVERIFIED` offen.
`TEST_FIXTURE` blockiert wissenschaftliche Readiness auch bei korrekter Algebra.

Der Transportvertrag unterstützt den isothermen reduzierten Onsager-Zweig
mit Teilchenfluss und `grad(mu)`: `C` hat Größe `S x (S-1)`, vollen Spaltenrang
und exakt `m^T C = 0`; Flüsse erfüllen exakt `sum(m_s*j_s)=0`.
`L_reduced` muss im skalierten Raum symmetrisch und strikt positiv sein.
Keine Eigenwert-Clips. Nicht aufgelöste Nullmoden werden abgewiesen.
Andere Force-/Fluxkonventionen brauchen einen expliziten späteren Adapter.
Nichtisotherme Wärme-Kreuzblöcke und dynamische Screeningverträge bleiben offen.

Thermo- und Ionisationsblöcke prüfen Felder, Einheiten, Achsen, Populationen
und referenzierte Qualitätsnachweise. Sie berechnen keine EOS, Reaktionsraten
oder thermodynamischen Identitäten aus Experimenten neu.
`Q_bullet` und `Q_m` sind getrennte Felder. Ein expliziter `MatchingRecord`
dokumentiert höchstens eine vorliegende Relation und zertifiziert sie nicht.
`assess_readiness` lässt `A35.RELEASE` wegen fehlender physischer Innenoperatoren
gesperrt. Materialdaten erzeugen keine Capture- oder SL-Rate.

### Ledger und Vorzeichen

Reservoirs: `outer_material`, `transition_region`, `seed`, `radiation`, `bath`,
`external`. `source -> target` bucht beim Sender `-sign * quantity`, beim
Empfänger `+sign * quantity`. Ladungswerte dürfen negativ sein. Materielle
Beträge sind positiv; Richtungsumkehr erfolgt über `sign=-1`.

`TransferLedger.postings` erzeugt immer beide Seiten. `audit(postings=...)`
prüft auch fremd übergebene Buchungen gegen die erwarteten Einträge und
berechnet Massen-/Ladungs-/Energieresiduen exakt. Selbst eine global ausgeglichene,
aber falsch zugeordnete Buchung scheitert. Externe Beiträge werden getrennt
ausgewiesen und benötigen `external=True`.

Ein Ledger enthält entweder Beträge oder Raten; niemals beides. Es besitzt
einen Frame, eine Domäne und für Energie eine gemeinsame Bilanzkonvention.
`balance(reservoir, observable)` liefert einen semantisch bezeichneten
`Balance` mit exaktem `Fraction`-Wert, Einheit, Frame und Definition.
`change` ist der niedrigere Algebra-Zugriff; bei `mode=RATE` bedeutet er eine
Speicheränderungsrate, keine integrierte gespeicherte Menge.

`species_transfer` leitet für einen Speziesvorgang **gemeinsam** Masse und Ladung
aus Teilchenzahl/-rate, Buchhaltungsmasse und Ladungszahl ab. Beide Kanäle
müssen vorhanden und konsistent sein. Energie wird nicht aus `m*c²` erfunden.
`species_change`/`element_change` halten den Materietransport nach Spezies/
Element getrennt; Reaktionen und Kernumwandlungen sind nicht implementiert.

Mehrere Spezies dürfen disjunkte Teile eines Ereignisses sein. Ein zusätzlicher
aggregierter `I_plasma`-Kanal an derselben Grenze wird hart abgewiesen.
`event_id` und `double_count_group` müssen tatsächliche physische Identität
abbilden: Wer **beides** für denselben Vorgang falsch umbenennt, erzeugt eine
semantische Täuschung, die aus den Zahlen allein nicht erkennbar ist.
Getrennte äußere/innere Grenzflächen bleiben zulässige separate Transfers.

`require_stationary_transition()` verlangt explizit verschwindende innere
Massen-, Ladungs-, Energie- und Speziesspeicheränderungen. Standardmäßig ist
Speicherung erlaubt. `validate_full_mixture_boundary` prüft algebraisch
`sum(m_s F_s) = -area*rho*u` mit expliziter Fläche, positivem Einwärtsfluss
und nach außen positivem `u`. Kein Zeitintegrator und keine Flussberechnung.

## Numerische Grenzen und Review

Skalare Constraints und Bilanzsummen benutzen exakte rationale Arithmetik:
**keine Bilanz-Toleranz**. Für Matrixprüfungen allein gilt nach Normierung auf
den größten Absolutwert `atol=1e-12`, `rtol=1e-10`; Begründung und zentrale
Konstanten stehen in `common/numerics.py`. Diese Schwelle beschreibt einen
konservativen binary64-Prüfbereich, kein empirisches Fehlerbudget.

Vollständiger Phasenbericht: `../A35_FOUNDATION_IMPLEMENTATION_REPORT.md`.
Nach diesem Slice ist **Review erforderlich; P05–P10 sind nicht freigegeben**.
