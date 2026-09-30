"""
vectorizer.py — Hybrid Vectorizer (TF-IDF + Semantic Embeddings)
Produces composite dense vectors for material descriptions.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from config import TFIDF_MAX_FEATURES, TFIDF_NGRAM_RANGE, EMBEDDING_MODEL

# ── Lazy-loaded embedding model (heavy; load once) ────────────────────
_embedding_model = None


def _get_embedding_model():
    """Lazy-load the sentence-transformer model."""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except Exception:
            _embedding_model = None
    return _embedding_model


class HybridVectorizer:
    """
    Combines TF-IDF sparse vectors with dense semantic embeddings.
    Falls back to TF-IDF-only if sentence-transformers is unavailable.
    """

    def __init__(self):
        self.tfidf = TfidfVectorizer(
            max_features=TFIDF_MAX_FEATURES,
            ngram_range=TFIDF_NGRAM_RANGE,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self._tfidf_fitted = False
        self._corpus_tfidf = None
        self._corpus_embeddings = None

    # ── Fit on a corpus ───────────────────────────────────────────────

    def fit(self, texts: list[str]):
        """Fit TF-IDF on the corpus and pre-compute embeddings."""
        if not texts:
            return
        self._corpus_tfidf = self.tfidf.fit_transform(texts)
        self._tfidf_fitted = True

        model = _get_embedding_model()
        if model is not None:
            self._corpus_embeddings = model.encode(
                texts, show_progress_bar=False, normalize_embeddings=True,
            )
        else:
            self._corpus_embeddings = None

    # ── Transform new texts ──────────────────────────────────────────

    def transform_tfidf(self, texts: list[str]):
        """Transform texts to TF-IDF sparse matrix."""
        if not self._tfidf_fitted:
            raise RuntimeError("TF-IDF not fitted. Call fit() first.")
        return self.tfidf.transform(texts)

    def transform_embeddings(self, texts: list[str]) -> np.ndarray | None:
        """Transform texts to dense semantic embeddings."""
        model = _get_embedding_model()
        if model is None:
            return None
        return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)

    # ── Retrieve pre-computed corpus vectors ─────────────────────────

    @property
    def corpus_tfidf(self):
        return self._corpus_tfidf

    @property
    def corpus_embeddings(self):
        return self._corpus_embeddings

    @property
    def has_embeddings(self) -> bool:
        return self._corpus_embeddings is not None
