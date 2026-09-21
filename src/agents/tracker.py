import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.database.models import ApplicationModel, JobModel
from src.models.application import ApplicationStatus, ApplicationCreate, ApplicationUpdate, ApplicationRecordSchema

logger = logging.getLogger(__name__)

class TrackerAgent:
    """Autonomous Tracker Agent: Manages the job application lifecycle, stage transitions, and follow-ups."""

    def add_to_tracker(self, db: Session, payload: ApplicationCreate) -> ApplicationRecordSchema:
        """Add a job to the user's application tracker."""
        job = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
        if not job:
            raise ValueError(f"Job with ID {payload.job_id} does not exist.")

        existing = db.query(ApplicationModel).filter(ApplicationModel.job_id == payload.job_id).first()
        if existing:
            existing.status = payload.status.value
            if payload.notes:
                existing.notes = payload.notes
            if payload.tailored_cover_letter:
                existing.tailored_cover_letter = payload.tailored_cover_letter
            if payload.interview_date:
                existing.interview_date = payload.interview_date
            db.commit()
            db.refresh(existing)
            return self._to_schema(existing, job)

        record = ApplicationModel(
            job_id=payload.job_id,
            status=payload.status.value,
            notes=payload.notes or "",
            tailored_cover_letter=payload.tailored_cover_letter or "",
            interview_date=payload.interview_date
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return self._to_schema(record, job)

    def update_application(self, db: Session, app_id: int, payload: ApplicationUpdate) -> Optional[ApplicationRecordSchema]:
        """Update status, notes, or interview date for an application."""
        record = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
        if not record:
            return None

        if payload.status:
            record.status = payload.status.value
        if payload.notes is not None:
            record.notes = payload.notes
        if payload.tailored_cover_letter is not None:
            record.tailored_cover_letter = payload.tailored_cover_letter
        if payload.interview_date is not None:
            record.interview_date = payload.interview_date

        record.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(record)

        job = db.query(JobModel).filter(JobModel.id == record.job_id).first()
        return self._to_schema(record, job)

    def delete_application(self, db: Session, app_id: int) -> bool:
        """Remove an application from tracking."""
        record = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
        if not record:
            return False
        db.delete(record)
        db.commit()
        return True

    def list_applications(self, db: Session, status: Optional[ApplicationStatus] = None) -> List[ApplicationRecordSchema]:
        """Retrieve all tracked applications, optionally filtered by status."""
        query = db.query(ApplicationModel)
        if status:
            query = query.filter(ApplicationModel.status == status.value)
        
        records = query.order_by(ApplicationModel.updated_at.desc()).all()
        results = []
        for r in records:
            job = db.query(JobModel).filter(JobModel.id == r.job_id).first()
            if job:
                results.append(self._to_schema(r, job))
        return results

    def get_funnel_metrics(self, db: Session) -> Dict[str, Any]:
        """Calculate application conversion funnel statistics."""
        apps = db.query(ApplicationModel).all()
        total = len(apps)

        counts = {
            "SHORTLISTED": 0,
            "APPLIED": 0,
            "INTERVIEWING": 0,
            "OFFER": 0,
            "REJECTED": 0
        }
        for a in apps:
            if a.status in counts:
                counts[a.status] += 1

        applied_count = counts["APPLIED"] + counts["INTERVIEWING"] + counts["OFFER"] + counts["REJECTED"]
        interview_rate = round((counts["INTERVIEWING"] + counts["OFFER"]) / max(applied_count, 1) * 100, 1)
        offer_rate = round(counts["OFFER"] / max(applied_count, 1) * 100, 1)

        return {
            "total_tracked": total,
            "counts": counts,
            "applied_total": applied_count,
            "interview_rate_pct": interview_rate,
            "offer_rate_pct": offer_rate
        }

    def _to_schema(self, record: ApplicationModel, job: JobModel) -> ApplicationRecordSchema:
        return ApplicationRecordSchema(
            id=record.id,
            job_id=record.job_id,
            job_title=job.title if job else "Unknown Position",
            company=job.company if job else "Unknown Company",
            location=job.location if job else "Remote",
            url=job.url if job else "#",
            source=job.source if job else "Aggregator",
            status=ApplicationStatus(record.status),
            notes=record.notes or "",
            tailored_cover_letter=record.tailored_cover_letter or "",
            interview_date=record.interview_date,
            match_score=record.match_score,
            created_at=record.created_at.isoformat() if record.created_at else "",
            updated_at=record.updated_at.isoformat() if record.updated_at else ""
        )
