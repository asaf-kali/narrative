"""Social network analysis — pure-Python, no external graph library required.

Algorithms used:
- Degree centrality: degree(v) / (n-1)
- Community detection: weighted label propagation (iterative, O(n·m) per pass)
"""

import itertools
import logging
import random

import pandas as pd
from models.config import AnalysisConfig
from pydantic import BaseModel

logger = logging.getLogger(__name__)

_MAX_PARTICIPANTS = 200  # guard against O(N²) blow-up
_LP_MAX_ITER = 30  # label propagation iteration cap

# Adjacency type: node_id → {neighbor_id → weight}
Adjacency = dict[str, dict[str, int]]


class NetworkNode(BaseModel):
    id: str
    label: str
    messages: int
    cluster: int
    centrality: float
    groups: list[str] = []  # groups this person appears in; populated by global graph


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: int


class NetworkGraph(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    communities: int
    mode: str


def build_coactivity_graph(df: pd.DataFrame, _config: AnalysisConfig) -> NetworkGraph:
    """Nodes = participants; edge weight = shared active days between each pair."""
    if df.empty:
        return NetworkGraph(nodes=[], edges=[], communities=0, mode="coactivity")

    sender_stats, annotated = _sender_stats(df)
    if len(sender_stats) > _MAX_PARTICIPANTS:
        sender_stats = sender_stats.nlargest(_MAX_PARTICIPANTS, "messages")
        logger.warning(f"Network: truncated to top {_MAX_PARTICIPANTS} participants by message count")

    active_days: dict[str, set[object]] = {
        row["id"]: set(annotated[annotated["_sender_id"] == row["id"]]["date"]) for _, row in sender_stats.iterrows()
    }

    raw_edges: list[tuple[str, str, int]] = []
    for (_, a), (_, b) in itertools.combinations(sender_stats.iterrows(), 2):
        weight = len(active_days[a["id"]] & active_days[b["id"]])
        if weight > 0:
            raw_edges.append((a["id"], b["id"], weight))

    id_to_label: dict[str, str] = {str(k): str(v) for k, v in sender_stats.set_index("id")["label"].to_dict().items()}
    id_to_msgs: dict[str, int] = {str(k): int(v) for k, v in sender_stats.set_index("id")["messages"].to_dict().items()}
    adj = _build_undirected_adj(sender_stats["id"].tolist(), raw_edges)

    return _finalise(adj=adj, raw_edges=raw_edges, id_to_label=id_to_label, id_to_msgs=id_to_msgs, mode="coactivity")


def build_reaction_graph(df: pd.DataFrame, reactions_df: pd.DataFrame, _config: AnalysisConfig) -> NetworkGraph:
    """Directed edges: reactor → message-author, weight = reaction count."""
    if df.empty or reactions_df.empty:
        return NetworkGraph(nodes=[], edges=[], communities=0, mode="reactions")

    sender_stats, annotated = _sender_stats(df)

    msg_info = (
        annotated[["message_id", "_sender_id", "sender_name"]]
        .drop_duplicates("message_id")
        .rename(columns={"_sender_id": "author_id", "sender_name": "author_label"})
    )

    merged = reactions_df.merge(msg_info, left_on="parent_message_id", right_on="message_id", how="inner")
    if merged.empty:
        return NetworkGraph(nodes=[], edges=[], communities=0, mode="reactions")

    id_to_label_df = (
        annotated[["_sender_id", "sender_name"]]
        .drop_duplicates("_sender_id")
        .set_index("_sender_id")["sender_name"]
        .to_dict()
    )
    merged["reactor_id"] = merged["sender_phone"].apply(lambda p: p or "me")

    edge_counts = merged.groupby(["reactor_id", "author_id"]).size().reset_index(name="weight")

    id_to_msgs: dict[str, int] = {str(k): int(v) for k, v in sender_stats.set_index("id")["messages"].to_dict().items()}
    id_to_label: dict[str, str] = {str(k): str(v) for k, v in sender_stats.set_index("id")["label"].to_dict().items()}

    all_ids = list(set(edge_counts["reactor_id"]) | set(edge_counts["author_id"]))
    raw_edges: list[tuple[str, str, int]] = [
        (str(row["reactor_id"]), str(row["author_id"]), int(row["weight"])) for _, row in edge_counts.iterrows()
    ]

    # Use undirected adjacency for community detection
    adj = _build_undirected_adj(all_ids, raw_edges)

    # Merge label sources
    merged_labels = {nid: id_to_label.get(nid, id_to_label_df.get(nid, nid)) for nid in all_ids}

    return _finalise(adj=adj, raw_edges=raw_edges, id_to_label=merged_labels, id_to_msgs=id_to_msgs, mode="reactions")


def build_global_graph(df: pd.DataFrame, include_me: bool = True) -> NetworkGraph:
    """Global contact graph across all chats.

    Nodes = every contact who sent at least one message in any group.
    Edges = shared group membership; weight = number of groups both people appear in.
    """
    if df.empty:
        return NetworkGraph(nodes=[], edges=[], communities=0, mode="coactivity")

    _, annotated = _sender_stats(df)

    # Whole-corpus sender stats for node sizing
    all_stats = (
        annotated.groupby("_sender_id")
        .agg(label=("sender_name", "first"), messages=("message_id", "count"))
        .reset_index()
        .rename(columns={"_sender_id": "id"})
    )
    id_to_label: dict[str, str] = {str(k): str(v) for k, v in all_stats.set_index("id")["label"].to_dict().items()}
    id_to_msgs: dict[str, int] = {str(k): int(v) for k, v in all_stats.set_index("id")["messages"].to_dict().items()}

    # Group membership: group_name → set of sender_ids
    group_df = annotated[annotated["is_group"]]
    group_members: dict[str, set[str]] = {}
    for gname, grp in group_df.groupby("chat_name"):
        members = {str(sid) for sid in grp["_sender_id"].unique()}
        if not include_me:
            members.discard("me")
        group_members[str(gname)] = members

    # Invert: sender_id → set of group names
    person_groups: dict[str, set[str]] = {}
    for gname, members in group_members.items():
        for sid in members:
            person_groups.setdefault(sid, set()).add(gname)

    # Build edges: for each group, connect all pairs of members (+1 shared group)
    edge_weights: dict[tuple[str, str], int] = {}
    for members in group_members.values():
        for a, b in itertools.combinations(sorted(members), 2):
            key = (a, b)
            edge_weights[key] = edge_weights.get(key, 0) + 1

    raw_edges: list[tuple[str, str, int]] = [(a, b, w) for (a, b), w in edge_weights.items()]
    people = list(person_groups.keys())
    adj = _build_undirected_adj(people, raw_edges)

    community_map = _label_propagation(adj) if adj else {}
    centrality = _degree_centrality(adj)

    nodes = [
        NetworkNode(
            id=n,
            label=id_to_label.get(n, n),
            messages=int(id_to_msgs.get(n, 0)),
            cluster=community_map.get(n, 0),
            centrality=round(centrality.get(n, 0.0), 4),
            groups=sorted(person_groups.get(n, set())),
        )
        for n in adj
    ]
    edges = [NetworkEdge(source=a, target=b, weight=w) for a, b, w in raw_edges]

    return NetworkGraph(
        nodes=nodes,
        edges=edges,
        communities=len(set(community_map.values())),
        mode="coactivity",
    )


# ── private helpers ───────────────────────────────────────────────────────────


def _sender_id(row: pd.Series) -> str:  # type: ignore[type-arg]
    if row.get("from_me") == 1 or row.get("sender_name") == "Me":
        return "me"
    return str(row.get("sender_phone") or "") or str(row.get("sender_name", "unknown"))


def _sender_stats(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (stats, annotated_df) where annotated_df has the _sender_id column added."""
    annotated = df.copy()
    annotated["_sender_id"] = annotated.apply(_sender_id, axis=1)
    stats = (
        annotated.groupby("_sender_id")
        .agg(label=("sender_name", "first"), messages=("message_id", "count"))
        .reset_index()
        .rename(columns={"_sender_id": "id"})
    )
    return stats, annotated


def _build_undirected_adj(nodes: list[str], edges: list[tuple[str, str, int]]) -> Adjacency:
    adj: Adjacency = {n: {} for n in nodes}
    for src, dst, w in edges:
        if src not in adj:
            adj[src] = {}
        if dst not in adj:
            adj[dst] = {}
        adj[src][dst] = adj[src].get(dst, 0) + w
        adj[dst][src] = adj[dst].get(src, 0) + w
    return adj


def _degree_centrality(adj: Adjacency) -> dict[str, float]:
    n = len(adj)
    if n <= 1:
        return dict.fromkeys(adj, 0.0)
    return {v: len(neighbors) / (n - 1) for v, neighbors in adj.items()}


def _label_propagation(adj: Adjacency) -> dict[str, int]:
    """Weighted label propagation community detection."""
    labels: dict[str, int] = {v: i for i, v in enumerate(adj)}
    nodes = list(adj.keys())

    for _ in range(_LP_MAX_ITER):
        random.shuffle(nodes)
        changed = False
        for v in nodes:
            if not adj[v]:
                continue
            votes: dict[int, int] = {}
            for neighbor, weight in adj[v].items():
                lbl = labels[neighbor]
                votes[lbl] = votes.get(lbl, 0) + weight
            best = max(votes, key=lambda x: votes[x])
            if labels[v] != best:
                labels[v] = best
                changed = True
        if not changed:
            break

    unique = {lbl: i for i, lbl in enumerate(sorted(set(labels.values())))}
    return {v: unique[lbl] for v, lbl in labels.items()}


def _finalise(
    adj: Adjacency,
    raw_edges: list[tuple[str, str, int]],
    id_to_label: dict[str, str],
    id_to_msgs: dict[str, int],
    mode: str,
) -> NetworkGraph:
    community_map = _label_propagation(adj) if adj else {}
    centrality = _degree_centrality(adj)

    nodes = [
        NetworkNode(
            id=n,
            label=id_to_label.get(n, n),
            messages=int(id_to_msgs.get(n, 0)),
            cluster=community_map.get(n, 0),
            centrality=round(centrality.get(n, 0.0), 4),
        )
        for n in adj
    ]

    edges = [NetworkEdge(source=s, target=t, weight=w) for s, t, w in raw_edges]

    return NetworkGraph(
        nodes=nodes,
        edges=edges,
        communities=len(set(community_map.values())),
        mode=mode,
    )
