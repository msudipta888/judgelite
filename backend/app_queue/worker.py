import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import redis
from bullmq import Worker
import json
import os
from code_file.code_execution import CodeExecution

redis_client: redis.Redis = None
worker: Worker = None
executor = CodeExecution()

async def process_job(job, token):
    global redis_client
    submission = job.data
    job_id = submission["id"]
    print("submision came")
    try:
        # Update cache status to Processing
        payload = {
            "status": "Processing",
            "submission": submission
        }
        if redis_client:
            redis_client.setex(
                f"submission:{job_id}",
                3600,
                json.dumps(payload)
            )
        
        # Execute code synchronously inside Docker sandbox
        result = executor.execute_code(submission)
        
        final_payload = {
            "status": "Completed" if result.get("status") == "Success" else result.get("status", "Failed"),
            "submission_id": job_id,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "execution_time": result.get("execution_time", 0),
            "memory_usage": result.get("memory_usage", "0 MB"),
            "exit_code": result.get("exit_code")
        }
        if redis_client:
            redis_client.setex(
                f"submission:{job_id}",
                3600,
                json.dumps(final_payload)
            )
    except Exception as e:
        error_payload = {
            "status": "Failed",
            "submission_id": job_id,
            "stdout": "",
            "stderr": str(e),
            "execution_time": 0,
            "memory_usage": "0 MB",
            "exit_code": None
        }
        if redis_client:
            redis_client.setex(
                f"submission:{job_id}",
                3600,
                json.dumps(error_payload)
            )

async def start_worker():
    global redis_client, worker
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_client = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
    try:
        redis_client.ping()
        print("Worker connected to Redis...")
    except Exception as e:
        print(f"Worker Redis connection failed: {e}")

    connection_opts = {
        "connection": {
            "host": redis_host,
            "port": 6379,
        },
        "concurrency": 3 
    }    
    worker = Worker("submission", process_job, opts=connection_opts)
    print("BullMQ Worker started and listening on queue 'submission'...")
    return worker

async def stop_worker():
    global redis_client, worker
    if worker:
        await worker.close()
    if redis_client:
        redis_client.close()

async def main():
    w = await start_worker()
    # Keep the async worker running indefinitely
    try:
        # help for worker run in background 24*7
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        await stop_worker()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
