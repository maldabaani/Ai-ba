"""Node 2: detect ambiguities in the SDD and pause the graph for human clarification."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from config import settings
from pipeline.nodes.json_response import extract_json, extract_text
from pipeline.state import StoryForgeState

logger = logging.getLogger(__name__)

_llm = ChatOllama(
    model=settings.OLLAMA_LLM_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    num_predict=2048,
    format="json",
)

CLARIFY_SYSTEM_PROMPT = """You are a senior business analyst reviewing a Solution Design Document (SDD) before user stories are generated from it.

Your job is to identify anything in the SDD that is unclear, missing, or ambiguous and would cause two developers to implement the feature differently. Focus on:

- Undefined values: status codes, error codes, or field values that are referenced but never defined
- Missing technical details: API endpoints, request/response payloads, or data structures that are mentioned but not fully specified
- Vague requirements: statements that are too broad or contradictory to implement precisely
- Conflicts with existing context: requirements that appear to clash with behavior described in the retrieved codebase, user manual, or JPA entity context (cite the source file name when raising these)

For each issue you find, write a single clear question that a developer would need answered before writing code. Be specific — reference the exact section, field, or requirement that is unclear.

Only ask questions about genuine blockers. Do not ask about writing style, grammar, or completeness of documentation.

You must respond with a JSON object in this exact format:
{"ambiguities": ["question 1", "question 2"]}

If everything is clear enough to implement, respond with:
{"ambiguities": []}"""


def _build_user_message(state: StoryForgeState) -> str:
    context = state["retrieved_context"]

    def _format_chunks(chunks: list[dict]) -> str:
        if not chunks:
            return "(none retrieved)"
        return "\n---\n".join(
            f"Source: {c['metadata'].get('source', 'unknown')}\n{c['content']}"
            for c in chunks
        )

    return (
        f"## Solution Design Document\n{state['solution_doc_text']}\n\n"
        f"## Retrieved User Manual Context\n{_format_chunks(context.get('manuals', []))}\n\n"
        f"## Retrieved Codebase Context\n{_format_chunks(context.get('codebase', []))}\n\n"
        f"## Retrieved JPA Entity Context\n{_format_chunks(context.get('entities', []))}\n"
    )


def _parse_ambiguities(raw_text: str) -> list[str]:
    parsed = extract_json(raw_text)
    # Direct list: ["q1", "q2"]
    if isinstance(parsed, list):
        return [str(item) for item in parsed if item]
    if isinstance(parsed, dict):
        # Expected: {"ambiguities": [...]}
        value = parsed.get("ambiguities")
        if isinstance(value, list):
            return [str(item) for item in value if item]
        # Wrapped: {"result": {"ambiguities": [...]}} etc.
        for key in ("result", "response", "output", "data"):
            inner = parsed.get(key)
            if isinstance(inner, dict):
                value = inner.get("ambiguities")
                if isinstance(value, list):
                    return [str(item) for item in value if item]
    return []


async def clarify_node(state: StoryForgeState) -> StoryForgeState:
    """Ask the LLM to flag in-scope ambiguities; pause the graph if any are found."""
    try:
        response = await _llm.ainvoke(
            [
                SystemMessage(content=CLARIFY_SYSTEM_PROMPT),
                HumanMessage(content=_build_user_message(state)),
            ]
        )
        raw_text = extract_text(response.content)
        logger.info("clarify_node raw LLM output (first 500 chars): %s", raw_text[:500])
        ambiguities = _parse_ambiguities(raw_text)
    except Exception as exc:  # noqa: BLE001 - surfaced to caller via state errors
        logger.exception("clarify_node failed; proceeding without clarification")
        raw_for_error = locals().get("raw_text", "(response not yet captured)")
        return {
            **state,
            "clarification_needed": False,
            "clarification_questions": [],
            "errors": state["errors"] + [
                f"clarify_node: {exc} | raw={raw_for_error[:200]}"
            ],
        }

    if ambiguities:
        return {
            **state,
            "clarification_needed": True,
            "clarification_questions": ambiguities,
            "status": "clarifying",
        }

    return {
        **state,
        "clarification_needed": False,
        "clarification_questions": [],
        "status": "generating",
    }
