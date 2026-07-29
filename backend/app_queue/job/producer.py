from bullmq import Queue
import redis
import json
import os

redis_client: redis.Redis = None
submissionQueue: Queue = None

async def initialze_queue():
    global redis_client, submissionQueue
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
   
    try:
        redis_client.ping()
        print("Connected to Redis...")
    except redis.exceptions.ConnectionError as e:
        print(f"Connection failed: {e}")
        return

    DEFAULT_JOB_OPTIONS = {
        "attempts": 3,
        "backoff": {
            "type": "exponential",
            "delay": 1000,
        },
        "removeOnComplete": {
            "count": 100,
        },
        "removeOnFail": {
            "count": 1000,
        }
    }
    submissionQueue = Queue("submission", {
        "connection": {
            "host": redis_host,
            "port": 6379,
        },
        "defaultJobOptions": DEFAULT_JOB_OPTIONS,
    })
    return submissionQueue

def getRedis():  return redis_client    
def getQueue():   return submissionQueue   

async def add_submission(submission:dict):
    """Add code submission in queue"""
    if not redis_client or not submissionQueue:
        raise Exception("Redis client or Submission queue is not initialized")
    print(submission)
    payload={
    "status":"Pending",
     "submission": submission
   }
    submission_id=str(submission["id"])
    # store initail submission state in redis
    redis_client.setex(
        f"submission:{submission_id}",
        3600,
       json.dumps(payload)
    )
    # add job to queue
    await submissionQueue.add(
        "execute_job",
        submission,
        opts={"jobId":str(submission["id"])}
    )
    return {"submission_id": submission_id, "status": "Pending"}
async def get_submission(id: str):
    """Get submission status from Redis"""
    if not redis_client:
        raise Exception("Redis client is not initialized")
    
    result = redis_client.get(f"submission:{id}")
    if not result:
        return None
    return json.loads(result)


# update data in cache   
async def update_submission(id: str, update: dict):
    if not redis_client:
        raise Exception("Redis client not initialized")
   
    existing_data = await get_submission(id)
    if not existing_data:
        raise Exception("Submission not found")
    # Merge new update with existing data
    update_data = { **existing_data, **update }
    if "status" in update:
        update_data["status"] = update["status"]
    elif "status" not in update_data:
        update_data["status"] = "Updated"

    redis_client.setex(
        f"submission:{id}",
        3600,
        json.dumps(update_data)
    )
    return update_data

# delete submission from cache
async def delete_submission(id: str):
    if not redis_client:
        raise Exception("Redis client not initialized")
   
    existing_data = redis_client.get(f"submission:{id}")
    if not existing_data:
        return False
    redis_client.delete(f"submission:{id}")
    return True

# for admin get Queue Statistics to check System Health Dashboard
async def QueueStats():
    if not submissionQueue:
        raise Exception("Submission queue is not initialized")
    counts = await submissionQueue.getJobCounts("waiting", "active", "completed", "failed")
    waiting = counts.get("waiting", 0)
    active = counts.get("active", 0)
    completed = counts.get("completed", 0)
    failed = counts.get("failed", 0)
    return {
        "submissions": {
            "total": waiting + active + completed + failed,
            "in_queue": waiting,
            "processing": active,
            "completed": completed,
            "failed": failed
        }
    }

# close queue and redis
async def close_queue():
    """Close queue and redis"""
    if submissionQueue: 
        await submissionQueue.close()
    if redis_client:
        redis_client.close()