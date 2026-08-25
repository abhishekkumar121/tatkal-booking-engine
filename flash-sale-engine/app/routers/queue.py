from fastapi import APIRouter, Depends
from app.auth_utils import get_current_user
from app.models import User
from app.redis_client import redis_client
import time

router = APIRouter(prefix="/queue", tags=["queue"])


@router.post("/{flash_sale_id}/join")
def join_queue(flash_sale_id: int, current_user: User = Depends(get_current_user)):
    allowed_key = f"allowed:{flash_sale_id}"
    queue_key = f"queue:{flash_sale_id}"
    user_id = str(current_user.id)

    if redis_client.zscore(allowed_key, user_id) is not None:      # <-- badla: sismember → zscore
        return {"status": "allowed", "message": "You may proceed to book now."}

    redis_client.sadd("active_queues", str(flash_sale_id))
    redis_client.zadd(queue_key, {user_id: time.time()}, nx=True)

    rank = redis_client.zrank(queue_key, user_id)
    return {"status": "queued", "position": (rank + 1) if rank is not None else None}


@router.get("/{flash_sale_id}/position")
def check_position(flash_sale_id: int, current_user: User = Depends(get_current_user)):
    allowed_key = f"allowed:{flash_sale_id}"
    queue_key = f"queue:{flash_sale_id}"
    user_id = str(current_user.id)

    if redis_client.zscore(allowed_key, user_id) is not None:      # <-- badla: sismember → zscore
        return {"status": "allowed", "message": "You may proceed to book now."}

    rank = redis_client.zrank(queue_key, user_id)
    if rank is None:
        return {"status": "not_in_queue"}
    return {"status": "queued", "position": rank + 1}