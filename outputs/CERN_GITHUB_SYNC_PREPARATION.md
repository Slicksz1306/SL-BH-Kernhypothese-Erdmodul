# CERN/A35-Synchronisation: Vorbereitung

Prüfdatum: 18.10.2026. Die Lieferkopie wurde in einem separaten Worktree auf
dem bestätigten Remote-Stand geprüft. Der Forschungs-Checkout und `main` wurden
nicht verändert.

## Geprüfte Checkouts

- Die Lieferkopie `C:\Users\xfire\Documents\Codex\2026-10-07\files-pasted-by-the-user-sl`
  und `C:\Users\xfire\Documents\Codex` sind keine Git-Repositories.
- Ein vorhandener Forschungscheckout befindet sich unter
  `C:\Users\xfire\Documents\Codex\2026-08-29\github-plugin-github-openai-curated-remote-3\work\SL-BH-Kernhypothese-Erdmodul`.
- Der Integrations-Worktree befindet sich unter
  `C:\Users\xfire\Documents\Codex\2026-10-18\sl-bh-cern-integration` auf
  Branch `integration/cern-a35-partial-20261018`.
- Eine direkte, read-only Remote-Ref-Prüfung bestätigte `origin/main` und den
  gleichnamigen Remote-Integrationsbranch bei `9670f0b280c593077d1469b35ef4e90a6fd9a8c1`.
- Die fünf lokalen Vorab-Commits ab `630d696` bis `c5074b7` wurden aus dem
  Integrationsbranch entfernt: Sie betreffen 61 allgemeine Forschungs-/A35-Dateien
  und gehören nicht in diesen begrenzten CERN/A35-PR.
- Der Branch enthält nun genau einen Liefercommit auf dieser Remote-Basis:
  `9b8ec54` (CERN/A35-Lieferung). Der ursprüngliche Integrationsstand ist unter
  dem lokalen Sicherungsref `backup/integration-pre-remote-base-20261018` erhalten.
- Im Forschungscheckout gibt es bereits lokale Änderungen und nicht getrackte
  Dateien. Sie sind fremder, noch nicht abgeschlossener Arbeitsstand und wurden
  nicht für diese Lieferung verwendet, verändert oder aufgenommen. Git meldete
  außerdem einige nicht lesbare temporäre Ordner; sie wurden weder untersucht
  noch geändert.
- Die CERN-Lieferkopie liegt außerhalb dieses Checkouts und ist nicht Teil seiner
  aktuellen Git-Dateiliste.

## Sichere Vorbereitung

Die zu synchronisierende Lieferung ist auf diesen Ordner begrenzt:
`outputs/a35_cern_layer/` plus die zugehörigen Abschlussberichte in `outputs/`.
Der Snapshot bleibt `FROZEN_PARTIAL`; sein ursprünglicher Manifesthash ist
`bbc4b1580a3556fc2c4e7adce7c3429127bbe86d7e05f5d118032f221d8b0190`.
Der Code-/Dokumentationshashkatalog ist `CERN_CODE_MANIFEST.json`.

Der Branch ist für einen sicheren Push vorbereitet; `main` wurde nicht direkt
verändert oder gemergt. Der Remote-Integrationsbranch zeigt weiterhin auf
`9670f0b...`; der Liefercommit wurde lokal noch nicht veröffentlicht.

Vor dem Push sind die noch offenen Gates (insbesondere die vollständige
jsonschema-Testumgebung) erfolgreich auszuführen. Danach darf ausschließlich
dieser Liefercommit auf den separaten Remote-Branch gepusht werden; anschließend
sind Remote-Commit und PR-Diff nochmals zu lesen. Ein direkter Push auf `main`
oder ein Merge ist ausgeschlossen.
