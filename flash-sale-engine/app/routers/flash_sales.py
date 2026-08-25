# Flash sale related APIs yahan likhi jayengi; abhi ye feature implement nahi hua hai.
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.database import get_db
from app.models import FlashSale, Product, User
from app.schemas import FlashSaleCreate, FlashSaleOut
from app.auth_utils import get_current_user
from datetime import datetime, timezone
from app.schemas import FlashSaleCreate, FlashSaleOut, BulkCreateRequest, BulkCreateResult, FlashSaleWithProduct
from app.redis_client import redis_client
from app.timeutils import now_ist


router = APIRouter(prefix="/flash-sales", tags=["flash_sales"])


@router.post("/", response_model=FlashSaleOut)
def create_flash_sale(
    sale: FlashSaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    product = db.query(Product).filter(Product.id == sale.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    new_sale = FlashSale(
        product_id=sale.product_id,
        start_time=sale.start_time,
        end_time=sale.end_time,
        max_per_user=sale.max_per_user,
        status="scheduled"
    )
    db.add(new_sale)
    db.commit()
    db.refresh(new_sale)
    return new_sale


@router.get("/with-details", response_model=list[FlashSaleWithProduct])
def list_flash_sales_with_details(db: Session = Depends(get_db)):
    now = now_ist()
    sales = db.query(FlashSale).filter(FlashSale.end_time >= now).all()
    results = []
    for sale in sales:
        product = db.query(Product).filter(Product.id == sale.product_id).first()
        if now < sale.start_time:
            status = "scheduled"
        elif sale.start_time <= now <= sale.end_time:
            status = "live"
        else:
            status = "ended"
        results.append({
            "id": sale.id,
            "product_id": sale.product_id,
            "product_name": product.name if product else "Unknown",
            "price": product.price if product else 0,
            "total_stock": product.total_stock if product else 0,
            "start_time": sale.start_time,
            "end_time": sale.end_time,
            "status": status,
            "max_per_user": sale.max_per_user,
        })
    return results


@router.get("/{flash_sale_id}", response_model=FlashSaleOut)
def get_flash_sale(flash_sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(FlashSale).filter(FlashSale.id == flash_sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")
    return sale


@router.get("/{flash_sale_id}/status")
def get_flash_sale_status(flash_sale_id: int, db: Session = Depends(get_db)):
    sale = db.query(FlashSale).filter(FlashSale.id == flash_sale_id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Flash sale not found")

    now = now_ist()

    if now < sale.start_time:
        live_status = "scheduled"
    elif sale.start_time <= now <= sale.end_time:
        live_status = "live"
    else:
        live_status = "ended"

    return {
        "id": sale.id,
        "status": live_status,
        "product_id": sale.product_id,
        "start_time": sale.start_time,
        "end_time": sale.end_time
    }



@router.get("/", response_model=list[FlashSaleOut])
def list_flash_sales(db: Session = Depends(get_db)):
    now = now_ist()
    return db.query(FlashSale).filter(FlashSale.end_time >= now).all()



@router.post("/bulk-create", response_model=list[BulkCreateResult])
def bulk_create(
    payload: BulkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    results = []
    for item in payload.items:
        new_product = Product(
            name=item.name,
            price=item.price,
            total_stock=item.total_stock
        )
        db.add(new_product)
        db.flush()  # ID turant chahiye, poora commit kiye bina

        redis_client.set(f"stock:{new_product.id}", new_product.total_stock)

        new_sale = FlashSale(
            product_id=new_product.id,
            start_time=item.start_time,
            end_time=item.end_time,
            max_per_user=item.max_per_user,
            status="scheduled"
        )
        db.add(new_sale)
        db.flush()

        results.append({"product": new_product, "flash_sale": new_sale})

    db.commit()
    for r in results:
        db.refresh(r["product"])
        db.refresh(r["flash_sale"])

    return results




