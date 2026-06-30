"""Node 5 (notion mode): create one Notion page per Epic in the configured
StoryForge database, with Dev Tasks and Unit Test Tasks rendered as nested
blocks within that page.

Mirrors export_document_node's content structure and create_ado_node's
error-handling convention (one story failing doesn't abort the rest) so all
three output modes stay interchangeable via settings.OUTPUT_MODE.
"""
from __future__ import annotations

import datetime
import logging

from notion_export.client import get_notion_export_client
from pipeline.state import StoryForgeState

logger = logging.getLogger(__name__)

MAX_RICH_TEXT_CHARS = 2000


def _rich_text(text: str) -> list[dict]:
    text = str(text)
    chunks = [text[i : i + MAX_RICH_TEXT_CHARS] for i in range(0, len(text), MAX_RICH_TEXT_CHARS)]
    chunks = chunks or [""]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def _heading_block(text: str, level: int) -> dict:
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich_text(text)}}


def _paragraph_block(text: str) -> dict:
    return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": _rich_text(text)}}


def _bullet_block(text: str) -> dict:
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": _rich_text(text)},
    }


def _list_blocks(items: list[str]) -> list[dict]:
    return [_bullet_block(str(item)) for item in items]


def _dict_or_list_blocks(value) -> list[dict]:
    if isinstance(value, dict):
        return [_bullet_block(f"{key}: {val}") for key, val in value.items()]
    if isinstance(value, list):
        return _list_blocks(value)
    return [_paragraph_block(str(value))]


def _story_blocks(story: dict) -> list[dict]:
    blocks: list[dict] = [
        _heading_block("User Story", 2),
        _paragraph_block(story.get("user_story", "")),
        _heading_block("Acceptance Criteria", 2),
    ]
    blocks.extend(_list_blocks(story.get("acceptance_criteria", [])))

    for dev_task in story.get("dev_tasks", []):
        blocks.append(_heading_block(f"Dev Task: {dev_task.get('title', '')}", 2))

        blocks.append(_heading_block("User Story", 3))
        blocks.append(_paragraph_block(dev_task.get("user_story", "")))

        blocks.append(_heading_block("Acceptance Criteria", 3))
        blocks.extend(_list_blocks(dev_task.get("acceptance_criteria", [])))

        blocks.append(_heading_block("Technical Approach", 3))
        blocks.extend(_list_blocks(dev_task.get("technical_approach", [])))

        blocks.append(_heading_block("Affected Components", 3))
        blocks.extend(_dict_or_list_blocks(dev_task.get("affected_components", {})))

        blocks.append(_heading_block("API Contract", 3))
        blocks.extend(_dict_or_list_blocks(dev_task.get("api_contract", {})))

        blocks.append(_heading_block("Business Rules", 3))
        blocks.extend(_list_blocks(dev_task.get("business_rules", [])))

        blocks.append(_heading_block("Error Handling", 3))
        blocks.extend(_list_blocks(dev_task.get("error_handling", [])))

    for unit_test_task in story.get("unit_test_tasks", []):
        blocks.append(
            _heading_block(f"Unit Test Task: {unit_test_task.get('title', '')}", 2)
        )

        blocks.append(_heading_block("Test Objective", 3))
        blocks.append(_paragraph_block(unit_test_task.get("test_objective", "")))

        blocks.append(_heading_block("Test Scenarios", 3))
        for category, scenario_items in unit_test_task.get("test_scenarios", {}).items():
            blocks.append(_bullet_block(category))
            blocks.extend(_list_blocks(scenario_items))

        blocks.append(_heading_block("Test Data", 3))
        blocks.extend(_dict_or_list_blocks(unit_test_task.get("test_data", {})))

        blocks.append(_heading_block("Mock Setup", 3))
        blocks.extend(_list_blocks(unit_test_task.get("mock_setup", [])))

        blocks.append(_heading_block("Assertions", 3))
        blocks.extend(_list_blocks(unit_test_task.get("assertions", [])))

    return blocks


def _story_properties(story: dict, ppm_number: str, ppm_name: str, system_name: str) -> dict:
    return {
        "Name": {
            "title": [{"text": {"content": story.get("epic_title", "Untitled Epic")[:2000]}}]
        },
        "PPM Number": {"rich_text": _rich_text(ppm_number)},
        "PPM Name": {"rich_text": _rich_text(ppm_name)},
        "System Name": {"rich_text": _rich_text(system_name)},
        "Status": {"select": {"name": "Generated"}},
        "Created": {"date": {"start": datetime.date.today().isoformat()}},
    }


async def create_notion_node(state: StoryForgeState) -> StoryForgeState:
    """Create one Notion page per approved Epic via the Notion API."""
    notion_results: list[dict] = []
    new_errors: list[str] = []

    try:
        client = get_notion_export_client()
    except Exception as exc:
        logger.exception("Failed to initialise Notion client")
        return {
            **state,
            "notion_results": [],
            "errors": state["errors"] + [f"create_notion_node: client init failed: {exc}"],
            "status": "error",
        }

    ppm_number = state["ppm_number"]
    ppm_name = state["ppm_name"]
    system_name = state["system_name"]

    for story in state["approved_stories"]:
        epic_title = story.get("epic_title", "Untitled Epic")
        try:
            properties = _story_properties(story, ppm_number, ppm_name, system_name)
            blocks = _story_blocks(story)
            created = await client.create_epic_page(properties, blocks)
            notion_results.append(
                {"epic_title": epic_title, "page_id": created["id"], "page_url": created["url"]}
            )
        except Exception as exc:  # noqa: BLE001 - one story failing must not abort the rest
            logger.exception("Failed to create Notion page for story %s", epic_title)
            new_errors.append(f"create_notion_node: {epic_title}: {exc}")

    return {
        **state,
        "notion_results": notion_results,
        "errors": state["errors"] + new_errors,
        "status": "done" if not new_errors else "error",
    }
