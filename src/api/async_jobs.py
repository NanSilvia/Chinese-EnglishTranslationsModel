"""
Async job management system for handling long-running translations.
Uses in-memory storage with background task processing.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, Any
from enum import Enum
from dataclasses import dataclass, asdict, field

from .models import JobStatus, TranslationResponse
from .service import TranslationService


@dataclass
class JobRecord:
    """Internal record of a translation, questions, or linguistic analysis job."""

    job_id: str
    status: JobStatus
    job_type: str  # "translation", "questions", or "linguistic"
    text: str
    schema_name: Optional[str] = None  # Used for translations
    question_count: Optional[int] = None  # Used for questions
    full_text: Optional[str] = None  # Used for linguistic analysis
    selected_text: Optional[str] = None  # Used for linguistic analysis
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: str = "Queued for processing"


class AsyncJobManager:
    """Manages async translation jobs with polling support."""

    def __init__(self, translation_service: TranslationService):
        self.translation_service = translation_service
        self.jobs: Dict[str, JobRecord] = {}
        self.processing_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None

    async def submit_job(
        self,
        text: str = None,
        job_type: str = "translation",
        schema_name: Optional[str] = None,
        question_count: Optional[int] = None,
        full_text: Optional[str] = None,
        selected_text: Optional[str] = None,
    ) -> str:
        """
        Submit a new job (translation, questions, or linguistic analysis).

        Args:
            text: Text to process (for translations and questions)
            job_type: "translation", "questions", or "linguistic"
            schema_name: Schema to use (for translations)
            question_count: Number of questions to generate (for questions)
            full_text: Complete text for context (for linguistic)
            selected_text: Text to analyze (for linguistic)

        Returns:
            Job ID for polling
        """
        job_id = str(uuid.uuid4())
        job = JobRecord(
            job_id=job_id,
            status=JobStatus.PENDING,
            job_type=job_type,
            text=text or "",
            schema_name=schema_name or "translate",
            question_count=question_count or 5,
            full_text=full_text,
            selected_text=selected_text,
        )
        self.jobs[job_id] = job
        await self.processing_queue.put(job_id)
        return job_id

    async def get_job_status(self, job_id: str) -> Optional[JobRecord]:
        """Get the status and result of a job."""
        return self.jobs.get(job_id)

    async def start_worker(self):
        """Start the background worker that processes queued jobs."""
        if self._worker_task is not None:
            return  # Worker already running

        self._worker_task = asyncio.create_task(self._process_jobs())

    async def _process_jobs(self):
        """Background worker that processes queued translation jobs."""
        while True:
            try:
                job_id = await asyncio.wait_for(
                    self.processing_queue.get(), timeout=60.0
                )
                await self._execute_job(job_id)
            except asyncio.TimeoutError:
                # Keep worker alive even if no jobs
                continue
            except Exception as e:
                print(f"Error in job processing: {e}")

    async def _execute_job(self, job_id: str):
        """Execute a single job (translation, questions, or linguistic analysis)."""
        job = self.jobs.get(job_id)
        if not job:
            return

        try:
            # Mark as processing
            job.status = JobStatus.PROCESSING
            job.started_at = datetime.now()
            job.progress = "Processing in progress..."

            # Run job in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()

            if job.job_type == "translation":
                translation_result = await loop.run_in_executor(
                    None,
                    self.translation_service.translate,
                    job.text,
                    job.schema_name,
                )

                # Check if translation was successful
                translation_data = translation_result.get("translation", {})
                if not translation_data.get("success", False):
                    raise Exception(translation_data.get("error", "Translation failed"))

                # Create response
                from .models import TranslationResponse

                job.result = TranslationResponse(
                    input_text=job.text,
                    translations={
                        translation_result.get("model", "unknown"): translation_data
                    },
                )

            elif job.job_type == "questions":
                questions_result = await loop.run_in_executor(
                    None,
                    self.translation_service.generate_questions,
                    job.text,
                    job.question_count,
                )

                # Check if questions generation was successful
                if not questions_result.get("success", False):
                    raise Exception(
                        questions_result.get("error", "Question generation failed")
                    )

                # Create response
                from .models import QuestionResponse

                job.result = QuestionResponse(
                    input_text=job.text,
                    question_count=job.question_count,
                    questions=questions_result.get("questions_list"),
                )

            elif job.job_type == "linguistic":
                linguistic_result = await loop.run_in_executor(
                    None,
                    self.translation_service.analyze_linguistic,
                    job.full_text,
                    job.selected_text,
                )

                # Check if linguistic analysis was successful
                if linguistic_result.get("error"):
                    raise Exception(
                        linguistic_result.get("error", "Linguistic analysis failed")
                    )

                if not linguistic_result.get("success", False):
                    raise Exception("Linguistic analysis returned no success status")

                # Filter success from result and store
                analysis_data = {
                    k: v for k, v in linguistic_result.items() if k != "success"
                }

                job.result = analysis_data

            else:
                raise Exception(f"Unknown job type: {job.job_type}")

            job.status = JobStatus.COMPLETED
            job.progress = "Processing completed"
            job.completed_at = datetime.now()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.progress = f"Processing failed: {str(e)}"
            job.completed_at = datetime.now()

    def cleanup_old_jobs(self, max_age_seconds: int = 3600):
        """Remove completed jobs older than max_age_seconds."""
        now = datetime.now()
        jobs_to_remove = []

        for job_id, job in self.jobs.items():
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                age = (now - job.completed_at).total_seconds()
                if age > max_age_seconds:
                    jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.jobs[job_id]
