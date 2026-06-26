"""LangGraph definition wiring the 5 StoryForge nodes together.

Flow: ANALYZE -> CLARIFY -> GENERATE -> REVIEW -> CREATE_ADO

The graph always interrupts before ``generate_node`` and before
``create_ado_node``. Whether a given pause is a genuine human-in-the-loop wait
or one that should be auto-resumed immediately (no ambiguities found /
review_mode disabled) is decided by the orchestration layer in
``pipeline.runner``, based on ``clarification_needed`` and ``review_mode`` in
the state at the time of the pause.
"""
from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from pipeline.nodes.analyze import analyze_node
from pipeline.nodes.clarify import clarify_node
from pipeline.nodes.create_ado import create_ado_node
from pipeline.nodes.generate import generate_node
from pipeline.nodes.review import review_node
from pipeline.state import StoryForgeState

NODE_ANALYZE = "analyze_node"
NODE_CLARIFY = "clarify_node"
NODE_GENERATE = "generate_node"
NODE_REVIEW = "review_node"
NODE_CREATE_ADO = "create_ado_node"


def build_graph():
    """Compile the StoryForge LangGraph with checkpointing and human-in-the-loop interrupts."""
    builder = StateGraph(StoryForgeState)

    builder.add_node(NODE_ANALYZE, analyze_node)
    builder.add_node(NODE_CLARIFY, clarify_node)
    builder.add_node(NODE_GENERATE, generate_node)
    builder.add_node(NODE_REVIEW, review_node)
    builder.add_node(NODE_CREATE_ADO, create_ado_node)

    builder.set_entry_point(NODE_ANALYZE)
    builder.add_edge(NODE_ANALYZE, NODE_CLARIFY)
    builder.add_edge(NODE_CLARIFY, NODE_GENERATE)
    builder.add_edge(NODE_GENERATE, NODE_REVIEW)
    builder.add_edge(NODE_REVIEW, NODE_CREATE_ADO)
    builder.add_edge(NODE_CREATE_ADO, END)

    checkpointer = MemorySaver()
    return builder.compile(
        checkpointer=checkpointer,
        interrupt_before=[NODE_GENERATE, NODE_CREATE_ADO],
    )


_graph = None


def get_graph():
    """Return a singleton compiled StoryForge graph instance."""
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
