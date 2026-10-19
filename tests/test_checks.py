import pytest

from scripts.checks import verify_checks


def test_completed_task_with_failed_assertion_is_rejected():
    with pytest.raises(AssertionError):
        verify_checks({"run_outcome": {"task_status": "completed", "tests": {"failed": 1}}})


def test_missing_verdicts_are_rejected():
    with pytest.raises(AssertionError):
        verify_checks({})
    with pytest.raises(AssertionError):
        verify_checks(
            {
                "run_outcome": {"tests": {"inconclusive": 1}},
                "records": [{"item_text": "task is complete", "status": "inconclusive"}],
            }
        )


def test_duplicate_label_does_not_discard_confirmed_verdict():
    verify_checks(
        {
            "run_outcome": {"tests": {"passed": 1, "inconclusive": 1}},
            "records": [
                {"item_text": "[assert] (at_end) task is complete", "status": "passed"},
                {"item_text": "task is complete", "status": "inconclusive"},
            ],
        }
    )
