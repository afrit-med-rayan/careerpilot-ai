import logging
import math
import re
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)

# Lazy loaded model
_model = None


def _get_sentence_transformer():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Lightweight MiniLM model for fast vector embeddings
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("SentenceTransformer 'all-MiniLM-L6-v2' loaded successfully.")
        except Exception as exc:
            logger.warning(f"Could not load SentenceTransformer: {exc}. Using TF-IDF cosine fallback.")
            _model = False
    return _model if _model is not False else None


def _text_to_vector(text: str) -> Counter:
    words = re.findall(r"\w+", text.lower())
    return Counter(words)


def compute_cosine_similarity_fallback(text1: str, text2: str) -> float:
    """Fallback cosine similarity based on term frequencies."""
    vec1 = _text_to_vector(text1)
    vec2 = _text_to_vector(text2)

    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in vec1.keys()])
    sum2 = sum([vec2[x] ** 2 for x in vec2.keys()])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator) / denominator


def compute_similarity(text1: str, text2: str) -> float:
    """
    Computes semantic similarity score between 0.0 and 1.0.
    Tries SentenceTransformer first; falls back to term-frequency cosine similarity.
    """
    if not text1.strip() or not text2.strip():
        return 0.0

    st_model = _get_sentence_transformer()
    if st_model is not None:
        try:
            embeddings = st_model.encode([text1, text2])
            # Dot product of normalized vectors = cosine similarity
            from sentence_transformers.util import cos_sim
            sim = cos_sim(embeddings[0], embeddings[1]).item()
            return max(0.0, min(1.0, float(sim)))
        except Exception as exc:
            logger.warning(f"SentenceTransformer computation failed: {exc}. Falling back.")

    return compute_cosine_similarity_fallback(text1, text2)
