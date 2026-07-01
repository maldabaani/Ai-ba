"""Node 3: generate User Stories, Dev Tasks, and Unit Test Tasks via Claude Sonnet."""
from __future__ import annotations

import logging

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from config import settings
from pipeline.nodes.json_response import extract_json, extract_text
from pipeline.state import StoryForgeState
from prompts.system_prompt import SYSTEM_PROMPT as PRODUCTION_SYSTEM_PROMPT
from prompts.system_prompt_selftest import SYSTEM_PROMPT as SELFTEST_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_OUTPUT_TOKENS = 8192

SYSTEM_PROMPT = (
    SELFTEST_SYSTEM_PROMPT if settings.PROMPT_VARIANT == "selftest" else PRODUCTION_SYSTEM_PROMPT
)

_llm = ChatOllama(
    model=settings.OLLAMA_LLM_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    num_predict=MAX_OUTPUT_TOKENS,
)


def _format_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "(none retrieved)"
    return "\n---\n".join(
        f"Source: {c['metadata'].get('source', 'unknown')} "
        f"[type={c['metadata'].get('type', 'unknown')}, "
        f"layer={c['metadata'].get('layer', 'unknown')}, "
        f"module={c['metadata'].get('module', 'unknown')}]\n{c['content']}"
        for c in chunks
    )


def _format_clarifications(answers: dict) -> str:
    if not answers:
        return "(no clarifications were needed)"
    return "\n".join(f"Q: {question}\nA: {answer}" for question, answer in answers.items())


def _build_user_message(state: StoryForgeState) -> str:
    context = state["retrieved_context"]
    return (
        f"## Project Metadata\n"
        f"PPM Number: {state['ppm_number']}\n"
        f"PPM Name: {state['ppm_name']}\n"
        f"System Name: {state['system_name']}\n\n"
        f"## Solution Design Document\n{state['solution_doc_text']}\n\n"
        f"## Retrieved User Manual Context\n{_format_chunks(context.get('manuals', []))}\n\n"
        f"## Retrieved Codebase Context\n{_format_chunks(context.get('codebase', []))}\n\n"
        f"## Retrieved JPA Entity Context\n{_format_chunks(context.get('entities', []))}\n\n"
        f"## Clarification Answers\n{_format_clarifications(state['clarification_answers'])}\n"
    )


def _parse_stories(raw_text: str) -> list[dict]:
    parsed = extract_json(raw_text)
    if not isinstance(parsed, list):
        raise ValueError("Expected a JSON array of stories")
    return parsed


async def generate_node(state: StoryForgeState) -> StoryForgeState:
    """Send the SDD + RAG context + clarification answers to Claude and parse stories."""
    try:
        response = await _llm.ainvoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=_build_user_message(state)),
            ]
        )
        stories = _parse_stories(extract_text(response.content))
    except Exception as exc:  # noqa: BLE001 - surfaced to caller via state errors
        logger.exception("generate_node failed")
        return {
            **state,
            "errors": state["errors"] + [f"generate_node: {exc}"],
            "status": "error",
        }

    return {
        **state,
        "generated_stories": stories,
        "status": "reviewing" if state["review_mode"] else "creating",
    }
