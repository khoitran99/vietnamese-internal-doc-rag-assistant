#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "default.yaml"
CHUNKS_PATH = ROOT / "data" / "processed" / "chunks.jsonl"
@dataclass
class StepResult:
    name: str
    passed: bool
    details: str


def _base_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT)
    env.setdefault("DISABLE_EXTERNAL_MODELS", "1")
    return env


def _run_command(name: str, cmd: List[str], env: Dict[str, str]) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception as exc:
        return False, f"{name} failed to execute: {exc}"

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()
    output = "\n".join(part for part in [stdout, stderr] if part).strip()

    if result.returncode != 0:
        return False, f"{name} exited with code {result.returncode}\n{output}"
    return True, output


def _extract_json_blob(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("No JSON object found in output")
    return json.loads(text[start : end + 1])


def _read_chunks() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not CHUNKS_PATH.exists():
        return rows
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _find_onboarding_chunk_id(rows: List[Dict[str, Any]]) -> str | None:
    for row in rows:
        if row.get("doc_id") == "engineering_onboarding_public" and "Onboarding" in row.get("section_path", ""):
            return row.get("chunk_id")
    return None


def run_step_2(env: Dict[str, str]) -> StepResult:
    ok, output = _run_command(
        "Step 2 (rebuild chunks+indices)",
        [sys.executable, "scripts/ingest_and_index.py", "--config", str(CONFIG_PATH)],
        env,
    )
    if not ok:
        return StepResult("Step 2", False, output)

    match = re.search(r"Ingested\s+(\d+)\s+chunks", output)
    if not match:
        return StepResult("Step 2", False, f"Rebuild succeeded but could not parse ingested chunk count.\n{output}")
    count = int(match.group(1))
    if count <= 0:
        return StepResult("Step 2", False, f"Chunk count is not positive: {count}")
    if not CHUNKS_PATH.exists():
        return StepResult("Step 2", False, f"Chunk file missing: {CHUNKS_PATH}")
    return StepResult("Step 2", True, f"Ingested {count} chunks")


def run_step_4(env: Dict[str, str]) -> StepResult:
    ok, output = _run_command(
        "Step 4 (unit/integration tests)",
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        env,
    )
    if not ok:
        return StepResult("Step 4", False, output)
    return StepResult("Step 4", True, "Tests passed")


def run_step_5(env: Dict[str, str]) -> StepResult:
    ok, output = _run_command(
        "Step 5 (retrieval eval)",
        [sys.executable, "scripts/run_eval.py", "--config", str(CONFIG_PATH), "--top_k", "5"],
        env,
    )
    if not ok:
        return StepResult("Step 5", False, output)

    try:
        report = _extract_json_blob(output)
    except Exception as exc:
        return StepResult("Step 5", False, f"Eval output is not valid JSON: {exc}\n{output}")

    for key in ("bm25", "dense", "hybrid"):
        if key not in report:
            return StepResult("Step 5", False, f"Missing '{key}' metrics in eval output")
        for metric in ("recall_at_k", "mrr", "evidence_hit_rate"):
            if metric not in report[key]:
                return StepResult("Step 5", False, f"Missing metric '{metric}' in '{key}'")
    return StepResult("Step 5", True, "Eval JSON structure is valid")


def run_step_7(env: Dict[str, str]) -> StepResult:
    rows = _read_chunks()
    expected_onboarding_chunk = _find_onboarding_chunk_id(rows)
    if not expected_onboarding_chunk:
        return StepResult(
            "Step 7",
            False,
            "Could not find expected onboarding chunk ID in data/processed/chunks.jsonl. Run Step 2 first.",
        )

    try:
        try:
            from fastapi.testclient import TestClient
        except Exception as exc:
            return StepResult("Step 7", False, f"fastapi TestClient is unavailable: {exc}")

        os.environ["APP_CONFIG_PATH"] = str(CONFIG_PATH)
        from src.api.app import create_app, get_service  # imported late so env var is applied

        get_service.cache_clear()
        client = TestClient(create_app())

        health_resp = client.get("/health")
        if health_resp.status_code != 200:
            return StepResult("Step 7", False, f"/health returned status {health_resp.status_code}")
        health = health_resp.json()
        if health.get("status") != "ok":
            return StepResult("Step 7", False, f"/health returned unexpected payload: {health}")

        onboarding_resp = client.post(
            "/ask",
            json={
                "question": "Kỹ sư mới cần hoàn thành onboarding trong bao lâu?",
                "top_k": 5,
                "access_level": "public",
            },
        )
        if onboarding_resp.status_code != 200:
            return StepResult("Step 7", False, f"Onboarding request failed: {onboarding_resp.status_code}")
        onboarding = onboarding_resp.json()
        if onboarding.get("status") != "ANSWERED":
            return StepResult("Step 7", False, f"Onboarding check failed: {onboarding}")
        first_citation = (onboarding.get("citations") or [{}])[0].get("chunk_id")
        if first_citation != expected_onboarding_chunk:
            return StepResult(
                "Step 7",
                False,
                f"Onboarding citation mismatch. Expected {expected_onboarding_chunk}, got {first_citation}",
            )

        unsupported_resp = client.post(
            "/ask",
            json={
                "question": "Quy định an toàn bay nội bộ là gì?",
                "top_k": 5,
                "access_level": "internal",
            },
        )
        if unsupported_resp.status_code != 200:
            return StepResult("Step 7", False, f"Unsupported request failed: {unsupported_resp.status_code}")
        unsupported = unsupported_resp.json()
        if unsupported.get("status") != "NOT_FOUND":
            return StepResult("Step 7", False, f"Unsupported question should be NOT_FOUND: {unsupported}")

        restricted_low_access_resp = client.post(
            "/ask",
            json={
                "question": "Thông tin đăng nhập nhạy cảm cần xoay vòng bao lâu?",
                "top_k": 5,
                "access_level": "public",
            },
        )
        if restricted_low_access_resp.status_code != 200:
            return StepResult("Step 7", False, f"Restricted low-access request failed: {restricted_low_access_resp.status_code}")
        restricted_low_access = restricted_low_access_resp.json()
        if restricted_low_access.get("status") != "NOT_FOUND":
            return StepResult(
                "Step 7",
                False,
                f"Restricted question with public access should be NOT_FOUND: {restricted_low_access}",
            )

        return StepResult("Step 7", True, "API smoke checks passed")
    except Exception as exc:
        return StepResult("Step 7", False, f"API smoke checks failed: {exc}")


def main() -> int:
    env = _base_env()

    steps = [
        run_step_2(env),
        run_step_4(env),
        run_step_5(env),
        run_step_7(env),
    ]

    print("\n=== Verification Summary ===")
    for step in steps:
        status = "PASS" if step.passed else "FAIL"
        print(f"[{status}] {step.name}: {step.details}")

    overall_pass = all(step.passed for step in steps)
    print(f"\nOVERALL: {'PASS' if overall_pass else 'FAIL'}")
    return 0 if overall_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
