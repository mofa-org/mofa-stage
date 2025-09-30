"""Lightweight text index for MoFA nodes."""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional


class NodeKnowledgeIndex:
    """Build a tiny TF-IDF index from gathered node metadata."""

    TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")

    def __init__(self):
        self._node_documents: Dict[str, Counter] = {}
        self._document_frequency: Counter = Counter()
        self._node_norms: Dict[str, float] = {}
        self._total_docs: int = 0

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return [token.lower() for token in NodeKnowledgeIndex.TOKEN_PATTERN.findall(text or "")]

    def build(self, nodes: Iterable[Dict]) -> None:
        """Rebuild the index from the provided node list."""
        self._node_documents.clear()
        self._document_frequency.clear()
        self._node_norms.clear()

        for node in nodes:
            name = node.get("name")
            if not name:
                continue

            tokens = self._node_tokens(node)
            if not tokens:
                continue

            counter = Counter(tokens)
            self._node_documents[name] = counter

        self._total_docs = len(self._node_documents)
        if self._total_docs == 0:
            return

        # Document frequency calculation
        for counter in self._node_documents.values():
            for token in counter:
                self._document_frequency[token] += 1

        # Pre-compute norms for cosine similarity
        for name, counter in self._node_documents.items():
            norm = 0.0
            for token, tf in counter.items():
                weight = tf * self._idf(token)
                norm += weight * weight
            self._node_norms[name] = math.sqrt(norm) if norm else 0.0

    def _node_tokens(self, node: Dict) -> List[str]:
        chunks: List[str] = []
        description = node.get("description")
        if description:
            chunks.append(description)

        metadata = node.get("metadata", {}) or {}
        for key in ("doc_highlights", "entry_points", "dependencies", "config_files",
                    "primary_files", "tests", "keywords"):
            value = metadata.get(key)
            if isinstance(value, str):
                chunks.append(value)
            elif isinstance(value, (list, tuple, set)):
                chunks.append(" ".join(str(item) for item in value))
            elif isinstance(value, dict):
                chunks.append(" ".join(
                    f"{k}:{v}" for k, v in value.items()
                ))

        for snippet in metadata.get("context_snippets", []) or []:
            text = snippet.get("snippet")
            if text:
                chunks.append(text)

        # Additional structural hints
        for structural_key in ("has_agent_package", "has_configs", "has_dataflow", "has_tests"):
            if metadata.get(structural_key):
                chunks.append(structural_key)

        return self._tokenize(" ".join(chunks))

    def _idf(self, token: str) -> float:
        df = self._document_frequency.get(token, 0)
        return math.log((self._total_docs + 1) / (df + 1)) + 1.0

    def search(self, query: str, limit: int = 5) -> List[Dict]:
        if not query or self._total_docs == 0:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        query_tf = Counter(query_tokens)
        query_vector: Dict[str, float] = {}
        query_norm = 0.0

        for token, tf in query_tf.items():
            weight = tf * self._idf(token)
            query_vector[token] = weight
            query_norm += weight * weight

        query_norm = math.sqrt(query_norm) if query_norm else 0.0
        if query_norm == 0:
            return []

        scores: Dict[str, float] = defaultdict(float)

        for token, q_weight in query_vector.items():
            if token not in self._document_frequency:
                continue
            idf = self._idf(token)
            for node_name, counter in self._node_documents.items():
                tf = counter.get(token)
                if not tf:
                    continue
                scores[node_name] += q_weight * tf * idf

        results = []
        for node_name, score in scores.items():
            norm = self._node_norms.get(node_name)
            if not norm:
                continue
            cosine = score / (norm * query_norm)
            results.append({"name": node_name, "score": round(float(cosine), 4)})

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:max(1, limit)]
