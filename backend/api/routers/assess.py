"""Assessment endpoints: submit an SDD for analysis, list jobs, and poll job state."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile

from api.job_registry import list_assess_jobs, register_assess_job
from config import settings
from pipeline.runner import get_job_state, start_job
from pipeline.state import StoryForgeState, new_state

router = APIRouter(prefix="/assess", tags=["assess"])


async def _run_assessment(initial_state: StoryForgeState) -> None:
    await start_job(initial_state)


@router.post("")
async def submit_assessment(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    ppm_number: str = Form(...),
    ppm_name: str = Form(...),
    system_name: str = Form(...),
    review_mode: bool = Form(False),
):
    job_id = str(uuid.uuid4())

    uploads_dir = Path(settings.UPLOADS_DIR)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    solution_doc_path = uploads_dir / f"{job_id}.pdf"
    solution_doc_path.write_bytes(await file.read())

    initial_state = new_state(
        job_id=job_id,
        ppm_number=ppm_number,
        ppm_name=ppm_name,
        system_name=system_name,
        solution_doc_path=str(solution_doc_path),
        review_mode=review_mode,
    )

    register_assess_job(job_id, ppm_number, ppm_name, system_name)
    background_tasks.add_task(_run_assessment, initial_state)

    return {"job_id": job_id}


@router.get("/jobs")
async def list_jobs():
    summaries = []
    for job in list_assess_jobs():
        state = await get_job_state(job["job_id"])
        summaries.append(
            {
                **job,
                "status": state["status"] if state else "pending",
                "story_count": len(state["generated_stories"]) if state else 0,
            }
        )
    return summaries


@router.get("/status/{job_id}")
async def get_assessment_status(job_id: str):
    state = await get_job_state(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return state
