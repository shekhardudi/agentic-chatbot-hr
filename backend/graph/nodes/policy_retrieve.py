"""
policy_retrieve node — hybrid retrieval using vector search + FTS,
fused with reciprocal rank fusion.
"""
from logger import get_logger
from models.state import AgentState
from db.rag import vector_search, fulltext_search, reciprocal_rank_fusion
from db.embedder import embed_texts

log = get_logger(__name__)


def policy_retrieve_node(state: AgentState) -> AgentState:
    queries = state.get("rewritten_queries") or [state["message"]]
    log.info("Hybrid retrieval | %d query variant(s)", len(queries))

    all_vector: list[dict] = []
    all_fts: list[dict] = []

    for i, query in enumerate(queries):
        log.debug("Embedding query %d/%d: %r", i + 1, len(queries), query[:60])
        embeddings = embed_texts([query])
        if embeddings:
            vec_results = vector_search(embeddings[0], limit=10)
            all_vector.extend(vec_results)
        fts_results = fulltext_search(query, limit=10)
        all_fts.extend(fts_results)

    log.debug("Raw results before dedup | vector=%d | fts=%d", len(all_vector), len(all_fts))

    seen_vec: dict[str, dict] = {}
    for r in all_vector:
        cid = r["child_id"]
        if cid not in seen_vec or r["score"] > seen_vec[cid]["score"]:
            seen_vec[cid] = r

    seen_fts: dict[str, dict] = {}
    for r in all_fts:
        cid = r["child_id"]
        if cid not in seen_fts or r["score"] > seen_fts[cid]["score"]:
            seen_fts[cid] = r

    fused = reciprocal_rank_fusion(
        list(seen_vec.values()),
        list(seen_fts.values()),
        top_n=8,
    )
    log.info(
        "Retrieval complete | unique_vector=%d | unique_fts=%d | fused=%d",
        len(seen_vec), len(seen_fts), len(fused),
    )
    state["retrieved_chunks"] = fused
    return state
