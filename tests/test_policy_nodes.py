"""
Tests for policy RAG graph nodes:
  - policy_rewrite_node
  - policy_expand_node
  - policy_grade_answer_node
"""
import pytest
import json
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# policy_rewrite_node
# ---------------------------------------------------------------------------

class TestPolicyRewriteNode:
    def _state(self, message="What is the travel reimbursement limit?"):
        return {
            "message": message,
            "rewritten_queries": None,
        }

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_parses_json_list(self, mock_llm):
        queries = ["travel reimbursement limit", "expense reimbursement cap", "travel cost policy"]
        mock_llm.return_value = json.dumps(queries)
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert state["message"] in result["rewritten_queries"]
        assert len(result["rewritten_queries"]) <= 3

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_original_message_always_included(self, mock_llm):
        mock_llm.return_value = json.dumps(["reworded query 1", "reworded query 2"])
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert state["message"] in result["rewritten_queries"]

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_fallback_on_invalid_json(self, mock_llm):
        mock_llm.return_value = "Here are some queries: reworded 1, reworded 2"
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert state["message"] in result["rewritten_queries"]

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_caps_at_three_variants(self, mock_llm):
        queries = ["q1", "q2", "q3", "q4", "q5"]
        mock_llm.return_value = json.dumps(queries)
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert len(result["rewritten_queries"]) == 3

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_non_list_json_falls_back_to_message(self, mock_llm):
        mock_llm.return_value = json.dumps({"query": "something"})
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert result["rewritten_queries"] == [state["message"]]

    @patch("graph.nodes.policy_rewrite.fast_chat")
    def test_json_in_larger_text_extracted(self, mock_llm):
        queries = ["query A", "query B"]
        mock_llm.return_value = f"Sure! Here are the variants: {json.dumps(queries)}"
        from graph.nodes.policy_rewrite import policy_rewrite_node
        state = self._state()
        result = policy_rewrite_node(state)
        assert state["message"] in result["rewritten_queries"]


# ---------------------------------------------------------------------------
# policy_expand_node
# ---------------------------------------------------------------------------

class TestPolicyExpandNode:
    @patch("graph.nodes.policy_expand.get_parent_section")
    def test_loads_unique_parent_sections(self, mock_get, sample_chunks, sample_parent_sections):
        parent_map = {p["parent_id"]: p for p in sample_parent_sections}
        mock_get.side_effect = lambda pid: parent_map.get(pid)
        from graph.nodes.policy_expand import policy_expand_node
        state = {"retrieved_chunks": sample_chunks, "parent_sections": None}
        result = policy_expand_node(state)
        # Two unique parent_ids in sample_chunks (parent-001, parent-002)
        assert len(result["parent_sections"]) == 2
        assert mock_get.call_count == 2

    @patch("graph.nodes.policy_expand.get_parent_section")
    def test_deduplicates_parent_ids(self, mock_get):
        chunks = [
            {"parent_id": "parent-001", "child_id": "c1"},
            {"parent_id": "parent-001", "child_id": "c2"},
            {"parent_id": "parent-001", "child_id": "c3"},
        ]
        mock_get.return_value = {"parent_id": "parent-001", "heading": "Leave", "filename": "policy.pdf"}
        from graph.nodes.policy_expand import policy_expand_node
        state = {"retrieved_chunks": chunks, "parent_sections": None}
        result = policy_expand_node(state)
        assert len(result["parent_sections"]) == 1
        assert mock_get.call_count == 1

    @patch("graph.nodes.policy_expand.get_parent_section")
    def test_empty_chunks_produces_empty_sections(self, mock_get):
        from graph.nodes.policy_expand import policy_expand_node
        state = {"retrieved_chunks": [], "parent_sections": None}
        result = policy_expand_node(state)
        assert result["parent_sections"] == []
        mock_get.assert_not_called()

    @patch("graph.nodes.policy_expand.get_parent_section")
    def test_missing_parent_skipped(self, mock_get):
        chunks = [{"parent_id": "missing-001", "child_id": "c1"}]
        mock_get.return_value = None
        from graph.nodes.policy_expand import policy_expand_node
        state = {"retrieved_chunks": chunks, "parent_sections": None}
        result = policy_expand_node(state)
        assert result["parent_sections"] == []


# ---------------------------------------------------------------------------
# policy_grade_answer_node
# ---------------------------------------------------------------------------

class TestPolicyGradeAnswerNode:
    def _state(self, chunks=None, parent_sections=None):
        return {
            "message": "What is the travel reimbursement limit?",
            "retrieved_chunks": chunks,
            "parent_sections": parent_sections or [],
            "evidence_sufficient": None,
            "topic_verdicts": None,
            "response": None,
            "citations": [],
        }

    def _llm_response(self, answer="The limit is $500.", sufficient=True, citations=None):
        return json.dumps({
            "answer": answer,
            "any_sufficient": sufficient,
            "topics": [{"topic": "travel", "sufficient": sufficient}],
            "citations": citations or [{"document": "expenses.pdf", "section": "Travel", "chunk_id": "c1"}],
        })

    @patch("graph.nodes.policy_grade_answer.strong_chat")
    def test_successful_grade_and_answer(self, mock_llm, sample_chunks, sample_parent_sections):
        mock_llm.return_value = self._llm_response()
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=sample_chunks, parent_sections=sample_parent_sections)
        result = policy_grade_answer_node(state)
        assert result["evidence_sufficient"] is True
        assert result["response"] == "The limit is $500."
        assert len(result["citations"]) == 1

    @patch("graph.nodes.policy_grade_answer.strong_chat")
    def test_insufficient_evidence_marked(self, mock_llm, sample_chunks, sample_parent_sections):
        mock_llm.return_value = self._llm_response(sufficient=False)
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=sample_chunks, parent_sections=sample_parent_sections)
        result = policy_grade_answer_node(state)
        assert result["evidence_sufficient"] is False

    def test_no_chunks_returns_abstain_response(self, sample_parent_sections):
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=[], parent_sections=sample_parent_sections)
        result = policy_grade_answer_node(state)
        assert result["evidence_sufficient"] is False
        assert result["response"] is not None
        assert len(result["topic_verdicts"]) == 0

    def test_no_chunks_no_parents_returns_fallback(self):
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=None, parent_sections=None)
        result = policy_grade_answer_node(state)
        assert result["evidence_sufficient"] is False
        assert "HR team" in result["response"]

    @patch("graph.nodes.policy_grade_answer.strong_chat")
    def test_fallback_on_invalid_json(self, mock_llm, sample_chunks, sample_parent_sections):
        mock_llm.return_value = "The reimbursement limit is $500 per trip."
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=sample_chunks, parent_sections=sample_parent_sections)
        result = policy_grade_answer_node(state)
        assert result["response"] == "The reimbursement limit is $500 per trip."

    @patch("graph.nodes.policy_grade_answer.strong_chat")
    def test_passes_top_6_chunks_to_llm(self, mock_llm, sample_parent_sections):
        mock_llm.return_value = self._llm_response()
        chunks = [
            {"child_id": f"c{i}", "parent_id": "parent-001", "content": f"content {i}", "score": 0.9}
            for i in range(10)
        ]
        from graph.nodes.policy_grade_answer import policy_grade_answer_node
        state = self._state(chunks=chunks, parent_sections=sample_parent_sections)
        policy_grade_answer_node(state)
        prompt_arg = mock_llm.call_args[0][0]
        # Only first 6 chunk IDs should appear in the prompt
        for i in range(6):
            assert f"c{i}" in prompt_arg
        for i in range(6, 10):
            assert f"c{i}" not in prompt_arg
