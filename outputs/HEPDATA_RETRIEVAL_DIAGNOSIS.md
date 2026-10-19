# HEPData: kontrollierte Fehlerdiagnose

Stand: 18.10.2026. Umfang: je **ein** neuer GET auf die beiden ursprünglich
fehlgeschlagenen JSON-Endpunkte sowie je ein HEAD auf die reguläre Archivroute.
Keine Authentifizierung, keine Browser-Challenge-
Automatisierung, kein Proxy, keine Umgehung der Zugriffskontrolle.

## Beleglage vor der Wiederholung

Die ursprünglichen Belege vom 18.10.2026, etwa 10:19 UTC, nennen `HTTPError`,
aber keinen HTTP-Status, Antwortheader oder Antwortkörper. Diese Aufzeichnung
war zur Ursachenbestimmung unzureichend. Sie bleibt unverändert erhalten.
Die konkrete Ursache der damaligen beiden Versuche ist rückwirkend **OPEN**;
die neue Antwort darf nicht als nachträglich gemessene alte Antwort ausgegeben werden.

## Ergebnisse der Wiederholung

| Merkmal | ATLAS EXOT-2024-32 | CMS EXO-24-028 |
|---|---|---|
| Exakter Endpunkt | `https://www.hepdata.net/record/ins3147718?format=json` | `https://www.hepdata.net/record/165871?format=json` |
| Abruf UTC | 2026-10-18T19:43:19.754347+00:00 | 2026-10-18T19:43:19.957581+00:00 |
| HTTP | 403 Forbidden | 403 Forbidden |
| Server-Header | cloudflare | cloudflare |
| Content-Type | text/html; charset=UTF-8 | text/html; charset=UTF-8 |
| Antwort | HTML-Prüfseite, Titel „Just a moment...“, Cloudflare-Challenge-Verweise | HTML-Prüfseite, Titel „Just a moment...“, Cloudflare-Challenge-Verweise |
| Antwort abgeschnitten? | nein | nein |
| Ergebnis | SOURCE_UNAVAILABLE | SOURCE_UNAVAILABLE |

Die protokollierte End-URL entspricht jeweils dem angefragten Endpunkt. Der
Origin-Datensatz wurde nicht erreicht bzw. nicht als JSON geliefert. Bestätigt
ist eine Ablehnung durch die vorgelagerte Cloudflare-Prüfschicht. Welche interne
Regel oder welche Eigenschaft dieses Clients sie auslöste, ist nicht bekannt.

## Prüfung offiziell dokumentierter Exportwege

Das offizielle HEPData-Projekt dokumentiert `hepdata-cli` für Suche und Download
von Datensätzen in JSON und weiteren regulären Formaten. Die Records-Dokumentation
beschreibt Datentabellen und JSON-Ressourcen. Quellen:
[HEPData-CLI](https://github.com/HEPData/hepdata-cli),
[HEPData Records API](https://hepdata.readthedocs.io/en/latest/modules/records.html).
Die veröffentlichte Originalarchivroute `/download/submission/ins<id>/original`
wurde für beide INSPIRE-IDs je einmal regulär mit HEAD geprüft:

| INSPIRE-ID | Angefragter Export | Antwort |
|---|---|---|
| `ins3147718` | `https://www.hepdata.net/download/submission/ins3147718/original` | **403 Forbidden**, `text/html; charset=UTF-8`, `cloudflare` |
| `ins3144373` | `https://www.hepdata.net/download/submission/ins3144373/original` | **403 Forbidden**, `text/html; charset=UTF-8`, `cloudflare` |

HEAD überträgt keinen Datenkörper. Diese zusätzlichen Prüfungen belegen Status,
Inhaltstyp und Server, aber liefern keinen zweiten JSON-Body. Der offizielle
Exportmechanismus existiert; über diese spezifischen Endpunkte wurde weiterhin
kein nutzbarer Export erreicht. Eine gezielte öffentliche Suche fand keinen
alternativen exportierten Eintrag zu diesen Analysen. Das beweist nicht, dass
HEPData die Records nicht besitzt.

Die gehashte offizielle CMS-Ergebnisseite im Snapshot wurde auf aktive
CSV-Hyperlinks geprüft. Für die untersuchten Figuren ist die Zahl aktiver
CSV-Links **null**; entsprechende Textstellen sind auskommentiertes HTML.
Verlinkt sind Bild-/PDF-Darstellungen. Es wurde keine Abbildung digitalisiert.

Die Antwort belegt für diese Versuche keinen DNS-/TLS-Ausfall, keinen Timeout,
keinen HTTP 429 und keinen HTTP 5xx. Ein falscher oder nicht existierender
Origin-Record lässt sich durch die vorgeschaltete 403-Seite weder bestätigen
noch ausschließen. Die Kennungen sind anhand der Quellen nachvollziehbar, aber
die tatsächlichen HEPData-Record-/Tabellenversionen bleiben unbestätigt.

CMS nennt außerdem den offiziellen Link `ins3144373` und die Paper-DOI
`10.17182/hepdata.165871`. Bereits vorhandene Abrufbelege dafür verzeichnen
ebenfalls `HTTPError`, jedoch ohne Status/Body. In dieser Wiederholungsprüfung
wurden diese zusätzlichen Endpunkte **nicht nochmals** abgefragt.

## Hashes und Ablage

Alle Pfade unten relativ zu
`a35_cern_layer/data/cern_lhc_snapshot_2026_10_07/`:

| Objekt | SHA-256 / inhaltsadressierter Name |
|---|---|
| ATLAS-Antwortkörper | `b4db6bccbf672f5a11f0606ec7da754762d74fae9ccad564d4a6d180a83992e7` |
| CMS-Antwortkörper | `a7b4e8e75aaf8cf20c40511ebb5177ce7363172afcc7d4fb882ef2af74a8d4c0` |
| ATLAS-Diagnosebeleg | `fd7b52a9b0c6fc4c24354dbabbe230b557924af670dc7ff6365cbeb57a7eb6ac` |
| CMS-Diagnosebeleg | `25fd40f1eb082c220cc4c7ed02788061ff5d0625fbcce370ebe202a037efb0c9` |

Antwortkörper: `raw/<SHA-256>`.
Belege: `receipts/atlas_hepdata_recheck/<SHA-256>.json` beziehungsweise
`receipts/cms_hepdata_recheck/<SHA-256>.json`. Sie enthalten die Antwortbytes
zusätzlich Base64-kodiert, ihren Hash, tatsächliche Abrufzeit und ausgewählte
Header. Sie sind **Fehlerbelege**, keine Collider-Datenquelle oder HEPData-Tabelle.

## Behandlung und Bewertung

- **PASS – Diagnosebelege:** Status, Inhaltstyp, Antwortbytes und Hash erhalten;
  alte Belege nicht überschrieben.
- **PASS – Fehlerbehandlung:** Drei Regressionen für 403, 429/Retry-After und
  Timeout wurden zunächst fehlschlagend und nach dem kleinen Patch erfolgreich getestet.
  Eine zusätzliche Review-Regression für IncompleteRead sichert den bereits
  bekannten HTTP-Status und eindeutig unvollständige Teilbytes; ebenfalls RED→GREEN.
- **FAIL – erfolgreicher Datenabruf:** Beide Wiederholungen liefern weiterhin kein JSON.
- **OPEN – HEPData-Validierung:** Version, Tabellen-ID, Vollständigkeit, Einheiten,
  Benchmarkbindung und Paper-Crosscheck können nicht bestätigt werden.
- **OPEN – historische Fehlerursache und konkrete Cloudflare-Regel:** Aus den
  verfügbaren alten bzw. neuen Belegen nicht eindeutig bestimmbar.
- **PASS – Suche nach offiziellen Exporten:** HEPData dokumentiert reguläre
  Formate; die zwei spezifischen Archiv-HEADs liefern ebenfalls 403.
- **OPEN – alternative Datentabelle:** Für diese Analysen wurde kein über einen
  alternativen offiziellen Export erreichbarer Zahlenbestand verifiziert.

Nächster zulässiger Schritt wäre ein regulärer, vom Nutzer bereitgestellter
HEPData-Export oder ein später wieder erlaubter offizieller Abruf. Ein Export
müsste denselben Herkunfts-, Versions-, Hash-, Tabellen- und Crosscheck-Gates
unterzogen werden. Bis dahin keine Ersatzwerte und kein FROZEN_COMPLETE.
