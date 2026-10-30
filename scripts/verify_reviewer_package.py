#!/usr/bin/env python3
"""Offline verifier for a sanitized research-provenance reviewer package."""
import argparse, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ZERO = "0" * 64

def canonical_hash(value):
    payload = dict(value)
    payload.pop("manifest_payload_sha256", None)
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("package", help="Reviewer package directory")
    p.add_argument("--verify-timestamps", action="store_true", help="Run ots verify for included proofs; may require network/header data")
    a = p.parse_args()
    root = Path(a.package).resolve()
    md = root / "manifests"
    if not md.is_dir():
        p.error("package must contain a manifests directory")
    manifests = sorted(md.glob("manifest-*.json"))
    if not manifests:
        print("FAIL: no manifests found")
        return 1
    errors, warnings, previous = [], [], ZERO
    for path in manifests:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{path.name}: invalid JSON ({type(exc).__name__})")
            continue
        if value.get("manifest_payload_sha256") != canonical_hash(value):
            errors.append(f"{path.name}: payload digest mismatch")
        if value.get("previous_manifest_sha256", ZERO) != previous:
            errors.append(f"{path.name}: previous-manifest link mismatch")
        previous = hashlib.sha256(path.read_bytes()).hexdigest()
        proof = path.with_suffix(path.suffix + ".ots")
        if not proof.exists():
            warnings.append(f"{path.name}: no external timestamp proof supplied")
        elif a.verify_timestamps:
            ots = shutil.which("ots")
            if not ots:
                warnings.append(f"{proof.name}: ots client unavailable")
            else:
                result = subprocess.run([ots, "verify", str(proof)], capture_output=True, text=True)
                if result.returncode:
                    warnings.append(f"{proof.name}: verification not successful: {(result.stderr or result.stdout).strip()}")
                else:
                    print(f"TIMESTAMP PASS: {proof.name}")
    index = root / "package-index.json"
    if index.exists():
        try:
            data = json.loads(index.read_text(encoding="utf-8"))
            expected = data.get("manifest_files", [])
            if expected and expected != [x.name for x in manifests]:
                errors.append("package index manifest inventory mismatch")
            proof_inventory = data.get("timestamp_proofs", {})
            for name, metadata in proof_inventory.items():
                proof = md / name
                if not proof.is_file():
                    errors.append(f"indexed timestamp proof missing: {name}")
                elif hashlib.sha256(proof.read_bytes()).hexdigest() != metadata.get("sha256"):
                    errors.append(f"timestamp proof digest mismatch: {name}")
        except Exception:
            errors.append("package index is invalid JSON")
    for x in errors: print("FAIL:", x)
    for x in warnings: print("WARNING:", x)
    if errors:
        print(f"RESULT: FAIL ({len(errors)} errors, {len(warnings)} warnings)")
        return 1
    print(f"RESULT: PASS (offline manifest integrity; {len(manifests)} manifests, {len(warnings)} warnings)")
    if not a.verify_timestamps:
        print("Timestamp proofs were not checked. Re-run with --verify-timestamps when ots is installed.")
    print("PASS does not establish completeness, authorship, or absence of AI use.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
