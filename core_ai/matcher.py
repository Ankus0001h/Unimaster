"""
matcher.py — Composite Cosine Similarity Engine & Auto-Clustering
Scores material pairs and groups duplicates into national clusters.
"""

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine
from rapidfuzz import fuzz
from config import (
    WEIGHT_SEMANTIC, WEIGHT_ATTRIBUTE, WEIGHT_FUZZY,
    MATCH_THRESHOLD, HIGH_CONFIDENCE, LOW_CONFIDENCE,
)
from core_ai.attribute_extractor import extract_attributes


def cosine_sim_sparse(a, b):
    """Cosine similarity between two sparse vectors (single row each)."""
    return sklearn_cosine(a, b)[0, 0]


def cosine_sim_dense(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two dense vectors."""
    a = a.flatten()
    b = b.flatten()
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


def attribute_similarity(attrs_a: dict, attrs_b: dict) -> float:
    """
    Compare two attribute dictionaries.
    Score = fraction of shared non-empty keys that have matching values.
    """
    all_keys = set(attrs_a.keys()) | set(attrs_b.keys())
    if not all_keys:
        return 0.0

    matches = 0
    compared = 0
    for key in all_keys:
        va = attrs_a.get(key, "").strip().lower()
        vb = attrs_b.get(key, "").strip().lower()
        if va or vb:
            compared += 1
            if va and vb:
                # Use fuzzy comparison for attribute values
                ratio = fuzz.ratio(va, vb) / 100.0
                if ratio >= 0.80:
                    matches += 1
                else:
                    matches += ratio * 0.5  # partial credit

    return matches / compared if compared else 0.0


def fuzzy_text_score(text_a: str, text_b: str) -> float:
    """Fuzzy string similarity using token-sort ratio."""
    return fuzz.token_sort_ratio(text_a, text_b) / 100.0


def composite_score(
    semantic: float,
    attribute: float,
    fuzzy: float,
) -> float:
    """
    Final Score = (0.6 × Semantic) + (0.3 × Attribute) + (0.1 × Fuzzy)
    """
    return (
        WEIGHT_SEMANTIC * semantic
        + WEIGHT_ATTRIBUTE * attribute
        + WEIGHT_FUZZY * fuzzy
    )


class MaterialMatcher:
    """
    Scores all pairs of materials and clusters duplicates.
    """

    def __init__(self, vectorizer):
        self.vectorizer = vectorizer

    def score_pair(
        self,
        idx_a: int,
        idx_b: int,
        raw_texts: list[str],
        processed_texts: list[str],
        attributes_list: list[dict],
    ) -> float:
        """Compute composite similarity between two items."""

        # Semantic score (TF-IDF cosine or embedding cosine)
        tfidf_a = self.vectorizer.corpus_tfidf[idx_a]
        tfidf_b = self.vectorizer.corpus_tfidf[idx_b]
        sem_score = cosine_sim_sparse(tfidf_a, tfidf_b)

        if self.vectorizer.has_embeddings:
            emb_a = self.vectorizer.corpus_embeddings[idx_a]
            emb_b = self.vectorizer.corpus_embeddings[idx_b]
            emb_score = cosine_sim_dense(emb_a, emb_b)
            sem_score = 0.5 * sem_score + 0.5 * emb_score

        # Attribute score
        attr_score = attribute_similarity(
            attributes_list[idx_a], attributes_list[idx_b]
        )

        # Fuzzy text score (on raw descriptions)
        fuz_score = fuzzy_text_score(raw_texts[idx_a], raw_texts[idx_b])

        return composite_score(sem_score, attr_score, fuz_score)

    def find_matches(
        self,
        raw_texts: list[str],
        processed_texts: list[str],
        attributes_list: list[dict],
        threshold: float = MATCH_THRESHOLD,
    ) -> list[dict]:
        """
        Compare all pairs and return matches above threshold.
        Returns list of {idx_a, idx_b, score} sorted descending by score.
        """
        n = len(processed_texts)
        matches = []

        for i in range(n):
            for j in range(i + 1, n):
                score = self.score_pair(
                    i, j, raw_texts, processed_texts, attributes_list
                )
                if score >= threshold:
                    matches.append({
                        "idx_a": i,
                        "idx_b": j,
                        "score": round(score * 100, 2),
                    })

        matches.sort(key=lambda m: m["score"], reverse=True)
        return matches

    def cluster_materials(
        self,
        raw_texts: list[str],
        processed_texts: list[str],
        attributes_list: list[dict],
        threshold: float = MATCH_THRESHOLD,
    ) -> list[list[int]]:
        """
        Union-Find clustering: group indices with match >= threshold.
        Returns list of clusters (each a list of row indices).
        """
        n = len(processed_texts)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        matches = self.find_matches(
            raw_texts, processed_texts, attributes_list, threshold
        )
        for m in matches:
            union(m["idx_a"], m["idx_b"])

        clusters: dict[int, list[int]] = {}
        for i in range(n):
            root = find(i)
            clusters.setdefault(root, []).append(i)

        # Return all clusters (including singletons)
        return list(clusters.values())
