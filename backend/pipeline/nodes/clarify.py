"""Node 2: detect ambiguities in the SDD and pause the graph for human clarification."""
from __future__ import annotations

import json
import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from config import settings
from pipeline.state import StoryForgeState

logger = logging.getLogger(__name__)

_llm = ChatAnthropic(
    model=settings.CLAUDE_MODEL, api_key=settings.ANTHROPIC_API_KEY, max_tokens=2048
)


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content
    return "".join(
        block.get("text", "") for block in content if isinstance(block, dict)
    )

CLARIFY_SYSTEM_PROMPT = """You are a senior business analyst reviewing a Solution \
Design Document (SDD) before user stories are generated from it. Your ONLY job is \
to find ambiguities in these four categories:

1. Undefined status values or error codes
2. Missing API endpoint paths or payload structures
3. Unspecified middleware queue/topic names
4. Implied DB changes not confirmed in the retrieved JPA entities

Do NOT raise ambiguities outside these four categories. Do NOT comment on writing \
quality, formatting, or anything not directly blocking accurate story generation.

Respond with ONLY valid JSON, no markdown fences, no preamble, matching exactly:
{"ambiguities": ["question 1", "question 2"]}

If there are no ambiguities in scope, respond with {"ambiguities": []}.
"""


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
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.split("\n", 1)[-1] if "\n" in cleaned else cleaned
    parsed = json.loads(cleaned)
    return parsed.get("ambiguities", [])


async def clarify_node(state: StoryForgeState) -> StoryForgeState:
    """Ask Claude to flag in-scope ambiguities; pause the graph if any are found."""
    try:
        response = await _llm.ainvoke(
            [
                SystemMessage(content=CLARIFY_SYSTEM_PROMPT),
                HumanMessage(content=_build_user_message(state)),
            ]
        )
        ambiguities = _parse_ambiguities(_extract_text(response.content))
    except Exception as exc:  # noqa: BLE001 - surfaced to caller via state errors
        logger.exception("clarify_node failed; proceeding without clarification")
        return {
            **state,
            "clarification_needed": False,
            "clarification_questions": [],
            "errors": state["errors"] + [f"clarify_node: {exc}"],
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
