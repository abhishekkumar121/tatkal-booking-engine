from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models import Order
from app.redis_client import redis_client
import time 

ORDER_TIMEOUT_MINUTES = 1             
MAX_CONCURRENT_PER_SALE = 5
ALLOWED_WINDOW_SECONDS = 90 


def cancel_unpaid_orders():
    db = SessionLocal()
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=ORDER_TIMEOUT_MINUTES)

        expired_orders = db.query(Order).filter(
            Order.status == "pending",
            Order.created_at < cutoff_time
        ).all()

        for order in expired_orders:
            order.status = "cancelled"
            # Stock wapas Redis mein add karo
            redis_client.incrby(f"stock:{order.flash_sale.product_id}", order.quantity)
            print(f"Cancelled order {order.id}, released {order.quantity} units back to stock")

        db.commit()
    finally:
        db.close()


def promote_queues():                                   # <-- CHANGE 4 (poora function replace)
    active_ids = redis_client.smembers("active_queues")
    now = time.time()
    for sale_id in active_ids:
        allowed_key = f"allowed:{sale_id}"
        queue_key = f"queue:{sale_id}"

        redis_client.zremrangebyscore(allowed_key, 0, now - ALLOWED_WINDOW_SECONDS)

        room = MAX_CONCURRENT_PER_SALE - redis_client.zcard(allowed_key)
        for _ in range(max(room, 0)):
            popped = redis_client.zpopmin(queue_key, 1)
            if not popped:
                break
            user_id, _score = popped[0]
            redis_client.zadd(allowed_key, {user_id: now})


scheduler = BackgroundScheduler()
scheduler.add_job(cancel_unpaid_orders, "interval", seconds=15)   
scheduler.add_job(promote_queues, "interval", seconds=1)