# Day 4 — Idempotency + Auto-Cancel Orders + k6 Load Testing

Yeh document Day 2 (race condition fix) ke baad ke 3 improvements explain karta hai: duplicate request handling, unpaid orders ka auto-cleanup, aur professional load testing tool (k6) se proof.

---

## 1. Idempotency — Duplicate Requests Ko Safely Handle Karna

### Problem Kya Thi

Pehle agar koi user "Buy" button 2 baar dabaye (double-click, ya slow network jisse retry ho), backend dono requests ko **alag-alag naya order** samajh leta — ya worse, DB ka `unique=True` constraint dusri request pe **ugly 500 error** de deta (kyunki dono same `idempotency_key` bhejte agar frontend sahi se implement kiya ho).

### Fix

`app/routers/orders.py` mein `create_order` function ke **sabse shuru** mein yeh check add kiya:

```python
existing_order = db.query(Order).filter(Order.idempotency_key == order.idempotency_key).first()
if existing_order:
    return existing_order  # purana wahi order wapas de do, naya mat banao
```

**Logic:** Naya order banane se **pehle**, check karo "kya is `idempotency_key` se koi order pehle bana hai?" Agar haan — **wahi purana order return** kar do, na Redis touch karo na naya DB row banao. Agar nahi — normal flow chalta hai.

### Real App Mein Key Kaise Aati Hai

Yeh key **frontend generate karta hai** (usually `crypto.randomUUID()` se) jab user button dabata hai. Agar wahi request retry ho, **wahi same key dobara** bhejta hai frontend — naya UUID nahi banata. Isi wajah se backend pehchan leta hai "yeh dobara aayi wahi request hai."

**Do layers of protection:**
1. Python-level check (upar wala code) — fast, clean response deta hai
2. DB ka `unique=True` constraint — safety net agar kabhi race condition se dono checks ek saath pass ho jayein (bahut rare)

### Test Kaise Kiya

Same `idempotency_key` ke saath 2 baar `/orders/` POST kiya — dono baar **same order `id`** wapas mila, stock sirf **ek baar** kam hua (Redis mein verify kiya).

---

## 2. Auto-Cancel Unpaid Orders — Background Cron Job

### Problem Kya Thi

Pehle order banते hi seedha `status="confirmed"` ho jata tha — koi payment wait hi nahi tha. Real flash-sale flow hota hai:
1. Order **"pending"** banta hai, stock reserve hota hai
2. User payment kare 15 min ke andar → **"confirmed"**
3. Payment na kare → order **auto-cancel** ho, stock **wapas release** ho jaye

Agar step 3 na ho, koi bhi order bana ke payment kabhi na kare to woh stock **hamesha ke liye locked** reh jata — koi aur khareed hi nahi pata.

### Fix — Do Changes

**1. `create_order` mein status badla:**
```python
status="pending",  # pehle "confirmed" tha
```

**2. Naya file `app/scheduler.py` — background job:**

```python
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
from app.database import SessionLocal
from app.models import Order
from app.redis_client import redis_client

ORDER_TIMEOUT_MINUTES = 15


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
            redis_client.incrby(f"stock:{order.flash_sale.product_id}", order.quantity)

        db.commit()
    finally:
        db.close()


scheduler = BackgroundScheduler()
scheduler.add_job(cancel_unpaid_orders, "interval", minutes=1)
```

**Kya ho raha hai:**
- `cancel_unpaid_orders()` — DB mein woh saare orders dhoondhta hai jo `"pending"` hain **aur** `15 min se zyada purane` hain
- Har aise order ko `"cancelled"` mark karta hai, **Redis mein stock wapas add karta hai** (`INCRBY`) taaki woh units dobara available ho jayein
- `BackgroundScheduler` — ek "background clock," jo `interval` ke hisaab se (har 1 minute) yeh function khud chalata rehta hai, bina manual trigger ke

**`order.flash_sale.product_id` kaam karne ke liye ek relationship add ki `models.py` mein:**
```python
class Order(Base):
    ...
    flash_sale = relationship("FlashSale")
```
`ForeignKey` sirf ek number store karta hai; `relationship(...)` SQLAlchemy ko batata hai "jab `order.flash_sale` likhu, poora FlashSale object apne aap fetch kar do" — manual query likhne se bachata hai.

**`app/main.py` mein scheduler start kiya:**
```python
from app.scheduler import scheduler

@app.on_event("startup")
def start_scheduler():
    scheduler.start()
```
Jab FastAPI app start hoti hai, scheduler bhi saath mein "on" ho jata hai, server jab tak chalta hai tab tak background mein chalta rehta hai.

### Test Kaise Kiya

Testing ke liye temporarily values kam ki (`ORDER_TIMEOUT_MINUTES = 0`, interval `seconds=10`), ek order banaya (pending), ~15-20 second wait kiya, DB mein check kiya — **status khud-ba-khud "cancelled" ho gaya**, Redis mein stock bhi wapas add ho gaya. Test ke baad production values (`15` minutes, `1` minute interval) wapas laga di.

---

## 3. k6 Load Testing — Professional Tool Se Proof

### Kyun Python Script Se k6 Pe Shift Kiya

Pehla concurrency test humne Python (`httpx` + `asyncio`) se kiya tha — woh race condition dikhane ke liye theek tha. Lekin **k6** industry-standard load testing tool hai (companies isko production mein use karti hain) — isse mile numbers zyada credible hote hain resume/interview ke liye, aur yeh detailed performance metrics (latency percentiles, throughput) khud calculate karke deta hai.

### Test Script (`load_test.js`)

```javascript
import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = 'http://localhost:8000';
const TOKEN = '...'; // login se mila token
const FLASH_SALE_ID = 10;

export const options = {
  vus: 50,        // 50 Virtual Users (concurrent)
  duration: '5s', // 5 second tak chalao
};

export default function () {
  const payload = JSON.stringify({
    flash_sale_id: FLASH_SALE_ID,
    quantity: 1,
    idempotency_key: `k6-${__VU}-${__ITER}-${Date.now()}`,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`,
    },
  };

  const res = http.post(`${BASE_URL}/orders/`, payload, params);

  check(res, {
    'status is 200 or 400': (r) => r.status === 200 || r.status === 400,
  });
}
```

**Key concepts:**
- `vus: 50` — 50 "Virtual Users" simultaneously requests bhejte hain
- `duration: '5s'` — poore 5 second tak yeh continuously repeat hota hai (har VU jitni baar ho sake utni requests bhejta hai)
- `__VU` aur `__ITER` — k6 ke built-in variables (current virtual user number, current iteration) — inko use karke har request ki **unique idempotency key** banayi, taaki har request ek "naya order attempt" simulate kare, na ki ek hi retry
- `check(...)` — response validate karta hai; humne check kiya status `200` (success) ya `400` (out of stock) hona chahiye — **`500` (server crash) kabhi nahi aana chahiye**

### Result Jo Mila (Stock = 20)

```
checks_total.......: 481     91.331593/s
checks_succeeded...: 100.00% 481 out of 481
checks_failed......: 0.00%   0 out of 481

http_req_duration..............: avg=531.56ms  p(95)=1.46s
http_req_failed................: 95.84% (461 out of 481)
http_reqs......................: 481    91.331593/s
```

**Analysis:**
- **481 total requests** fire hui 5 second mein, 50 concurrent virtual users se
- **`checks_succeeded: 100%`** — matlab har response `200` ya `400` tha, koi `500`/crash nahi — system ne gracefully sab handle kiya
- **461 requests "out of stock" (400)** mili, matlab **20 requests successful (200)** hui — **exactly utni jitna stock tha (20)**
- **Zero overselling**, chahe 481 requests ek saath aayi ho
- **Throughput:** ~91 requests/second
- **Latency:** average 531ms, p95 1.46 second

### Resume Ke Liye Kaise Likhna Hai

> "Load-tested the booking API with k6 (50 concurrent virtual users, 481 requests in 5 seconds) — confirmed zero overselling with exactly the available stock (20 units) fulfilled and remaining requests cleanly rejected, at ~91 req/s throughput."

---

## Interview Mein In Teeno Ko Kaise Discuss Karna Hai

**Idempotency pooche jaye to:** "Maine duplicate request handling add ki — client ek unique idempotency key bhejta hai har order attempt ke saath, aur agar wahi key dobara aaye (retry/double-click ki wajah se), main naya order banane ki jagah purana wahi order return kar deta hoon — isse duplicate charges ya duplicate stock deduction nahi hote."

**Auto-cancel pooche jaye to:** "Maine ek background scheduler (APScheduler) laga ke unpaid orders ko automatically cancel karta hoon 15 minute ke baad, aur unka reserved stock wapas Redis mein release karta hoon — isse agar koi order banake payment kabhi na kare, woh stock hamesha ke liye locked nahi rehta."

**Load testing pooche jaye to:** "Maine k6 se 50 concurrent virtual users simulate kiye, 481 requests bheji 5 second mein — result mein exactly utni hi orders successful hui jitna stock tha, baaki cleanly rejected, zero server errors."

---

## Abhi Tak Ka Overall Project Status

- Auth (register/login/JWT) ✅
- Product/FlashSale/Order CRUD ✅
- Concurrency-safe booking (Redis Lua atomic decrement) ✅
- DB-Redis stock sync ✅
- Idempotency (duplicate request handling) ✅
- Auto-cancel unpaid orders (background scheduler) ✅
- k6 load testing with real metrics ✅

**Yeh ek complete, demoable, resume-ready checkpoint hai.**

## Next Steps (Optional, Time Permitting)

- README banana (architecture summary + benchmark numbers + setup instructions)
- Docker mein poori app ko bhi containerize karna (abhi sirf infra Docker mein hai, FastAPI app khud laptop pe chal rahi hai)
- AI-powered semantic search layer (agar scope badhana ho)