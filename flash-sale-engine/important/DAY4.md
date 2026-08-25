# Day 5 — IRCTC Tatkal Problems: Solved (TatkalEngine)

Yeh document batata hai humne research-confirmed IRCTC Tatkal problems ko kaise solve kiya, existing (Day 0-4) backend ke upar. Naya project nahi banaya — same battle-tested backend (auth, Redis atomic stock, idempotency, auto-cancel, k6-tested) ke upar naye features add kiye.

---

## Research — Real Problems Kya The

Google/news se confirm kiye gaye current IRCTC Tatkal complaints:
1. **Payment kata, ticket nahi bana** — sabse common complaint, IRCTC ne khud isko fix karne ke liye "Resume/Retry Booking" feature banaya (permanent fix nahi mana jata)
2. **Screen freeze karke seedha "Waitlist"/"Regret"** — backend itna slow hai ki jab tak request process ho, stock khatam
3. **Agents/bots ko unfair advantage** — genuine users struggle karte hain
4. **Poora site/payment gateway down** peak load pe (e-ticketing paused ~3 hours documented incident)
5. **Refund transparency ki kami** — status pata nahi chalta

---

## Problem 1: Overselling (Recap — Day 2 Se)

Redis Lua atomic decrement se already solved — 5 stock, 15 orders bug se, fix ke baad exactly 5 orders. (Poora detail `DAY2_CONCURRENCY_EXPLAINED.md` mein hai.)

---

## Problem 2: "Payment Kata, Ticket Nahi Mila" — Reserve→Pay Flow

### Fix Se Pehle
Order banate hi seedha `status="confirmed"` ho jata tha — koi payment step hi nahi tha bich mein.

### Fix
Order ab **do steps** mein confirm hota hai:

**Step A — Reserve (`POST /orders/`):** Seat Redis se turant reserve hoti hai (atomic decrement), DB mein order `"pending"` status ke saath banta hai.

**Step B — Pay (`POST /orders/{id}/pay`):**
```python
class PaymentRequest(BaseModel):
    simulate_failure: bool = False


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay_for_order(order_id: int, payment: PaymentRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order already {order.status}, cannot pay again")

    if payment.simulate_failure:
        order.status = "payment_failed"
        order.refund_status = "initiated"
        redis_client.incrby(f"stock:{order.flash_sale.product_id}", order.quantity)
        db.commit()
        db.refresh(order)
        raise HTTPException(status_code=402, detail="Payment failed — seat released, refund initiated")

    order.status = "confirmed"
    db.commit()
    db.refresh(order)
    return order
```

**Kyun yeh asli IRCTC bug fix karta hai:** Agar payment fail ho, seat **turant** (usi request ke andar) Redis mein wapas release hoti hai — koi aur user ko wait nahi karna padta uske "stuck" hone ka. Real IRCTC mein yeh instant nahi hota, refund/release ke liye time lagta hai.

---

## Problem 3: Per-User Limit + Rate Limiting (Agents/Bots)

### Per-User Limit
`create_order` mein, `flash_sale` fetch hone ke baad:
```python
user_order_count = db.query(Order).filter(
    Order.user_id == current_user.id,
    Order.flash_sale_id == order.flash_sale_id,
    Order.status.in_(["pending", "confirmed"])
).count()

if user_order_count >= flash_sale.max_per_user:
    raise HTTPException(status_code=429, detail=f"Booking limit reached — max {flash_sale.max_per_user} ticket(s) per user for this window")
```
Sirf `pending`/`confirmed` count hote hain — cancelled/failed orders punish nahi karte (genuine retry allowed rehta hai).

### Rate Limiting
`create_order` ke **sabse shuru** mein (DB touch karne se pehle hi reject karna hai):
```python
rate_limit_key = f"ratelimit:order:{current_user.id}"
request_count = redis_client.incr(rate_limit_key)
if request_count == 1:
    redis_client.expire(rate_limit_key, 2)

if request_count > 3:
    raise HTTPException(status_code=429, detail="Too many requests — please slow down")
```
`INCR` + `EXPIRE` combo se ek "sliding 2-second window" banta hai — 2 second mein 3 se zyada requests to `429`.

**Real IRCTC problem se link:** Agents/bots scripts se bahut fast requests bhejte hain — yeh dono mechanisms unko slow karte hain bina genuine users ko affect kiye.

---

## Problem 4: Virtual Waiting Room (Sabse Complex Feature)

### Concept
Jab flash sale live ho, users **seedha** booking nahi kar sakte — pehle queue join karte hain. Background job **har second** top N (5) users ko "allowed" karta hai.

### `app/routers/queue.py`
```python
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

    if redis_client.sismember(allowed_key, user_id):
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

    if redis_client.sismember(allowed_key, user_id):
        return {"status": "allowed", "message": "You may proceed to book now."}

    rank = redis_client.zrank(queue_key, user_id)
    if rank is None:
        return {"status": "not_in_queue"}
    return {"status": "queued", "position": rank + 1}
```

**Redis data structures ka use:**
- `queue:{id}` — **Sorted Set** (`ZADD`), score = join timestamp → automatically FIFO order
- `allowed:{id}` — **Set**, jo abhi book kar sakte hain
- `active_queues` — **Set**, kaunsi flash sales ki queue "on" hai

### `app/scheduler.py` Mein Naya Background Job
```python
MAX_CONCURRENT_PER_SALE = 5

def promote_queues():
    active_ids = redis_client.smembers("active_queues")
    for sale_id in active_ids:
        allowed_key = f"allowed:{sale_id}"
        queue_key = f"queue:{sale_id}"
        room = MAX_CONCURRENT_PER_SALE - redis_client.scard(allowed_key)
        for _ in range(max(room, 0)):
            popped = redis_client.zpopmin(queue_key, 1)
            if not popped:
                break
            user_id, _score = popped[0]
            redis_client.sadd(allowed_key, user_id)

scheduler.add_job(promote_queues, "interval", seconds=1)
```
Har 1 second chalta hai, khali jagah (`MAX_CONCURRENT_PER_SALE - abhi allowed count`) jitne users queue se `ZPOPMIN` (sabse purana/pehla) uthake `allowed` mein daal deta hai.

### `create_order` Mein Gate
```python
queue_active = redis_client.sismember("active_queues", str(order.flash_sale_id))
if queue_active:
    allowed_key = f"allowed:{order.flash_sale_id}"
    if not redis_client.sismember(allowed_key, str(current_user.id)):
        raise HTTPException(status_code=403, detail="Please join the queue and wait for your turn before booking")
    redis_client.srem(allowed_key, str(current_user.id))
```
**Kyun purane flows nahi toote:** Yeh check sirf tab active hota hai jab flash sale `active_queues` mein ho (kisi ne `/queue/join` call kiya ho) — warna normal booking chalti rehti hai.

**Real IRCTC problem se link:** "Screen freeze karke seedha waitlist" milne ki jagah, user ko **clear queue position** milta hai — backend bhi ek controlled rate pe requests process karta hai, crash nahi hota.

---

## Problem 5: Peak Load Crash (Recap — Day 4 Se)

k6 se 50 concurrent users, 481 requests/5sec — 100% checks passed, koi 500 error nahi, exact stock jitna hi orders confirm hue. (Poora detail `DAY4_IDEMPOTENCY_AUTOCANCEL_LOADTEST.md` mein hai.)

---

## Problem 6: Refund Transparency

### `models.py` Mein Naya Column
```python
refund_status = Column(String(20), nullable=True)
```
`nullable=True` — jin orders mein refund kabhi hua hi nahi, unke liye khali rehta hai.

### Migration
```bash
alembic revision --autogenerate -m "add refund_status to orders"
alembic upgrade head
```

### Payment Failure Pe Turant Set Hota Hai
(Dekh upar Problem 2 ka code — `order.refund_status = "initiated"` line)

### Naya Endpoint
```python
@router.get("/{order_id}/refund-status")
def get_refund_status(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.refund_status:
        raise HTTPException(status_code=400, detail="No refund associated with this order")
    return {"order_id": order.id, "refund_status": order.refund_status}
```

**Real IRCTC problem se link:** Asli IRCTC mein refund status turant pata nahi chalta, bank pe depend karta hai. Yahan user ko **turant confirmation** milta hai ki process shuru ho gaya — better transparency.

---

## Interview Mein Kaise Present Karna Hai

> "Maine ek concurrency-safe Tatkal-style booking engine banaya jo IRCTC ke research-confirmed real problems solve karta hai — overselling Redis atomic locking se, 'payment debited but seat not booked' ek reserve-then-confirm two-phase flow se (jisme payment fail hone par seat turant release hoti hai), bot/agent abuse per-user limits aur Redis rate limiting se, aur 'screen freeze into waitlist' ek virtual waiting room se jo Redis Sorted Sets use karke fair FIFO queueing karta hai aur backend ko ek controlled rate pe hi load deता hai."

---

## Abhi Tak Ka Overall Status

Saare 6 research-confirmed IRCTC Tatkal problems solved hain:
1. Overselling ✅
2. Payment-failed seat-stuck ✅
3. Per-user limit + rate limiting ✅
4. Virtual waiting room ✅
5. Peak load resilience (k6-proven) ✅
6. Refund transparency ✅

## Next Steps (Infra Polish)
- Full app Dockerize
- WebSocket live stock push
- CI/CD (GitHub Actions)
- Distributed tracing (OpenTelemetry + Jaeger)
- k6 load test — full flow (queue→reserve→pay)
- README + architecture diagram