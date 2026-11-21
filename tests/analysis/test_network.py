import math

import pandas as pd
import pytest
from pydantic import BaseModel

from narrative.analysis.network import (
    ADJACENCY_TAU_SECONDS,
    SIGNAL_WEIGHTS,
    NetworkEdge,
    NetworkGraph,
    NetworkNode,
    NetworkOptions,
    Signal,
    build_chat_network,
    build_global_network,
)
from narrative.models.interactions import InteractionFrames

type Link = tuple[int, str]  # (message_id, person id)
type Scenario = tuple[pd.DataFrame, InteractionFrames]

_T0 = pd.Timestamp("2024-01-10 09:00", tz="UTC")
_HOUR = 3600


class Msg(BaseModel):
    """One test message: `sender` is a phone, or "me"."""

    message_id: int
    sender: str
    seconds: float
    chat: int = 1
    is_group: bool = True


def _messages_df(messages: list[Msg]) -> pd.DataFrame:
    rows = [
        {
            "message_id": m.message_id,
            "chat_row_id": m.chat,
            "from_me": int(m.sender == "me"),
            "sender_name": "Me" if m.sender == "me" else f"name-{m.sender}",
            "sender_phone": "" if m.sender == "me" else m.sender,
            "chat_phone": f"chat{m.chat}",
            "timestamp": _T0 + pd.to_timedelta(m.seconds, unit="s"),
            "is_group": m.is_group,
            "chat_name": f"G{m.chat}",
        }
        for m in messages
    ]
    return pd.DataFrame(rows)


def _frames(
    replies: list[Link] | None = None,
    reactions: list[Link] | None = None,
    mentions: list[Link] | None = None,
) -> InteractionFrames:
    """Build interaction tables from (message_id, person) links.

    replies: (reply message_id, quoted_id); reactions: (parent message_id, reactor_id);
    mentions: (message_id, mentioned_id).
    """
    return InteractionFrames(
        replies=pd.DataFrame(replies or [], columns=["message_id", "quoted_id"]),
        reactions=pd.DataFrame(reactions or [], columns=["parent_message_id", "reactor_id"]),
        mentions=pd.DataFrame(mentions or [], columns=["message_id", "mentioned_id"]),
    )


def _edge(graph: NetworkGraph, a: str, b: str) -> NetworkEdge | None:
    pair = {a, b}
    return next((e for e in graph.edges if {e.source, e.target} == pair), None)


def _nodes(graph: NetworkGraph) -> dict[str, NetworkNode]:
    return {n.id: n for n in graph.nodes}


# Alice (111) and Bob (222) talk; Carol (333) posts hours later.
_CHAT = [
    Msg(message_id=1, sender="111", seconds=0),
    Msg(message_id=2, sender="222", seconds=60),
    Msg(message_id=3, sender="111", seconds=120),
    Msg(message_id=4, sender="333", seconds=5 * _HOUR),
]
_ONLY = NetworkOptions(signals=frozenset({Signal.REPLIES, Signal.REACTIONS, Signal.MENTIONS}))


def test_chat_network_empty_df_returns_empty_graph() -> None:
    graph = build_chat_network(df=pd.DataFrame(), interactions=_frames(), options=NetworkOptions())
    assert graph.nodes == []
    assert graph.edges == []
    assert graph.communities == 0
    assert Signal.GROUPS not in graph.signals


def test_chat_network_counts_replies_reactions_and_mentions() -> None:
    frames = _frames(replies=[(2, "111"), (3, "222")], reactions=[(1, "222")], mentions=[(2, "111")])
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=frames, options=_ONLY)
    edge = _edge(graph, "111", "222")
    assert edge is not None
    assert (edge.replies, edge.reactions, edge.mentions) == (2, 1, 1)
    expected = 2 * SIGNAL_WEIGHTS[Signal.REPLIES] + SIGNAL_WEIGHTS[Signal.REACTIONS] + SIGNAL_WEIGHTS[Signal.MENTIONS]
    assert edge.weight == pytest.approx(expected)


def test_chat_network_adjacency_decays_with_gap() -> None:
    options = NetworkOptions(signals=frozenset({Signal.ADJACENCY}))
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=_frames(), options=options)
    edge = _edge(graph, "111", "222")
    assert edge is not None
    # Two turn changes, each 60s apart.
    assert edge.adjacency == pytest.approx(2 * math.exp(-60 / ADJACENCY_TAU_SECONDS), abs=1e-3)
    # Carol posted 5 hours after Alice: too far apart to count.
    assert _edge(graph, "111", "333") is None


def test_chat_network_consecutive_messages_form_one_turn() -> None:
    messages = [
        Msg(message_id=1, sender="111", seconds=0),
        Msg(message_id=2, sender="111", seconds=10),
        Msg(message_id=3, sender="111", seconds=20),
        Msg(message_id=4, sender="222", seconds=20),
    ]
    options = NetworkOptions(signals=frozenset({Signal.ADJACENCY}))
    graph = build_chat_network(df=_messages_df(messages), interactions=_frames(), options=options)
    edge = _edge(graph, "111", "222")
    assert edge is not None
    assert edge.adjacency == pytest.approx(1.0)  # gap measured from the turn's last message
    assert len(graph.edges) == 1


def test_chat_network_unselected_signals_are_reported_but_not_weighted() -> None:
    options = NetworkOptions(signals=frozenset({Signal.REPLIES}))
    frames = _frames(replies=[(2, "111")])
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=frames, options=options)
    edge = _edge(graph, "111", "222")
    assert edge is not None
    assert edge.adjacency > 0
    assert edge.weight == pytest.approx(SIGNAL_WEIGHTS[Signal.REPLIES])
    assert graph.signals == [Signal.REPLIES]


def test_chat_network_reciprocity_reflects_direction_balance() -> None:
    one_way = build_chat_network(df=_messages_df(_CHAT), interactions=_frames(replies=[(2, "111")]), options=_ONLY)
    mutual = build_chat_network(
        df=_messages_df(_CHAT), interactions=_frames(replies=[(2, "111"), (3, "222")]), options=_ONLY
    )
    one_way_edge = _edge(one_way, "111", "222")
    mutual_edge = _edge(mutual, "111", "222")
    assert one_way_edge is not None
    assert mutual_edge is not None
    assert one_way_edge.reciprocity == 0
    assert mutual_edge.reciprocity == 1


def test_chat_network_drops_interactions_with_non_participants_and_self() -> None:
    frames = _frames(mentions=[(1, "999")], reactions=[(1, "111")])
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=frames, options=_ONLY)
    assert graph.edges == []
    assert "999" not in _nodes(graph)


def test_chat_network_includes_me() -> None:
    messages = [*_CHAT, Msg(message_id=5, sender="me", seconds=5 * _HOUR + 30)]
    graph = build_chat_network(df=_messages_df(messages), interactions=_frames(), options=NetworkOptions())
    assert "me" in _nodes(graph)
    assert _edge(graph, "me", "333") is not None


def test_chat_network_max_nodes_keeps_strongest() -> None:
    frames = _frames(replies=[(2, "111"), (3, "222")])
    options = _ONLY.model_copy(update={"max_nodes": 2})
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=frames, options=options)
    assert set(_nodes(graph)) == {"111", "222"}


def test_chat_network_scores_lift_and_keeps_every_node_on_backbone() -> None:
    graph = build_chat_network(df=_messages_df(_CHAT), interactions=_frames(), options=NetworkOptions())
    assert graph.edges
    assert all(e.lift > 0 for e in graph.edges)
    on_backbone = {node for e in graph.edges if e.backbone for node in (e.source, e.target)}
    connected = {node for e in graph.edges for node in (e.source, e.target)}
    assert on_backbone == connected


def _two_cliques_with_bridge() -> Scenario:
    """Cliques {a1,a2,a3} and {b1,b2,b3}; x replies once to a1 and once to b1."""
    people = ["a1", "a2", "a3", "b1", "b2", "b3", "x"]
    messages = [Msg(message_id=i, sender=p, seconds=i * _HOUR) for i, p in enumerate(people, start=1)]
    by_sender = {m.sender: m.message_id for m in messages}
    replies: list[Link] = []
    for clique in (["a1", "a2", "a3"], ["b1", "b2", "b3"]):
        replies += [(by_sender[src], dst) for src in clique for dst in clique if src != dst for _ in range(5)]
    replies += [(by_sender["x"], "a1"), (by_sender["x"], "b1")]
    return _messages_df(messages), _frames(replies=replies)


def test_chat_network_detects_communities_and_bridges() -> None:
    df, frames = _two_cliques_with_bridge()
    graph = build_chat_network(df=df, interactions=frames, options=_ONLY)
    nodes = _nodes(graph)
    assert nodes["a1"].cluster == nodes["a2"].cluster == nodes["a3"].cluster
    assert nodes["b1"].cluster == nodes["b2"].cluster == nodes["b3"].cluster
    assert nodes["a1"].cluster != nodes["b1"].cluster
    top_bridges = sorted(nodes.values(), key=lambda n: n.bridging, reverse=True)[:3]
    assert {n.id for n in top_bridges} == {"x", "a1", "b1"}


def test_global_network_weights_shared_small_groups_above_large_ones() -> None:
    small = [Msg(message_id=i, sender=s, seconds=i * _HOUR, chat=1) for i, s in enumerate(["111", "222"], start=1)]
    big_senders = ["111", "333", *[f"9{i}" for i in range(20)]]
    big = [Msg(message_id=100 + i, sender=s, seconds=i * _HOUR, chat=2) for i, s in enumerate(big_senders)]
    options = NetworkOptions(signals=frozenset({Signal.GROUPS}))
    graph = build_global_network(df=_messages_df([*small, *big]), interactions=_frames(), options=options)
    small_pair = _edge(graph, "111", "222")
    big_pair = _edge(graph, "111", "333")
    assert small_pair is not None
    assert big_pair is not None
    assert small_pair.shared_groups == big_pair.shared_groups == 1
    assert small_pair.weight > big_pair.weight
    assert _nodes(graph)["111"].groups == ["G1", "G2"]


def test_global_network_aggregates_across_groups_and_ignores_direct_chats() -> None:
    messages = [
        Msg(message_id=1, sender="111", seconds=0, chat=1),
        Msg(message_id=2, sender="222", seconds=60, chat=1),
        Msg(message_id=3, sender="111", seconds=0, chat=2),
        Msg(message_id=4, sender="222", seconds=60, chat=2),
        Msg(message_id=5, sender="333", seconds=0, chat=3, is_group=False),
        Msg(message_id=6, sender="me", seconds=60, chat=3, is_group=False),
    ]
    frames = _frames(replies=[(2, "111"), (4, "111")])
    graph = build_global_network(df=_messages_df(messages), interactions=frames, options=NetworkOptions())
    edge = _edge(graph, "111", "222")
    assert edge is not None
    assert edge.replies == 2
    assert edge.shared_groups == 2
    assert set(_nodes(graph)) == {"111", "222"}


def test_global_network_can_exclude_me() -> None:
    messages = [
        Msg(message_id=1, sender="111", seconds=0),
        Msg(message_id=2, sender="me", seconds=60),
        Msg(message_id=3, sender="222", seconds=120),
    ]
    options = NetworkOptions(include_me=False)
    graph = build_global_network(df=_messages_df(messages), interactions=_frames(), options=options)
    assert "me" not in _nodes(graph)
    assert all("me" not in (e.source, e.target) for e in graph.edges)


def test_global_network_lift_is_measured_within_each_group() -> None:
    """An isolated dyad isn't 'closer than chance' just because nobody else is around."""
    messages = [
        Msg(message_id=1, sender="111", seconds=0, chat=1),
        Msg(message_id=2, sender="222", seconds=60, chat=1),
        *[Msg(message_id=10 + i, sender=s, seconds=i * 60, chat=2) for i, s in enumerate(["333", "444", "555"] * 3)],
    ]
    options = NetworkOptions(signals=frozenset({Signal.ADJACENCY}))
    graph = build_global_network(df=_messages_df(messages), interactions=_frames(), options=options)
    dyad = _edge(graph, "111", "222")
    assert dyad is not None
    assert dyad.lift == pytest.approx(2.0)


def test_global_network_membership_only_ties_have_zero_lift() -> None:
    messages = [Msg(message_id=1, sender="111", seconds=0), Msg(message_id=2, sender="222", seconds=5 * _HOUR)]
    options = NetworkOptions(signals=frozenset({Signal.GROUPS}))
    graph = build_global_network(df=_messages_df(messages), interactions=_frames(), options=options)
    edge = _edge(graph, "111", "222")
    assert edge is not None
    assert edge.lift == 0
