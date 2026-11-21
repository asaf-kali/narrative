"""Social network analysis: who actually interacts with whom.

Directed interaction signals between two participants of the same group (source → target):
- replies:   source quoted one of target's messages
- reactions: source reacted to one of target's messages
- mentions:  source @mentioned target
- adjacency: source's turn came right after target's turn, decayed by exp(-Δt / τ)

The global graph adds `groups`: shared group membership, weighted 1 / (size - 1) per pair, so each
group adds exactly 1 to a member's strength and sharing a 4-person group counts far more than sharing
a 500-person one (a big group can't push its members to the top).

Edge weight is a weighted sum of the selected signals. On top of it every edge gets:
- lift:     observed interaction / interaction expected from both people's activity in each chat
            they share (configuration model, pooled over chats), so pairs that interact more than
            chance stand out even among quiet people
- backbone: survives the disparity filter (or is an endpoint's strongest tie), which prunes
            the hairball that heavy posters create

Nodes get communities and bridging (weighted betweenness). Communities come from Louvain, which
picks their number from the graph; a requested number uses greedy modularity merging instead.
"""

import logging
from collections.abc import Hashable
from enum import StrEnum
from typing import Any

import networkx as nx
import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from narrative.models.interactions import InteractionFrames

logger = logging.getLogger(__name__)

type Record = dict[Hashable, Any]  # one DataFrame row from to_dict("records")
type PeopleGraph = nx.Graph[str]


class Signal(StrEnum):
    REPLIES = "replies"
    REACTIONS = "reactions"
    MENTIONS = "mentions"
    ADJACENCY = "adjacency"
    GROUPS = "groups"


class NetworkNode(BaseModel):
    id: str
    label: str
    messages: int
    cluster: int
    strength: float  # weighted degree
    bridging: float  # normalized weighted betweenness
    groups: list[str] = []  # groups this person posted in; populated by the global graph
    chat_id: int | None = None  # this person's 1-on-1 chat, when there is one


class NetworkEdge(BaseModel):
    source: str
    target: str
    weight: float
    lift: float  # interaction vs. chance within shared chats; 0 = membership-only tie
    backbone: bool
    reciprocity: float  # min/max of the two directions' weights; 1 = perfectly mutual
    replies: int
    reactions: int
    mentions: int
    adjacency: float
    shared_groups: int


class NetworkGraph(BaseModel):
    nodes: list[NetworkNode]
    edges: list[NetworkEdge]
    communities: int
    signals: list[Signal]
    group_chats: dict[str, int] = {}  # group name -> chat id, for the names in `NetworkNode.groups`


class NetworkOptions(BaseModel):
    model_config = ConfigDict(frozen=True)

    signals: frozenset[Signal] = frozenset(Signal)
    max_nodes: int = 150
    include_me: bool = True
    allowed_ids: frozenset[str] | None = None  # restrict nodes to these people ("me" always allowed)
    clusters: int | None = None  # number of communities; None lets Louvain pick it
    private_chats: dict[str, int] = {}  # person id -> their 1-on-1 chat id


SIGNAL_WEIGHTS: dict[Signal, float] = {
    Signal.REPLIES: 3.0,
    Signal.MENTIONS: 3.0,
    Signal.REACTIONS: 1.0,
    Signal.ADJACENCY: 1.0,
    Signal.GROUPS: 10.0,
}
ADJACENCY_TAU_SECONDS = 600.0  # τ = 10 minutes
_ADJACENCY_MIN_VALUE = 0.01  # ignore turns more than ~46 minutes apart
_BACKBONE_ALPHA = 0.05  # disparity-filter significance level
_BETWEENNESS_SAMPLE = 200  # sample pivots above this many nodes
_BETWEENNESS_MIN_NODES = 3  # nobody can sit between fewer
_ME = "me"

_EVENT_COLUMNS = ["chat_row_id", "source", "target", "signal", "value"]
_EVENT_SIGNALS = [Signal.REPLIES, Signal.REACTIONS, Signal.MENTIONS, Signal.ADJACENCY]


def build_chat_network(df: pd.DataFrame, interactions: InteractionFrames, options: NetworkOptions) -> NetworkGraph:
    """Interaction graph of a single group chat."""
    signals = options.signals - {Signal.GROUPS}
    return _build_network(df=df, interactions=interactions, options=options, signals=signals)


def build_global_network(df: pd.DataFrame, interactions: InteractionFrames, options: NetworkOptions) -> NetworkGraph:
    """Interaction graph across all group chats, plus size-weighted shared group membership."""
    groups_df = df[df["is_group"]] if not df.empty else df
    return _build_network(df=groups_df, interactions=interactions, options=options, signals=options.signals)


# ── pipeline ──────────────────────────────────────────────────────────────────


def _build_network(
    df: pd.DataFrame, interactions: InteractionFrames, options: NetworkOptions, signals: frozenset[Signal]
) -> NetworkGraph:
    ordered_signals = sorted(signals)
    if df.empty:
        return NetworkGraph(nodes=[], edges=[], communities=0, signals=ordered_signals)

    annotated = _annotate(df=df, include_me=options.include_me)
    members = annotated[["chat_row_id", "_sender_id"]].drop_duplicates()
    events = _interaction_events(annotated=annotated, interactions=interactions, members=members)
    pairs = _aggregate_pairs(events=events, members=members, signals=signals)

    node_stats = _node_stats(annotated=annotated, pairs=pairs)
    candidates = _allowed_nodes(node_stats=node_stats, allowed_ids=options.allowed_ids)
    top_ids = set(candidates.head(options.max_nodes)["id"])
    pairs = pairs[pairs["a"].isin(top_ids) & pairs["b"].isin(top_ids)]
    pairs = _flag_backbone(pairs=pairs)

    graph = _to_networkx(pairs=pairs, node_ids=top_ids)
    clusters = _communities(graph=graph, count=options.clusters)
    bridging = _bridging(graph=graph)
    strength = _strength(pairs=pairs)

    selected = node_stats[node_stats["id"].isin(top_ids)]
    show_groups = Signal.GROUPS in signals
    nodes = [
        _to_node(record=record, clusters=clusters, bridging=bridging, strength=strength, show_groups=show_groups)
        for record in selected.to_dict("records")
    ]
    for node in nodes:
        node.chat_id = options.private_chats.get(node.id)
    edges = [_to_edge(record=record) for record in pairs.to_dict("records")]
    communities = len(set(clusters.values()))
    group_chats = _group_chats(annotated=annotated, nodes=nodes)
    return NetworkGraph(
        nodes=nodes, edges=edges, communities=communities, signals=ordered_signals, group_chats=group_chats
    )


def _annotate(df: pd.DataFrame, include_me: bool) -> pd.DataFrame:
    """Add a stable `_sender_id`: "me", else phone (1-on-1 falls back to the chat party), else name."""
    annotated = df.copy()
    phone = annotated["sender_phone"].fillna("").astype(str)
    chat_phone = annotated["chat_phone"].fillna("").astype(str)
    phone = phone.where((phone != "") | annotated["is_group"], chat_phone)
    name = annotated["sender_name"].fillna("unknown").astype(str)
    sender_id = phone.where(phone != "", name)
    is_me = annotated["from_me"] == 1
    annotated["_sender_id"] = sender_id.where(~is_me, _ME)
    if include_me:
        return annotated
    return annotated[~is_me]


def _interaction_events(
    annotated: pd.DataFrame, interactions: InteractionFrames, members: pd.DataFrame
) -> pd.DataFrame:
    """All directed events, restricted to pairs who both posted in the chat, self-loops dropped."""
    frames = [
        _reply_events(annotated=annotated, replies=interactions.replies),
        _reaction_events(annotated=annotated, reactions=interactions.reactions),
        _mention_events(annotated=annotated, mentions=interactions.mentions),
        _adjacency_events(annotated=annotated),
    ]
    non_empty = [f for f in frames if not f.empty]
    if not non_empty:
        return pd.DataFrame(columns=_EVENT_COLUMNS)
    events = pd.concat(non_empty, ignore_index=True)
    events = events[events["source"] != events["target"]]
    source_members = members.rename(columns={"_sender_id": "source"})
    target_members = members.rename(columns={"_sender_id": "target"})
    events = events.merge(source_members, on=["chat_row_id", "source"])
    return events.merge(target_members, on=["chat_row_id", "target"])


def _reply_events(annotated: pd.DataFrame, replies: pd.DataFrame) -> pd.DataFrame:
    """Reply author → quoted author."""
    if replies.empty:
        return pd.DataFrame(columns=_EVENT_COLUMNS)
    authors = annotated[["message_id", "chat_row_id", "_sender_id"]]
    merged = replies[["message_id", "quoted_id"]].merge(authors, on="message_id")
    return _events_frame(merged=merged, source_col="_sender_id", target_col="quoted_id", signal=Signal.REPLIES)


def _reaction_events(annotated: pd.DataFrame, reactions: pd.DataFrame) -> pd.DataFrame:
    """Reactor → reacted-message author."""
    if reactions.empty:
        return pd.DataFrame(columns=_EVENT_COLUMNS)
    authors = annotated[["message_id", "chat_row_id", "_sender_id"]]
    reacted = reactions[["parent_message_id", "reactor_id"]].rename(columns={"parent_message_id": "message_id"})
    merged = reacted.merge(authors, on="message_id")
    return _events_frame(merged=merged, source_col="reactor_id", target_col="_sender_id", signal=Signal.REACTIONS)


def _mention_events(annotated: pd.DataFrame, mentions: pd.DataFrame) -> pd.DataFrame:
    """Mentioning author → mentioned person."""
    if mentions.empty:
        return pd.DataFrame(columns=_EVENT_COLUMNS)
    authors = annotated[["message_id", "chat_row_id", "_sender_id"]]
    merged = mentions[["message_id", "mentioned_id"]].merge(authors, on="message_id")
    return _events_frame(merged=merged, source_col="_sender_id", target_col="mentioned_id", signal=Signal.MENTIONS)


def _adjacency_events(annotated: pd.DataFrame) -> pd.DataFrame:
    """Turn author → previous turn's author, weighted by exp(-gap / τ).

    A turn is a run of consecutive messages by one sender in one chat.
    """
    ordered = annotated.sort_values(["chat_row_id", "timestamp", "message_id"])
    chat = ordered["chat_row_id"]
    sender = ordered["_sender_id"]
    new_turn = (chat != chat.shift()) | (sender != sender.shift())
    turn_id = new_turn.cumsum()
    turns = ordered.groupby(turn_id).agg(
        chat_row_id=("chat_row_id", "first"),
        source=("_sender_id", "first"),
        start=("timestamp", "min"),
        end=("timestamp", "max"),
    )
    previous = turns.shift()
    same_chat = turns["chat_row_id"] == previous["chat_row_id"]
    gap_seconds = (turns["start"] - previous["end"]).dt.total_seconds()
    turns["target"] = previous["source"]
    turns["value"] = np.exp(-gap_seconds.clip(lower=0) / ADJACENCY_TAU_SECONDS)
    turns["signal"] = Signal.ADJACENCY
    linked = turns[same_chat & (turns["value"] >= _ADJACENCY_MIN_VALUE)]
    return linked[_EVENT_COLUMNS].reset_index(drop=True)


def _events_frame(merged: pd.DataFrame, source_col: str, target_col: str, signal: Signal) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "chat_row_id": merged["chat_row_id"],
            "source": merged[source_col].astype(str),
            "target": merged[target_col].astype(str),
            "signal": signal,
            "value": 1.0,
        }
    )


def _aggregate_pairs(events: pd.DataFrame, members: pd.DataFrame, signals: frozenset[Signal]) -> pd.DataFrame:
    """One row per unordered pair (a < b): per-signal totals, combined weight, reciprocity."""
    events = events.assign(weighted=events["value"] * _signal_weights(series=events["signal"], signals=signals))
    events["a"] = np.minimum(events["source"], events["target"])
    events["b"] = np.maximum(events["source"], events["target"])

    per_signal = events.pivot_table(index=["a", "b"], columns="signal", values="value", aggfunc="sum", fill_value=0)
    per_signal = per_signal.reindex(columns=_EVENT_SIGNALS, fill_value=0)
    per_signal.columns = [str(c) for c in per_signal.columns]

    forward = events["source"] == events["a"]
    directed = events.assign(
        forward=events["weighted"].where(forward, 0), backward=events["weighted"].where(~forward, 0)
    )
    directions = directed.groupby(["a", "b"])[["forward", "backward"]].sum()

    expected = _expected_weights(events=events)
    pairs = per_signal.join(directions, how="outer").join(expected, how="outer")
    membership = _membership_pairs(members=members)
    pairs = pairs.join(membership, how="outer").astype(float).fillna(0).reset_index()

    group_weight = SIGNAL_WEIGHTS[Signal.GROUPS] if Signal.GROUPS in signals else 0.0
    pairs["weight"] = pairs["forward"] + pairs["backward"] + group_weight * pairs["group_affinity"]
    high = pairs[["forward", "backward"]].max(axis=1)
    low = pairs[["forward", "backward"]].min(axis=1)
    pairs["reciprocity"] = (low / high.where(high > 0)).fillna(0)
    interaction = pairs["forward"] + pairs["backward"]
    pairs["lift"] = (interaction / pairs["expected"].where(pairs["expected"] > 0)).fillna(0)
    return pairs[pairs["weight"] > 0]


def _expected_weights(events: pd.DataFrame) -> pd.Series:
    """Per pair: Σ over chats of the interaction weight expected from both people's activity there.

    Within one chat, expected(a, b) = s_a · s_b / 2W (configuration model), with s a person's
    interaction strength in that chat and W the chat's total. Comparing inside each chat keeps
    small closed circles from looking "closer than chance" merely for being isolated.
    """
    chat_pairs = events.groupby(["chat_row_id", "a", "b"])["weighted"].sum().reset_index()
    side_a = chat_pairs[["chat_row_id", "a", "weighted"]].rename(columns={"a": "id"})
    side_b = chat_pairs[["chat_row_id", "b", "weighted"]].rename(columns={"b": "id"})
    both = pd.concat([side_a, side_b], ignore_index=True)
    strength = both.groupby(["chat_row_id", "id"])["weighted"].sum().reset_index()
    strength_a = strength.rename(columns={"id": "a", "weighted": "s_a"})
    strength_b = strength.rename(columns={"id": "b", "weighted": "s_b"})
    chat_pairs = chat_pairs.merge(strength_a, on=["chat_row_id", "a"]).merge(strength_b, on=["chat_row_id", "b"])
    total = chat_pairs.groupby("chat_row_id")["weighted"].transform("sum")
    chat_pairs["expected"] = chat_pairs["s_a"] * chat_pairs["s_b"] / (2 * total)
    return chat_pairs.groupby(["a", "b"])["expected"].sum()


def _signal_weights(series: pd.Series, signals: frozenset[Signal]) -> pd.Series:
    active = {signal: weight for signal, weight in SIGNAL_WEIGHTS.items() if signal in signals}
    return series.map(active).fillna(0.0)


def _membership_pairs(members: pd.DataFrame) -> pd.DataFrame:
    """Per unordered pair: shared group count and affinity Σ 1/(group size - 1)."""
    sizes = members.groupby("chat_row_id")["_sender_id"].transform("size")
    sized = members.assign(affinity=1 / (sizes.clip(lower=2) - 1))
    joined = sized.merge(members, on="chat_row_id", suffixes=("_a", "_b"))
    joined = joined[joined["_sender_id_a"] < joined["_sender_id_b"]]
    grouped = joined.groupby(["_sender_id_a", "_sender_id_b"]).agg(
        shared_groups=("chat_row_id", "size"), group_affinity=("affinity", "sum")
    )
    return grouped.rename_axis(["a", "b"])


def _allowed_nodes(node_stats: pd.DataFrame, allowed_ids: frozenset[str] | None) -> pd.DataFrame:
    if allowed_ids is None:
        return node_stats
    allowed = allowed_ids | {_ME}
    return node_stats[node_stats["id"].isin(allowed)]


def _node_stats(annotated: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Per sender: label, message count, groups, strength — sorted strongest first."""
    stats = annotated.groupby("_sender_id").agg(
        label=("sender_name", "first"),
        messages=("message_id", "count"),
        groups=("chat_name", lambda names: set(names.astype(str))),
    )
    strength = pd.Series(_strength(pairs=pairs), dtype=float)
    stats["strength"] = strength.reindex(stats.index).fillna(0.0)
    stats = stats.rename_axis("id").reset_index()
    return stats.sort_values(["strength", "messages"], ascending=False)


def _group_chats(annotated: pd.DataFrame, nodes: list[NetworkNode]) -> dict[str, int]:
    """Chat id of every group named on a node; a name shared by several groups maps to the busiest."""
    names = {group for node in nodes for group in node.groups}
    if not names:
        return {}
    chats = annotated[annotated["chat_name"].astype(str).isin(names)]
    busiest = chats.groupby(["chat_name", "chat_row_id"]).size().sort_values().reset_index()
    return {str(row["chat_name"]): int(row["chat_row_id"]) for row in busiest.to_dict("records")}


def _strength(pairs: pd.DataFrame) -> dict[str, float]:
    totals = _endpoint_weights(pairs=pairs).groupby("id")["weight"].sum()
    return {str(k): float(v) for k, v in totals.items()}


def _endpoint_weights(pairs: pd.DataFrame) -> pd.DataFrame:
    """Each edge twice, once per endpoint: columns `edge` (row label in pairs), `id`, `weight`."""
    side_a = pairs[["a", "weight"]].rename(columns={"a": "id"}).rename_axis("edge").reset_index()
    side_b = pairs[["b", "weight"]].rename(columns={"b": "id"}).rename_axis("edge").reset_index()
    return pd.concat([side_a, side_b], ignore_index=True)


def _flag_backbone(pairs: pd.DataFrame) -> pd.DataFrame:
    """Add the disparity-filter backbone flag."""
    if pairs.empty:
        return pairs.assign(backbone=pd.Series(dtype=bool))
    strength = pd.Series(_strength(pairs=pairs))
    degree = pd.concat([pairs["a"], pairs["b"]]).value_counts()
    s_a = pairs["a"].map(strength)
    s_b = pairs["b"].map(strength)

    alpha_a = _disparity(weight=pairs["weight"], strength=s_a, degree=pairs["a"].map(degree))
    alpha_b = _disparity(weight=pairs["weight"], strength=s_b, degree=pairs["b"].map(degree))
    significant = np.minimum(alpha_a, alpha_b) < _BACKBONE_ALPHA
    strongest = _is_strongest_tie(pairs=pairs)
    return pairs.assign(backbone=significant | strongest)


def _disparity(weight: pd.Series, strength: pd.Series, degree: pd.Series) -> pd.Series:
    """Disparity-filter p-value (Serrano et al. 2009); a node's only edge is always significant."""
    share = weight / strength
    alpha = (1 - share) ** (degree - 1)
    return alpha.where(degree > 1, 0.0)


def _is_strongest_tie(pairs: pd.DataFrame) -> pd.Series:
    """Flag each node's single heaviest tie (first wins on ties) — keeps every node attached."""
    ends = _endpoint_weights(pairs=pairs)
    strongest = ends.loc[ends.groupby("id")["weight"].idxmax(), "edge"]
    return pd.Series(pairs.index.isin(strongest), index=pairs.index)


def _to_networkx(pairs: pd.DataFrame, node_ids: set[str]) -> PeopleGraph:
    graph: PeopleGraph = nx.Graph()
    graph.add_nodes_from(node_ids)
    for record in pairs.to_dict("records"):
        weight = float(record["weight"])
        graph.add_edge(record["a"], record["b"], weight=weight, distance=1 / weight)
    return graph


def _communities(graph: PeopleGraph, count: int | None) -> dict[str, int]:
    if graph.number_of_edges() == 0:
        return dict.fromkeys(graph.nodes, 0)
    parts: list[set[str]] | list[frozenset[str]]
    if count is None:
        parts = nx.community.louvain_communities(graph, weight="weight", seed=0)
    else:
        # cutoff = best_n stops merging at exactly `size` communities, before or past the modularity peak.
        size = min(count, graph.number_of_nodes())
        parts = nx.community.greedy_modularity_communities(graph, weight="weight", cutoff=size, best_n=size)
    ordered = sorted(parts, key=len, reverse=True)
    return {node: index for index, part in enumerate(ordered) for node in part}


def _bridging(graph: PeopleGraph) -> dict[str, float]:
    """Betweenness with distance = 1 / weight; sampled for large graphs."""
    if graph.number_of_nodes() < _BETWEENNESS_MIN_NODES:
        return {}
    sample = _BETWEENNESS_SAMPLE if graph.number_of_nodes() > _BETWEENNESS_SAMPLE else None
    scores: dict[str, float] = nx.betweenness_centrality(graph, k=sample, weight="distance", seed=0)
    return scores


def _to_node(
    record: Record,
    clusters: dict[str, int],
    bridging: dict[str, float],
    strength: dict[str, float],
    show_groups: bool,
) -> NetworkNode:
    node_id = str(record["id"])
    groups = sorted(record["groups"]) if show_groups else []
    return NetworkNode(
        id=node_id,
        label=str(record["label"]),
        messages=int(record["messages"]),
        cluster=clusters.get(node_id, 0),
        strength=round(strength.get(node_id, 0.0), 3),
        bridging=round(bridging.get(node_id, 0.0), 4),
        groups=groups,
    )


def _to_edge(record: Record) -> NetworkEdge:
    return NetworkEdge(
        source=str(record["a"]),
        target=str(record["b"]),
        weight=round(float(record["weight"]), 3),
        lift=round(float(record["lift"]), 3),
        backbone=bool(record["backbone"]),
        reciprocity=round(float(record["reciprocity"]), 3),
        replies=int(record["replies"]),
        reactions=int(record["reactions"]),
        mentions=int(record["mentions"]),
        adjacency=round(float(record["adjacency"]), 3),
        shared_groups=int(record["shared_groups"]),
    )
