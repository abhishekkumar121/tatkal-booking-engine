from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Order, FlashSale, Product, User
from app.schemas import OrderCreate, OrderOut , PaymentRequest
from app.auth_utils import get_current_user
from app.redis_client import redis_client
from app.lua_scripts import DECREMENT_STOCK_SCRIPT

router = APIRouter(prefix="/orders", tags=["orders"])

decrement_script = redis_client.register_script(DECREMENT_STOCK_SCRIPT)


@router.post("/", response_model=OrderOut)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Rate limiting — per user, per second
    rate_limit_key = f"ratelimit:order:{current_user.id}"
    request_count = redis_client.incr(rate_limit_key)
    if request_count == 1:
        redis_client.expire(rate_limit_key, 2)  # 2 second window

    if request_count > 3:
        raise HTTPException(status_code=429, detail="Too many requests — please slow down")


    # Queue gate — agar is flash sale ki active queue hai, user "allowed" hona chahiye
    queue_active = redis_client.sismember("active_queues", str(order.flash_sale_id))
    if queue_active:
        allowed_key = f"allowed:{order.flash_sale_id}"
        if redis_client.zscore(allowed_key, str(current_user.id)) is None:   # <-- badla: sismember → zscore
            raise HTTPException(status_code=403, detail="Please join the queue and wait for your turn before booking")
        redis_client.zrem(allowed_key, str(current_user.id))                  # <-- badla: srem → zrem



    # Idempotency check — pehle dekh lo yeh request pehle kabhi aayi thi kya
    existing_order = db.query(Order).filter(Order.idempotency_key == order.idempotency_key).first()
    if existing_order:
        return existing_order  # purana wahi order wapas de do, naya mat banao

    flash_sale = db.query(FlashSale).filter(FlashSale.id == order.flash_sale_id).first()
    if not flash_sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")

    user_order_count = db.query(Order).filter(
        Order.user_id == current_user.id,
        Order.flash_sale_id == order.flash_sale_id,
        Order.status.in_(["pending", "confirmed"])
    ).count()

    if user_order_count >= flash_sale.max_per_user:
        raise HTTPException(
            status_code=429,
            detail=f"Booking limit reached — max {flash_sale.max_per_user} ticket(s) per user for this window"
        )

    stock_key = f"stock:{flash_sale.product_id}"

    # Atomic check + decrement — Redis ke andar ek hi step mein
    result = decrement_script(keys=[stock_key], args=[order.quantity])

    if result == -2:
        raise HTTPException(status_code=500, detail="Stock not initialized in Redis")
    if result == -1:
        raise HTTPException(status_code=400, detail="Out of stock")

    # Redis mein decrement safal hua — ab DB mein order record banao
    new_order = Order(
        user_id=current_user.id,
        flash_sale_id=order.flash_sale_id,
        quantity=order.quantity,
        status="pending",
        idempotency_key=order.idempotency_key,
        berth_preference=order.berth_preference,
        passenger_names=order.passenger_names

    )
    db.add(new_order)

    # DB ke product stock ko bhi Redis ke saath sync karo
    product = db.query(Product).filter(Product.id == flash_sale.product_id).first()
    product.total_stock = result  # Lua script ne jo naya stock return kiya, wahi use karo

    db.commit()
    db.refresh(new_order)
    return new_order


@router.post("/{order_id}/pay", response_model=OrderOut)
def pay_for_order(
    order_id: int,
    payment: PaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if order.status != "pending":
        raise HTTPException(status_code=400, detail=f"Order already {order.status}, cannot pay again")

    if payment.simulate_failure:
        order.status = "payment_failed"
        order.refund_status = "initiated"  # naya
        redis_client.incrby(f"stock:{order.flash_sale.product_id}", order.quantity)
        db.commit()
        db.refresh(order)
        raise HTTPException(status_code=402, detail="Payment failed — seat released, refund initiated")


    order.status = "confirmed"
    db.commit()
    db.refresh(order)
    return order



@router.get("/{order_id}/refund-status")
def get_refund_status(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(Order).filter(Order.id == order_id, Order.user_id == current_user.id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if not order.refund_status:
        raise HTTPException(status_code=400, detail="No refund associated with this order")
    return {"order_id": order.id, "refund_status": order.refund_status}