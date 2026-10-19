# CERN/A35 Manifest-Reconciliation

The historical CERN_CODE_MANIFEST.json is retained unchanged. This integration
uses CERN_CODE_MANIFEST_INTEGRATION.json for the same 64 delivery files.

The ten files affected only by Git EOL normalization are protected by targeted
repository-local -text rules in outputs/a35_cern_layer/.gitattributes. Their
published CRLF bytes therefore remain identical in the worktree, index, and
commit tree.

Two files intentionally changed in commit e2847f0ab72360b0199044c66389bf3557c72e60:

- outputs/a35_cern_layer/dependency-lock.txt: clarified Foundation runtime
  notes and documented the separate hash-pinned collider dependency lock.
- outputs/CERN_GITHUB_SYNC_PREPARATION.md: updated the report from pre-integration
  preparation to the verified separate integration worktree and branch state.

The new manifest records the byte hashes of the corrected integration tree. It
does not hash itself, avoiding a circular dependency. No P01-P04 files, raw
evidence, or frozen snapshot files were changed.
