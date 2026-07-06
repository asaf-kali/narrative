"""Shared default parameters for the semantic search index pipeline.

Kept dependency-free (no FlagEmbedding/lancedb) so it is always importable, even
when the optional `semantic` extra is not installed. Both the CLI (`main.py`) and
the API route import these so full-index and per-chat re-index stay consistent.
"""

from __future__ import annotations

# Inactivity gap (seconds) that ends a session — a burst of activity becomes one session.
DEFAULT_GAP_SECONDS = 60 * 60 * 2  # 2 hours

# Embedding batch size.
DEFAULT_BATCH_SIZE = 32

# Messages read per DB page while streaming a chat.
DEFAULT_CHUNK_SIZE = 500

# Minimum text chars before a gap is allowed to end a session (keeps appending if below).
DEFAULT_MIN_SESSION_CHARS = 500

# Hard cap on messages per session — splits long bursts so each embedding vector
# stays topically focused instead of averaging many topics into one centroid.
DEFAULT_MAX_SESSION_MESSAGES = 30

# Candidate pool size pulled from the vector/text indexes before reranking.
DEFAULT_RERANK_CANDIDATES = 60
