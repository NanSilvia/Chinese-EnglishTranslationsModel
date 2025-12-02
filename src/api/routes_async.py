"""
Async API routes for long-running translation, question generation, and linguistic analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List

from .models import (
    AsyncTranslationJob,
    AsyncQuestionsJob,
    AsyncLinguisticJob,
    AsyncJobResponse,
    AsyncJobStatusResponse,
    JobStatus,
)
from .async_jobs import AsyncJobManager
from .service import TranslationService
from .schemas import PromptingSchemaRegistry

router = APIRouter()


def get_job_manager():
    """Get or create async job manager instance."""
    if not hasattr(get_job_manager, "_instance"):
        translation_service = TranslationService()
        get_job_manager._instance = AsyncJobManager(translation_service)
    return get_job_manager._instance


@router.post("/translate/async", response_model=AsyncJobResponse)
async def translate_async(request: AsyncTranslationJob):
    """
    Submit a translation job asynchronously.

    Returns a job_id that can be used to poll the status with GET /translate/status/{job_id}

    Example:
    ```json
    {
        "text": "这是一个很长的测试句子，需要翻译...",
        "schema_name": "translate"
    }
    ```

    Poll with: GET /translate/status/{job_id}
    """
    job_manager = get_job_manager()

    try:
        # Validate schema exists
        schema = PromptingSchemaRegistry.get_or_default(request.schema_name)

        # Submit job to async queue
        job_id = await job_manager.submit_job(
            text=request.text,
            job_type="translation",
            schema_name=request.schema_name,
        )

        return AsyncJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Job {job_id} submitted. Poll /translate/status/{job_id} for results.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@router.get("/translate/status/{job_id}", response_model=AsyncJobStatusResponse)
async def get_translation_status(job_id: str):
    """
    Poll the status of an async translation job.

    Returns:
    - PENDING: Job is waiting to be processed
    - PROCESSING: Translation is currently running
    - COMPLETED: Translation finished successfully (result included)
    - FAILED: Translation failed (error message included)
    """
    job_manager = get_job_manager()
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    response = AsyncJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat() if job.created_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )

    if job.status == JobStatus.COMPLETED:
        response.result = job.result
    elif job.status == JobStatus.FAILED:
        response.error = job.error

    return response


@router.post("/batch/translate/async")
async def batch_translate_async(
    requests: List[AsyncTranslationJob], schema_name: str = Query(default="translate")
):
    """
    Submit multiple translation jobs asynchronously.

    Returns a list of job IDs that can be polled individually.

    Example:
    ```json
    [
        {"text": "第一个句子"},
        {"text": "第二个句子"},
        {"text": "第三个句子"}
    ]
    ```
    """
    job_manager = get_job_manager()

    try:
        job_ids = []
        for req in requests:
            job_id = await job_manager.submit_job(
                text=req.text,
                job_type="translation",
                schema_name=req.schema_name or schema_name,
            )
            job_ids.append(job_id)

        return {
            "total_submitted": len(job_ids),
            "job_ids": job_ids,
            "message": "All jobs submitted. Poll /translate/status/{job_id} for each job.",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to submit batch jobs: {str(e)}"
        )


@router.post("/questions/async")
async def generate_questions_async(request: AsyncQuestionsJob):
    """
    Submit a question generation job asynchronously.

    Returns a job_id that can be used to poll the status with GET /questions/status/{job_id}

    Example:
    ```json
    {
        "text": "北京是中国的首都...",
        "question_count": 5
    }
    ```

    Poll with: GET /questions/status/{job_id}
    """
    job_manager = get_job_manager()

    try:
        # Submit job to async queue
        job_id = await job_manager.submit_job(
            text=request.text,
            job_type="questions",
            question_count=request.question_count,
        )

        return {
            "job_id": job_id,
            "status": "pending",
            "message": f"Job {job_id} submitted. Poll /questions/status/{job_id} for results.",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@router.get("/questions/status/{job_id}")
async def get_questions_status(job_id: str):
    """
    Poll the status of an async question generation job.

    Returns:
    - PENDING: Job is waiting to be processed
    - PROCESSING: Question generation is currently running
    - COMPLETED: Question generation finished successfully (result included)
    - FAILED: Question generation failed (error message included)
    """
    job_manager = get_job_manager()
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    response = AsyncJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat() if job.created_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )

    if job.status == JobStatus.COMPLETED:
        response.result = job.result
    elif job.status == JobStatus.FAILED:
        response.error = job.error

    return response


@router.post("/linguistic/async", response_model=AsyncJobResponse)
async def analyze_linguistic_async(request: AsyncLinguisticJob):
    """
    Submit a linguistic analysis job asynchronously.

    Analyzes the selected_text within the context of full_text, providing:
    - Sentence structure breakdown
    - Grammatical rule explanations
    - Grammar patterns with examples
    - English translation
    - Expansion notes if needed

    Returns a job_id that can be used to poll the status with GET /linguistic/status/{job_id}

    Example:
    ```json
    {
        "full_text": "北京是中国的首都，也是世界著名的历史文化名城。",
        "selected_text": "是中国的首都"
    }
    ```

    Poll with: GET /linguistic/status/{job_id}
    """
    job_manager = get_job_manager()

    try:
        # Submit job to async queue
        job_id = await job_manager.submit_job(
            job_type="linguistic",
            full_text=request.full_text,
            selected_text=request.selected_text,
        )

        return AsyncJobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            message=f"Job {job_id} submitted. Poll /linguistic/status/{job_id} for results.",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to submit job: {str(e)}")


@router.get("/linguistic/status/{job_id}", response_model=AsyncJobStatusResponse)
async def get_linguistic_status(job_id: str):
    """
    Poll the status of an async linguistic analysis job.

    Returns:
    - PENDING: Job is waiting to be processed
    - PROCESSING: Linguistic analysis is currently running
    - COMPLETED: Analysis finished successfully (result included)
    - FAILED: Analysis failed (error message included)
    """
    job_manager = get_job_manager()
    job = await job_manager.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    response = AsyncJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        progress=job.progress,
        created_at=job.created_at.isoformat() if job.created_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
    )

    if job.status == JobStatus.COMPLETED:
        response.result = job.result
    elif job.status == JobStatus.FAILED:
        response.error = job.error

    return response
