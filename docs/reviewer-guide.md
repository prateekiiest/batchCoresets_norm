# Reviewer guide: sanitized research provenance package

## LaunchAgent and Cold Turkey context

The local macOS event log may include collector-start, periodic self-reported heartbeat, and caught-error records. These are collector self-reports, not an independent monitor of `launchd`; a missing heartbeat marks an observation gap whose cause is unknown. The periodic manifest hashes available LaunchAgent stdout/stderr logs without including their contents.

If Cold Turkey Blocker Statistics is enabled, export the visible statistics from its Statistics tab and, if you want the export's exact bytes represented in a later manifest, place a copy at `.writing-provenance/cold-turkey-statistics-export.json`. The collector records only that file's SHA-256 and byte size in the sanitized manifest; it does not parse or publish the export. Keep the original export private because it may contain website, application, or window-title details. Cold Turkey's own guide says statistics are stored locally and that visible statistics can be exported. A hash establishes the identity of the supplied export bytes, not that the statistics are complete or that a block was continuously enforced.

The sanitized package is produced under public-evidence/reviewer-package/.

## Contents

- manifests/manifest-*.json: periodic path-redacted manifests. Each contains a UTC observation time, locally observed Git HEAD, hashes and sizes of available event logs, and tracked-artifact hashes grouped by extension. Filenames and directory paths are omitted.
- Matching .ots files: OpenTimestamps proofs, when supplied by the collector.
- package-index.json: inventory of included manifests.
- README.md: verification instructions and scope.

The package excludes raw event logs, snapshots, prompts, AI responses, document contents, usernames, absolute paths, and credentials. Review the separate research-evidence-report.md and research-evidence-audit.json before sharing them.

## Verify offline

Use Python 3.9+ and the standard library:

    python3 scripts/verify_reviewer_package.py public-evidence/reviewer-package

The verifier checks JSON parsing, canonical manifest SHA-256 digests, previous-manifest links, and package inventory. These checks run offline.

PASS means the supplied manifests are internally consistent with their declared hashes and links. It does not prove completeness, continuous collection, or that a local user did not alter records before anchoring.

## Verify external timestamps

Install the OpenTimestamps client:

    python3 -m pip install opentimestamps-client

Then run:

    python3 scripts/verify_reviewer_package.py public-evidence/reviewer-package --verify-timestamps

This invokes ots verify for included proofs. Bitcoin timestamp verification may need network access or locally available Bitcoin header data, depending on proof state and client version. A pending proof is not a completed Bitcoin anchoring. If the package-index proof is absent, the reviewer cannot rule out that the package omits later manifests. Do not claim an externally verified timestamp until ots verify reports success. The package verifier does not upgrade proofs or contact timestamp calendars.

A researcher can separately upgrade a pending proof while online with:

    ots upgrade path/to/manifest.json.ots

Then regenerate the reviewer package. Keep each manifest JSON and its matching .ots file together: the proof commits to the exact manifest bytes.

## Evidence categories

- Observed: a configured collector or editor integration emitted a record.
- Integrity checked: supplied bytes match recorded SHA-256 digests and chain links.
- Externally timestamp verified: OpenTimestamps successfully verifies a proof for the exact manifest bytes.
- Declared: information supplied by the researcher, not independently observed.
- Not observed: no corresponding event appears in available logs. This is not evidence that activity did not occur.
- Unknown/unavailable: instrumentation or records were absent, disabled, incomplete, or failed verification.

## AI-use interpretation

Cursor hook records can document supported events emitted by Cursor when hooks were installed and enabled. They do not quantify generated text, establish that generated text entered the final paper, or cover other AI tools. A missing Cursor log, or no matching event in a present log, cannot establish non-use.

Researchers should separately disclose AI tools and assistance according to venue and institutional policy. The toolkit's own development used AI assistance; see the repository README disclosure.

## Privacy and limitations

Artifact paths are omitted. Hashes can be compared against candidate files, but a hash alone does not reveal which manuscript or source file it represents. The package does not provide a filename-to-hash mapping.

The collector is a user-level process on a machine controlled by the researcher. Local records can be deleted or altered before external timestamping. Polling can miss intermediate edits that occur and revert between scans. The tool does not observe thoughts, all keystrokes, all browser activity, every external AI service, other devices, or unmonitored folders. Git commit identity is not proof of human authorship.

This is supporting provenance evidence, not forensic surveillance, authorship certification, or proof that AI was never used.
