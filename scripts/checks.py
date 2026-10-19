import re


def verify_checks(payload: dict) -> None:
    outcome = payload.get("run_outcome") or {}
    tests = outcome.get("tests") or {}
    has_summary = bool(tests)
    if not has_summary:
        raise AssertionError("Artemis の検証結果が取得できません。")
    has_failures = tests.get("failed", 0) > 0 or tests.get("unchecked", 0) > 0
    if has_failures:
        raise AssertionError(f"Artemis のアサーションに失敗または未検証があります: {tests}")

    statuses: dict[str, set[str]] = {}
    for record in payload.get("records", []):
        text = record.get("item_text", "").strip()
        # 上流が同じ検証を接頭辞の有無で重複記録するため、別要件として数えない。
        canonical = re.sub(r"^\[(?:assert|verify)\]\s*\((?:on_complete|at_end)\)\s*", "", text)
        statuses.setdefault(canonical, set()).add(record.get("status", "unknown"))
    has_verified_items = bool(statuses) and all("passed" in values for values in statuses.values())
    if not has_verified_items:
        raise AssertionError("成功を確認できない検証項目があります。checks.json を確認。")
