#!/usr/bin/env python3
"""
Phase 6 verify gate for the O-RAN Agent Harness public repo.

Runs 10 deterministic checks against the repository contents and exits 0 if
all pass, non-zero if any fail. Check 9 (JSON Schema validation) is optional
and auto-skipped if `jsonschema` is not installed. Check 10 (runtime walker
end-to-end) requires PyYAML and runs the walker as a subprocess. Designed for
any reviewer to run after cloning:

    python3 scripts/verify.py

Checks:
  1. Citation headers on every authored YAML and JSON in harness/ and scenarios/
  2. JSON parse on every .json in the public tree
  3. YAML parse on every .yaml and .yml in the public tree
  4. harness/conformance.md bidirectional completeness (no stale rows, no missing files)
  5. Em dash (U+2014) audit across the public tree, must be zero
  6. Leakage guard: git ls-files must contain no .local/, python_demo/, .env; .pdf
     allowed only under draft_papers/ (scientifically authored papers)
  7. README structure: 80-400 lines, three goals in the lede
  8. File counts: harness/ has 20 files, omc-skills/o-ran/ has 6 markdown files
  9. Schema validation: scenario data validates against declared harness/schemas/ (optional, requires jsonschema)

Dependencies:
  - Python 3.8 or later (uses pathlib, f-strings)
  - PyYAML (pip install pyyaml)
  - git (must be runnable from the repo root for the leakage check)
  - jsonschema (pip install jsonschema) for check 9; if missing, check 9 is skipped with a warning

Excluded from the public tree scans: .git, .local, .omc, python_demo.
"""

import json
import os
import re
import subprocess  # noqa: F401  used both in check 6 (no_leakage) and check 10 (walker_e2e)
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parent.parent
EM_DASH = chr(0x2014)
CHECK_PATHS = ["harness", "scenarios"]
PUBLIC_TREE_EXCLUDES = {".git", ".local", ".omc", ".omx", "python_demo", "node_modules", "dist", ".vite", "__pycache__"}

results = []


def record(name, passed, detail=""):
    results.append((name, passed, detail))
    status = "PASS" if passed else "FAIL"
    suffix = f" ({detail})" if detail else ""
    print(f"  {status}: {name}{suffix}")


def is_in_public_tree(p):
    return not any(part in PUBLIC_TREE_EXCLUDES for part in p.parts)


def main():
    print("=" * 72)
    print("Phase 6 verify gate: O-RAN Agent Harness")
    print(f"Repo root: {REPO_ROOT}")
    print("=" * 72)

    # 1. Citation headers
    print("\n--- citation headers ---")
    missing = []
    for d in CHECK_PATHS:
        for p in (REPO_ROOT / d).rglob("*"):
            if not p.is_file():
                continue
            if p.suffix not in {".yaml", ".yml", ".json"}:
                continue
            if p.name == "conformance.md":
                continue
            try:
                content = p.read_text(encoding="utf-8")
            except Exception:
                continue
            if p.suffix in {".yaml", ".yml"}:
                head = "\n".join(content.split("\n")[:5])
                ok = "Conforms to:" in head and "Bibliography ref:" in head
            else:
                try:
                    ok = "_conforms_to" in json.loads(content)
                except Exception:
                    ok = False
            if not ok:
                missing.append(str(p.relative_to(REPO_ROOT)))
    detail = f"{len(missing)} missing"
    if missing:
        detail += ": " + ", ".join(missing[:5]) + ("..." if len(missing) > 5 else "")
    record("citation_headers", not missing, detail)

    # 2. JSON parse
    print("\n--- JSON parse ---")
    fails = []
    for p in REPO_ROOT.rglob("*.json"):
        if not is_in_public_tree(p.relative_to(REPO_ROOT)):
            continue
        try:
            json.loads(p.read_text())
        except Exception as e:
            fails.append(f"{p.relative_to(REPO_ROOT)}: {str(e)[:60]}")
    record("json_parse", not fails, f"{len(fails)} failures")

    # 3. YAML parse
    print("\n--- YAML parse ---")
    fails = []
    for pattern in ["*.yaml", "*.yml"]:
        for p in REPO_ROOT.rglob(pattern):
            if not is_in_public_tree(p.relative_to(REPO_ROOT)):
                continue
            try:
                list(yaml.safe_load_all(p.read_text()))
            except Exception as e:
                fails.append(f"{p.relative_to(REPO_ROOT)}: {str(e)[:60]}")
    record("yaml_parse", not fails, f"{len(fails)} failures")

    # 4. conformance.md bidirectional
    print("\n--- conformance.md bidirectional ---")
    conf_path = REPO_ROOT / "harness/conformance.md"
    if not conf_path.exists():
        record("conformance_complete", False, "harness/conformance.md missing")
    else:
        conf = conf_path.read_text()
        row_pattern = r"\| (harness/[^\s|]+\.(?:yaml|yml|json|md)|scenarios/[^\s|]+) "
        rows = re.findall(row_pattern, conf)
        expected = set()
        for d in CHECK_PATHS:
            for p in (REPO_ROOT / d).rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix in {".yaml", ".yml", ".json", ".md"}:
                    expected.add(str(p.relative_to(REPO_ROOT)))
        listed = set(rows)
        missing_from_table = expected - listed
        stale_rows = listed - expected
        ok = not missing_from_table and not stale_rows
        detail = (
            f"{len(rows)} rows, "
            f"{len(missing_from_table)} missing from table, "
            f"{len(stale_rows)} stale"
        )
        record("conformance_complete", ok, detail)

    # 5. Em dash audit
    print("\n--- em dash audit ---")
    hits = []
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file():
            continue
        if not is_in_public_tree(p.relative_to(REPO_ROOT)):
            continue
        try:
            if EM_DASH in p.read_text(encoding="utf-8"):
                hits.append(str(p.relative_to(REPO_ROOT)))
        except Exception:
            pass
    record("em_dashes", not hits, f"{len(hits)} files" + (f": {hits}" if hits else ""))

    # 6. Leakage guard
    print("\n--- leakage guard (git ls-files) ---")
    try:
        tracked = subprocess.check_output(
            ["git", "ls-files"], cwd=str(REPO_ROOT)
        ).decode().split()
        # PDFs under draft_papers/ are intentional: scientifically authored papers
        # by the harness author. The .pdf rule otherwise defends against
        # partner-confidential PDFs leaking elsewhere in the tree.
        pattern_forbidden = re.compile(r"\.local/|python_demo/|\.env$")
        pattern_pdf = re.compile(r"\.pdf$")
        leaks = []
        for t in tracked:
            if pattern_forbidden.search(t):
                leaks.append(t)
            elif pattern_pdf.search(t) and not t.startswith("draft_papers/"):
                leaks.append(t)
        record("no_leakage", not leaks, f"{len(leaks)} leaks" + (f": {leaks}" if leaks else ""))
    except Exception as e:
        record("no_leakage", False, f"git command failed: {e}")

    # 7. README structure
    print("\n--- README structure ---")
    readme = (REPO_ROOT / "README.md").read_text()
    line_count = readme.count("\n")
    top_lede = "\n".join(readme.split("\n")[:90])
    g1 = "Here is my presentation" in top_lede
    g2 = "Here is the example work" in top_lede
    g3 = "Here is where I actually test" in top_lede
    ok = 80 <= line_count <= 400 and g1 and g2 and g3
    record(
        "readme_structure",
        ok,
        f"lines={line_count}, three goals present={g1 and g2 and g3}",
    )

    # 8. File counts (exclude __pycache__ and *.pyc which appear after running the walker)
    print("\n--- file counts ---")
    harness_count = sum(
        1
        for p in (REPO_ROOT / "harness").rglob("*")
        if p.is_file()
        and "__pycache__" not in p.parts
        and p.suffix != ".pyc"
    )
    omc_count = sum(1 for p in (REPO_ROOT / "omc-skills/o-ran").glob("*.md"))
    ok = harness_count == 26 and omc_count == 6
    record(
        "file_counts",
        ok,
        f"harness={harness_count}/26, omc-skills md={omc_count}/6",
    )

    # 9. Schema validation (optional, requires jsonschema)
    print("\n--- schema validation (scenarios vs harness/schemas/) ---")
    try:
        import jsonschema
    except ImportError:
        print("  SKIP: jsonschema not installed (pip install jsonschema). Check 9 not run.")
    else:
        rp_schema = json.loads((REPO_ROOT / "harness/schemas/RemediationProposal.json").read_text())
        fp_schema = json.loads((REPO_ROOT / "harness/schemas/FaultPayload.json").read_text())
        rev_schema = json.loads((REPO_ROOT / "harness/schemas/ReversibilityProfile.json").read_text())
        fails = []
        scenario_ids = [
            "A_fw_lldp_agent",
            "A_prime_ice_driver",
            "D_phc_drift_hw_only",
            "E_nic_firmware_update",
            "E_with_smo_reject",
        ]
        # Validate fault payloads against FaultPayload schema (all 5 scenarios)
        for sid in scenario_ids:
            path = f"scenarios/{sid}/fault_payload.json"
            data = json.loads((REPO_ROOT / path).read_text())
            data_no_meta = {k: v for k, v in data.items() if k != "_conforms_to"}
            try:
                jsonschema.validate(data_no_meta, fp_schema)
            except jsonschema.ValidationError as e:
                fails.append(f"{path}: {e.message}")
        # Validate audit_event.event.remediation against RemediationProposal schema (all 5)
        for sid in scenario_ids:
            path = f"scenarios/{sid}/audit_event.json"
            data = json.loads((REPO_ROOT / path).read_text())
            remediation = data["event"]["remediation"]
            # ReversibilityProfile is a harness-unique extension on RemediationProposal
            rem_for_validation = {k: v for k, v in remediation.items() if k != "reversibility_profile"}
            try:
                jsonschema.validate(rem_for_validation, rp_schema)
            except jsonschema.ValidationError as e:
                fails.append(f"{path}: {e.message}")
            # Validate the reversibility_profile portion against ReversibilityProfile schema
            if "reversibility_profile" in remediation:
                try:
                    jsonschema.validate(remediation["reversibility_profile"], rev_schema)
                except jsonschema.ValidationError as e:
                    fails.append(f"{path} reversibility_profile: {e.message}")
        record("schema_validation", not fails, f"{len(fails)} failures" + (": " + "; ".join(fails) if fails else ""))

    # 10. Runtime walker end-to-end (requires PyYAML, already a dep)
    print("\n--- runtime walker end-to-end (scenarios vs committed audit_event.json) ---")
    walker_fails = []
    material_fields = [
        "targetLayer",
        "taxonomyMatch",
        "actionType",
        "ocloudInternalPath",
        "actionPayloadRef",
        "dryRun",
        "requiresHumanApproval",
    ]
    for scenario in [
        "A_fw_lldp_agent",
        "A_prime_ice_driver",
        "D_phc_drift_hw_only",
        "E_nic_firmware_update",
        "E_with_smo_reject",
    ]:
        fault_path = REPO_ROOT / f"scenarios/{scenario}/fault_payload.json"
        expected_path = REPO_ROOT / f"scenarios/{scenario}/audit_event.json"
        try:
            result = subprocess.run(
                ["python3", "-m", "harness.runtime.walker", str(fault_path)],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                check=True,
                timeout=30,
            )
            actual = json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            walker_fails.append(f"{scenario}: walker exited {e.returncode}: {e.stderr[:120]}")
            continue
        except Exception as e:
            walker_fails.append(f"{scenario}: walker error: {e}")
            continue

        expected = json.loads(expected_path.read_text())
        for field in material_fields:
            a = actual["event"]["remediation"].get(field)
            e = expected["event"]["remediation"].get(field)
            if a != e:
                walker_fails.append(f"{scenario}: {field} actual={a!r} expected={e!r}")
        a_conf = actual["event"]["remediation"].get("reversibility_profile", {}).get(
            "confidence_in_reversibility"
        )
        e_conf = expected["event"]["remediation"].get("reversibility_profile", {}).get(
            "confidence_in_reversibility"
        )
        if a_conf != e_conf:
            walker_fails.append(
                f"{scenario}: reversibility_profile.confidence_in_reversibility "
                f"actual={a_conf!r} expected={e_conf!r}"
            )
    record(
        "walker_e2e",
        not walker_fails,
        f"{len(walker_fails)} failures"
        + (": " + "; ".join(walker_fails) if walker_fails else ""),
    )

    # Summary
    print()
    print("=" * 72)
    passed = sum(1 for _, p, _ in results if p)
    total = len(results)
    print(f"SUMMARY: {passed}/{total} checks passed")
    if passed == total:
        print("OVERALL: PASS")
        return 0
    else:
        print("OVERALL: FAIL")
        for name, ok, detail in results:
            if not ok:
                print(f"  FAILED: {name} ({detail})")
        return 1


if __name__ == "__main__":
    sys.exit(main())
