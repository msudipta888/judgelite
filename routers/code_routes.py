from fastapi import APIRouter, HTTPException
from app_queue.job.producer import add_submission, get_submission, update_submission, delete_submission, QueueStats

router = APIRouter(
    prefix="/route",
    tags=["Code Execution"]
)

# 1. Post submission -> Push job into BullMQ Queue
@router.post("/submission")
async def code_submission(submission: dict):
    try:
        # Ensure submission has an ID (generate one if missing)
        import uuid
        if "id" not in submission:
            submission["id"] = str(uuid.uuid4())
            
        result = await add_submission(submission)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Get status / result of submission from Redis
@router.get("/submission/{submission_id}")
async def check_submission_status(submission_id: str):
    try:
        result = await get_submission(submission_id)
        if not result:
            raise HTTPException(status_code=404, detail="Submission not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Update submission status in Redis cache
@router.put("/submission/{submission_id}")
async def update_submission_status(submission_id: str, update: dict):
    try:
        result = await update_submission(submission_id, update)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 4. Delete submission from Redis cache
@router.delete("/submission/{submission_id}")
async def delete_submission_by_id(submission_id: str):
    try:
        success = await delete_submission(submission_id)
        if not success:
            raise HTTPException(status_code=404, detail="Submission not found")
        return {"message": f"Submission {submission_id} deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Get queue statistics (for monitoring dashboard)
@router.get("/queue-stats")
async def get_queue_stats():
    try:
        stats = await QueueStats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
