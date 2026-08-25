# FastAPI class import kar rahe hain, isi se web app banta hai.
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Auth router import kar rahe hain jisme register/login/me APIs likhi hain.
from app.routers import auth , products , flash_sales , orders ,queue

from app.scheduler import scheduler

from fastapi.middleware.cors import CORSMiddleware
import asyncio
import os
from app.database import SessionLocal
from app.database import engine
from app.models import FlashSale, Product
from app.timeutils import now_ist
from app.tracing import configure_tracing



# FastAPI app ka main object bana rahe hain; title docs page par dikhega.
app = FastAPI(title="Flash Sale Engine")
configure_tracing(app, engine)

frontend_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGIN",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth wale saare routes main app ke andar connect kar rahe hain.
app.include_router(auth.router)
app.include_router(products.router)
app.include_router(flash_sales.router)
app.include_router(orders.router)
app.include_router(queue.router)


@app.on_event("startup")
def start_scheduler():
    scheduler.start()

# Ye decorator batata hai ki GET request "/health" URL par aayegi to niche wala function chalega.
@app.get("/health")
# Health check function; server alive hai ya nahi check karne ke liye.
def health():
    # Client ko simple JSON response bhej rahe hain.
    return {"status": "ok"}


@app.websocket("/ws/flash-sales/{flash_sale_id}/stock")
async def flash_sale_stock_socket(websocket: WebSocket, flash_sale_id: int):
    await websocket.accept()
    try:
        while True:
            db = SessionLocal()
            try:
                sale = db.query(FlashSale).filter(FlashSale.id == flash_sale_id).first()
                if not sale:
                    await websocket.send_json({"error": "Flash sale not found"})
                    await websocket.close(code=1008)
                    return

                product = db.query(Product).filter(Product.id == sale.product_id).first()
                now = now_ist()
                if now < sale.start_time:
                    live_status = "scheduled"
                elif sale.start_time <= now <= sale.end_time:
                    live_status = "live"
                else:
                    live_status = "ended"

                await websocket.send_json({
                    "id": sale.id,
                    "status": live_status,
                    "product_id": sale.product_id,
                    "total_stock": product.total_stock if product else 0,
                    "start_time": sale.start_time.isoformat(),
                    "end_time": sale.end_time.isoformat(),
                })
            finally:
                db.close()

            await asyncio.sleep(1)
    except WebSocketDisconnect:
        return
