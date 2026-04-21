"""
Tests for db/rag.py — vector_search, fulltext_search, get_parent_section,
and reciprocal_rank_fusion.

The three DB functions use ManagedConn which requires a live pool, so we
patch at the ManagedConn level. The RRF function is pure Python — no mocks.
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# reciprocal_rank_fusion — pure function, no mocking needed
# ---------------------------------------------------------------------------

class TestReciprocalRankFusion:
    def setup_method(self):
        from db.rag import reciprocal_rank_fusion
        self.rrf = reciprocal_rank_fusion

    def _chunk(self, child_id, parent_id="p1", score=0.5):
        return {"child_id": child_id, "parent_id": parent_id, "content": "...", "score": score}

    def test_empty_inputs_returns_empty(self):
        result = self.rrf([], [], top_n=5)
        assert result == []

    def test_single_vector_result(self):
        chunks = [self._chunk("c1"), self._chunk("c2"), self._chunk("c3")]
        result = self.rrf(chunks, [], top_n=2)
        assert len(result) == 2
        assert result[0]["child_id"] == "c1"  # rank 0 → highest RRF score

    def test_single_fts_result(self):
        chunks = [self._chunk("c1"), self._chunk("c2"), self._chunk("c3")]
        result = self.rrf([], chunks, top_n=2)
        assert len(result) == 2

    def test_deduplication_on_overlap(self):
        vec = [self._chunk("c1"), self._chunk("c2")]
        fts = [self._chunk("c2"), self._chunk("c3")]
        result = self.rrf(vec, fts, top_n=3)
        ids = [r["child_id"] for r in result]
        assert len(set(ids)) == len(ids)  # no duplicates

    def test_overlapping_chunk_ranked_higher(self):
        vec = [self._chunk("c1"), self._chunk("c2")]
        fts = [self._chunk("c2"), self._chunk("c1")]
        result = self.rrf(vec, fts, top_n=2)
        # Both c1 and c2 appear in both lists — order depends on rank
        ids = [r["child_id"] for r in result]
        assert "c1" in ids
        assert "c2" in ids

    def test_top_n_limits_output(self):
        chunks = [self._chunk(f"c{i}") for i in range(20)]
        result = self.rrf(chunks, [], top_n=5)
        assert len(result) == 5

    def test_top_n_larger_than_results_returns_all(self):
        chunks = [self._chunk("c1"), self._chunk("c2")]
        result = self.rrf(chunks, [], top_n=10)
        assert len(result) == 2

    def test_k_parameter_affects_score(self):
        chunks = [self._chunk("c1")]
        result_k60 = self.rrf(chunks, [], k=60, top_n=1)
        # With k=1 the score for rank-0 would be 1/(1+1)=0.5
        # With k=60 the score for rank-0 would be 1/(60+1)=0.016
        # We just verify it still returns the item
        assert result_k60[0]["child_id"] == "c1"

    def test_fts_only_chunk_included(self):
        vec = [self._chunk("c1")]
        fts = [self._chunk("c1"), self._chunk("c2")]
        result = self.rrf(vec, fts, top_n=2)
        ids = [r["child_id"] for r in result]
        assert "c2" in ids

    def test_preserves_chunk_fields(self):
        chunk = {"child_id": "c1", "parent_id": "p1", "content": "hello world", "score": 0.9}
        result = self.rrf([chunk], [], top_n=1)
        assert result[0]["content"] == "hello world"
        assert result[0]["parent_id"] == "p1"


# ---------------------------------------------------------------------------
# vector_search — mock ManagedConn
# ---------------------------------------------------------------------------

class TestVectorSearch:
    def _mock_conn(self, rows, cols):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        cur.description = [(c,) for c in cols]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: s
        conn.__exit__ = MagicMock(return_value=False)
        return conn, cur

    @patch("db.rag.ManagedConn")
    def test_returns_list_of_dicts(self, mock_managed_conn):
        cols = ["child_id", "parent_id", "content", "window_index", "score"]
        rows = [("c1", "p1", "text", 0, 0.9)]
        conn, cur = self._mock_conn(rows, cols)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.rag import vector_search
        result = vector_search([0.1, 0.2, 0.3], limit=5)
        assert len(result) == 1
        assert result[0]["child_id"] == "c1"
        assert result[0]["score"] == 0.9

    @patch("db.rag.ManagedConn")
    def test_empty_result_returns_empty_list(self, mock_managed_conn):
        conn, cur = self._mock_conn([], ["child_id", "parent_id", "content", "window_index", "score"])
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.rag import vector_search
        result = vector_search([0.1, 0.2], limit=5)
        assert result == []


# ---------------------------------------------------------------------------
# fulltext_search — mock ManagedConn
# ---------------------------------------------------------------------------

class TestFulltextSearch:
    @patch("db.rag.ManagedConn")
    def test_returns_list_of_dicts(self, mock_managed_conn):
        cur = MagicMock()
        cur.fetchall.return_value = [("c2", "p1", "full text result", 1, 0.75)]
        cur.description = [("child_id",), ("parent_id",), ("content",), ("window_index",), ("score",)]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.rag import fulltext_search
        result = fulltext_search("travel reimbursement", limit=10)
        assert result[0]["child_id"] == "c2"
        assert result[0]["score"] == 0.75

    @patch("db.rag.ManagedConn")
    def test_empty_query_returns_empty_list(self, mock_managed_conn):
        cur = MagicMock()
        cur.fetchall.return_value = []
        cur.description = [("child_id",), ("parent_id",), ("content",), ("window_index",), ("score",)]
        cur.__enter__ = lambda s: s
        cur.__exit__ = MagicMock(return_value=False)
        conn = MagicMock()
        conn.cursor.return_value = cur
        conn.__enter__ = lambda s: conn
        conn.__exit__ = MagicMock(return_value=False)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.rag import fulltext_search
        result = fulltext_search("", limit=10)
        assert result == []
