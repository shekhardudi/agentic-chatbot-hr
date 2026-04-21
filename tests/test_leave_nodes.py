"""
Tests for leave-related graph nodes:
  - leave_apply_calculate (pure Python, no external I/O in the helper)
  - leave_apply_gather (LLM call mocked)
  - leave_apply_update (NocoDB call mocked)
  - leave_balance_node (NocoDB call mocked)
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# calculate_leave_hours — pure function, no mocking needed
# ---------------------------------------------------------------------------

class TestCalculateLeaveHours:
    def setup_method(self):
        from graph.nodes.leave_apply_calculate import calculate_leave_hours
        self.calc = calculate_leave_hours

    def test_days_to_hours(self):
        assert self.calc(1.0, "days") == 8.0

    def test_three_days(self):
        assert self.calc(3.0, "days") == 24.0

    def test_half_day(self):
        assert self.calc(0.5, "days") == 4.0

    def test_hours_unchanged(self):
        assert self.calc(16.0, "hours") == 16.0

    def test_fractional_hours(self):
        assert self.calc(2.5, "hours") == 2.5

    def test_zero_days(self):
        assert self.calc(0.0, "days") == 0.0

    def test_zero_hours(self):
        assert self.calc(0.0, "hours") == 0.0


# ---------------------------------------------------------------------------
# leave_apply_calculate node
# ---------------------------------------------------------------------------

class TestLeaveApplyCalculateNode:
    def _make_state(self, leave_type="annual", duration=3.0, unit="days",
                    employee_id="EMP-001"):
        return {
            "employee_email": "alice@example.com",
            "employee_id": employee_id,
            "leave_apply_type": leave_type,
            "leave_apply_duration": duration,
            "leave_apply_unit": unit,
            "leave_apply_hours": None,
            "leave_apply_sufficient": None,
            "leave_apply_current_balance": None,
            "leave_apply_new_balance": None,
            "leave_apply_status": None,
            "response": None,
        }

    @patch("graph.nodes.leave_apply_calculate.nocodb")
    def test_sufficient_balance(self, mock_nocodb, leave_apply_ready_state):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 80.0, "used_ytd_hours": 0.0}]
        from graph.nodes.leave_apply_calculate import leave_apply_calculate
        state = self._make_state()
        result = leave_apply_calculate(state)
        assert result["leave_apply_sufficient"] is True
        assert result["leave_apply_hours"] == 24.0
        assert result["leave_apply_current_balance"] == 80.0
        assert result["leave_apply_new_balance"] == 56.0
        assert result["leave_apply_status"] == "calculated"

    @patch("graph.nodes.leave_apply_calculate.nocodb")
    def test_insufficient_balance(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 8.0, "used_ytd_hours": 72.0}]
        from graph.nodes.leave_apply_calculate import leave_apply_calculate
        state = self._make_state(duration=5.0)  # 40 hours requested
        result = leave_apply_calculate(state)
        assert result["leave_apply_sufficient"] is False
        assert result["leave_apply_status"] == "insufficient_balance"
        assert "Insufficient" in result["response"]

    @patch("graph.nodes.leave_apply_calculate.nocodb")
    def test_no_balance_record(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = []
        from graph.nodes.leave_apply_calculate import leave_apply_calculate
        state = self._make_state()
        result = leave_apply_calculate(state)
        assert result["leave_apply_sufficient"] is False
        assert result["leave_apply_status"] == "no_balance_record"
        assert result["response"] is not None

    @patch("graph.nodes.leave_apply_calculate.nocodb")
    def test_hours_unit(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 20.0, "used_ytd_hours": 0.0}]
        from graph.nodes.leave_apply_calculate import leave_apply_calculate
        state = self._make_state(duration=4.0, unit="hours")
        result = leave_apply_calculate(state)
        assert result["leave_apply_hours"] == 4.0
        assert result["leave_apply_sufficient"] is True
        assert result["leave_apply_new_balance"] == 16.0

    @patch("graph.nodes.leave_apply_calculate.nocodb")
    def test_exact_balance_is_sufficient(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 24.0, "used_ytd_hours": 0.0}]
        from graph.nodes.leave_apply_calculate import leave_apply_calculate
        state = self._make_state(duration=3.0)  # exactly 24 hours
        result = leave_apply_calculate(state)
        assert result["leave_apply_sufficient"] is True
        assert result["leave_apply_new_balance"] == 0.0


# ---------------------------------------------------------------------------
# leave_apply_gather node
# ---------------------------------------------------------------------------

class TestLeaveApplyGatherNode:
    def _base_state(self, message="I want to take annual leave", entities=None):
        return {
            "employee_email": "alice@example.com",
            "message": message,
            "entities": entities or {},
            "leave_apply_type": None,
            "leave_apply_duration": None,
            "leave_apply_unit": None,
            "leave_apply_status": None,
            "response": None,
            "status": "complete",
        }

    @patch("graph.nodes.leave_apply_gather.fast_chat")
    def test_missing_both_asks_question(self, mock_llm):
        mock_llm.return_value = "What type of leave and how many days?"
        from graph.nodes.leave_apply_gather import leave_apply_gather
        state = self._base_state()
        result = leave_apply_gather(state)
        assert result["leave_apply_status"] == "missing_info"
        assert result["status"] == "needs_clarification"
        assert result["response"] is not None
        mock_llm.assert_called_once()

    @patch("graph.nodes.leave_apply_gather.fast_chat")
    def test_missing_duration_asks_question(self, mock_llm):
        mock_llm.return_value = "How many days would you like?"
        from graph.nodes.leave_apply_gather import leave_apply_gather
        state = self._base_state(entities={"leave_type": "annual"})
        result = leave_apply_gather(state)
        assert result["leave_apply_status"] == "missing_info"

    @patch("graph.nodes.leave_apply_gather.fast_chat")
    def test_missing_leave_type_asks_question(self, mock_llm):
        mock_llm.return_value = "What type of leave do you need?"
        from graph.nodes.leave_apply_gather import leave_apply_gather
        state = self._base_state(entities={"leave_duration": 3})
        result = leave_apply_gather(state)
        assert result["leave_apply_status"] == "missing_info"

    def test_all_present_sets_ready(self):
        from graph.nodes.leave_apply_gather import leave_apply_gather
        state = self._base_state(
            entities={"leave_type": "annual", "leave_duration": 3, "leave_unit": "days"}
        )
        result = leave_apply_gather(state)
        assert result["leave_apply_status"] == "ready"
        assert result["leave_apply_type"] == "annual"
        assert result["leave_apply_duration"] == 3.0
        assert result["leave_apply_unit"] == "days"

    def test_invalid_leave_type_asks_question(self):
        from graph.nodes.leave_apply_gather import leave_apply_gather
        with patch("graph.nodes.leave_apply_gather.fast_chat") as mock_llm:
            mock_llm.return_value = "Please specify: annual, sick, or personal."
            state = self._base_state(
                entities={"leave_type": "maternity", "leave_duration": 3}
            )
            result = leave_apply_gather(state)
            assert result["leave_apply_status"] == "missing_info"

    def test_defaults_unit_to_days(self):
        from graph.nodes.leave_apply_gather import leave_apply_gather
        state = self._base_state(
            entities={"leave_type": "sick", "leave_duration": 2}
            # no leave_unit provided
        )
        result = leave_apply_gather(state)
        assert result["leave_apply_unit"] == "days"


# ---------------------------------------------------------------------------
# leave_apply_update node
# ---------------------------------------------------------------------------

class TestLeaveApplyUpdateNode:
    def _state(self):
        return {
            "employee_email": "alice@example.com",
            "employee_id": "EMP-001",
            "leave_apply_type": "annual",
            "leave_apply_hours": 24.0,
            "leave_apply_new_balance": 56.0,
            "leave_apply_status": "calculated",
            "response": None,
        }

    @patch("graph.nodes.leave_apply_update.nocodb")
    def test_successful_update(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 80.0, "used_ytd_hours": 0.0}]
        mock_nocodb.update_leave_balance.return_value = {"balance_hours": 56.0}
        from graph.nodes.leave_apply_update import leave_apply_update
        state = self._state()
        result = leave_apply_update(state)
        assert result["leave_apply_status"] == "applied"
        mock_nocodb.update_leave_balance.assert_called_once_with(
            employee_id="EMP-001",
            leave_type="annual",
            new_balance_hours=56.0,
            new_used_hours=24.0,
        )

    @patch("graph.nodes.leave_apply_update.nocodb")
    def test_failed_update_sets_error_response(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 80.0, "used_ytd_hours": 0.0}]
        mock_nocodb.update_leave_balance.return_value = {}
        from graph.nodes.leave_apply_update import leave_apply_update
        state = self._state()
        result = leave_apply_update(state)
        assert result["leave_apply_status"] == "update_failed"
        assert result["response"] is not None

    @patch("graph.nodes.leave_apply_update.nocodb")
    def test_used_hours_cumulates_correctly(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"balance_hours": 56.0, "used_ytd_hours": 24.0}]
        mock_nocodb.update_leave_balance.return_value = {"balance_hours": 32.0}
        from graph.nodes.leave_apply_update import leave_apply_update
        state = self._state()
        state["leave_apply_hours"] = 24.0
        state["leave_apply_new_balance"] = 32.0
        leave_apply_update(state)
        _, kwargs = mock_nocodb.update_leave_balance.call_args
        assert kwargs["new_used_hours"] == 48.0  # 24 existing + 24 new


# ---------------------------------------------------------------------------
# leave_balance_node
# ---------------------------------------------------------------------------

class TestLeaveBalanceNode:
    def _state(self, employee_id="EMP-001", leave_type=None):
        return {
            "employee_email": "alice@example.com",
            "employee_id": employee_id,
            "entities": {"leave_type": leave_type} if leave_type else {},
            "leave_data": None,
            "response": None,
        }

    @patch("graph.nodes.leave_balance.nocodb")
    def test_fetches_balances(self, mock_nocodb):
        balances = [{"leave_type": "annual", "balance_hours": 80.0}]
        mock_nocodb.get_leave_balance.return_value = balances
        from graph.nodes.leave_balance import leave_balance_node
        state = self._state()
        result = leave_balance_node(state)
        assert result["leave_data"] == {"balances": balances, "employee_id": "EMP-001"}
        mock_nocodb.get_leave_balance.assert_called_once_with("EMP-001", None)

    @patch("graph.nodes.leave_balance.nocodb")
    def test_filtered_by_leave_type(self, mock_nocodb):
        mock_nocodb.get_leave_balance.return_value = [{"leave_type": "sick", "balance_hours": 40.0}]
        from graph.nodes.leave_balance import leave_balance_node
        state = self._state(leave_type="sick")
        leave_balance_node(state)
        mock_nocodb.get_leave_balance.assert_called_once_with("EMP-001", "sick")

    @patch("graph.nodes.leave_balance.nocodb")
    def test_missing_employee_id_sets_error(self, mock_nocodb):
        from graph.nodes.leave_balance import leave_balance_node
        state = self._state(employee_id=None)
        result = leave_balance_node(state)
        assert result["leave_data"] is None
        assert result["response"] is not None
        mock_nocodb.get_leave_balance.assert_not_called()

    @patch("graph.nodes.leave_balance.nocodb")
    def test_nocodb_exception_sets_error(self, mock_nocodb):
        mock_nocodb.get_leave_balance.side_effect = RuntimeError("NocoDB down")
        from graph.nodes.leave_balance import leave_balance_node
        state = self._state()
        result = leave_balance_node(state)
        assert result["leave_data"] is None
        assert "Unable to retrieve" in result["response"]
