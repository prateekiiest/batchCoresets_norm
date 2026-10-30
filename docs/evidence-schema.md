# Evidence schema and interpretation

Sanitized periodic manifests use schema_version 2 and are described by schemas/reviewer-manifest-v2.schema.json.

## Manifest fields

| Field | Meaning |
|---|---|
| schema_version | Manifest schema version (2). |
| created_at_utc | Collector-reported UTC creation time; independently trusted only if the matching timestamp proof verifies. |
| collector_version | Collector implementation version label. |
| git_head | Git HEAD observed locally when the manifest was made. |
| previous_manifest_sha256 | SHA-256 of the previous manifest's exact file bytes, or 64 zeroes for the first manifest. |
| logs | SHA-256 and byte size of available local event logs; log contents are not included. |
| tracked_artifacts_by_extension | Path-free lists of SHA-256 hashes and byte sizes for tracked files, grouped by extension. |
| manifest_payload_sha256 | SHA-256 of canonical JSON for all other fields (UTF-8, sorted keys, compact separators, no trailing newline). |
| note | Interpretation warning. |

The previous-manifest chain uses SHA-256 of the previous manifest's exact serialized bytes, including its final newline. The payload digest is calculated before adding manifest_payload_sha256.

## Event records

The local macOS event log is JSON Lines. Each event includes schema, observed_at_utc, event_id, event_type, evidence_class, event-specific metadata, previous_event_hash, and event_hash. Raw logs remain local by default.

## External timestamp proofs

An .ots file commits to the exact bytes of its corresponding manifest. A proof is meaningful only when the reviewer has both manifest and proof and successfully verifies it. A timestamp request, mere proof-file presence, or pending calendar operation is not proof of a completed Bitcoin timestamp.

Hash consistency is not completeness. A local timestamp is not an external timestamp. A Git author field is not identity verification. Missing events are not evidence of non-use. Artifact hashes establish byte equality only when candidate artifacts are independently hashed and compared.
