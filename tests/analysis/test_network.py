import pandas as pd
from analysis.network import NetworkGraph, NetworkNode, build_coactivity_graph, build_global_graph, build_reaction_graph
from models.config import AnalysisConfig

_CONFIG = AnalysisConfig()


def _messages_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "message_id": [1, 2, 3, 4, 5],
            "from_me": [0, 0, 0, 0, 0],
            "sender_name": ["Alice", "Bob", "Alice", "Carol", "Bob"],
            "sender_phone": ["111", "222", "111", "333", "222"],
            "date": pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02", "2024-01-02", "2024-01-03"]).date,
            "is_group": [True] * 5,
            "chat_name": ["G1"] * 5,
        }
    )


def _node_map(graph: NetworkGraph) -> dict[str, NetworkNode]:
    return {n.id: n for n in graph.nodes}


def test_build_coactivity_graph_empty_df_returns_empty_graph() -> None:
    graph = build_coactivity_graph(pd.DataFrame(), _CONFIG)
    assert graph.nodes == []
    assert graph.edges == []
    assert graph.communities == 0
    assert graph.mode == "coactivity"


def test_build_coactivity_graph_edges_reflect_shared_active_days() -> None:
    graph = build_coactivity_graph(_messages_df(), _CONFIG)
    edges = {(e.source, e.target): e.weight for e in graph.edges}
    # Alice+Bob share 2024-01-01, Alice+Carol share 2024-01-02, Bob+Carol share no day.
    assert edges.get(("111", "222")) == 1
    assert edges.get(("111", "333")) == 1
    assert ("222", "333") not in edges
    assert ("333", "222") not in edges


def test_build_coactivity_graph_node_message_counts_and_centrality() -> None:
    graph = build_coactivity_graph(_messages_df(), _CONFIG)
    nodes = _node_map(graph)
    assert nodes["111"].messages == 2
    assert nodes["111"].centrality == 1.0  # Alice connects to both other nodes
    assert nodes["222"].centrality == 0.5


def test_build_coactivity_graph_connected_graph_is_one_community() -> None:
    graph = build_coactivity_graph(_messages_df(), _CONFIG)
    assert graph.communities == 1


def test_build_reaction_graph_empty_when_either_df_empty() -> None:
    graph = build_reaction_graph(_messages_df(), pd.DataFrame(), _CONFIG)
    assert graph.nodes == []
    assert graph.mode == "reactions"


def test_build_reaction_graph_directed_edges_reactor_to_author() -> None:
    reactions_df = pd.DataFrame(
        {
            "parent_message_id": [1, 1, 4],
            "reactor_id": ["222", "333", "111"],
            "reactor_name": ["Bob", "Carol", "Alice"],
        }
    )
    graph = build_reaction_graph(_messages_df(), reactions_df, _CONFIG)
    edges = {(e.source, e.target): e.weight for e in graph.edges}
    assert edges[("222", "111")] == 1  # Bob reacted to Alice's message 1
    assert edges[("333", "111")] == 1  # Carol reacted to Alice's message 1
    assert edges[("111", "333")] == 1  # Alice reacted to Carol's message 4


def test_build_reaction_graph_no_matching_messages_returns_empty() -> None:
    reactions_df = pd.DataFrame({"parent_message_id": [999], "reactor_id": ["111"], "reactor_name": ["Alice"]})
    graph = build_reaction_graph(_messages_df(), reactions_df, _CONFIG)
    assert graph.nodes == []


def test_build_global_graph_empty_df() -> None:
    graph = build_global_graph(pd.DataFrame())
    assert graph.nodes == []
    assert graph.communities == 0


def test_build_global_graph_groups_reflect_shared_chat_membership() -> None:
    graph = build_global_graph(_messages_df(), include_me=True)
    nodes = _node_map(graph)
    assert nodes["111"].groups == ["G1"]
    edges = {(e.source, e.target): e.weight for e in graph.edges}
    assert edges.get(("111", "222")) == 1
    assert edges.get(("111", "333")) == 1
    assert edges.get(("222", "333")) == 1


def test_build_global_graph_exclude_me_removes_me_from_groups() -> None:
    df = _messages_df()
    df.loc[0, "sender_name"] = "Me"
    df.loc[0, "sender_phone"] = ""
    df.loc[0, "from_me"] = 1
    graph = build_global_graph(df, include_me=False)
    ids = {n.id for n in graph.nodes}
    assert "me" not in ids
