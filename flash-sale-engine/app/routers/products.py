# FastAPI router, dependency, aur HTTP error helpers import kar rahe hain.
from fastapi import APIRouter, Depends, HTTPException

# SQLAlchemy database session type hint.
from sqlalchemy.orm import Session

# DB session dependency import kar rahe hain.
from app.database import get_db

# Product aur User database models import kar rahe hain.
from app.models import Product, User

# Product request/response schemas import kar rahe hain.
from app.schemas import ProductCreate, ProductOut

# Protected route ke liye current logged-in user dependency.
from app.auth_utils import get_current_user

# Products router bana rahe hain; saare endpoints /products prefix se start honge.
router = APIRouter(prefix="/products", tags=["products"])

from app.redis_client import redis_client


# POST /products/ endpoint product create karta hai.
@router.post("/", response_model=ProductOut)
# Product create function request body, DB session, aur current user leta hai.
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Naya Product object banate hain jo DB mein insert hoga.
    new_product = Product(
        # Request body se product name set karte hain.
        name=product.name,
        # Request body se product price set karte hain.
        price=product.price,
        # Request body se total stock set karte hain.
        total_stock=product.total_stock
    )
    # Product ko DB session mein add karte hain.
    db.add(new_product)
    # Transaction commit karke product database mein save karte hain.
    db.commit()
    # DB se latest product values reload karte hain, including generated id.
    db.refresh(new_product)


    # Redis mein bhi stock initialize karo
    redis_client.set(f"stock:{new_product.id}", new_product.total_stock)
    
    # Saved product object return karte hain; FastAPI ProductOut schema mein convert karega.
    return new_product


# GET /products/{product_id} endpoint single product fetch karta hai.
@router.get("/{product_id}", response_model=ProductOut)
# URL se product_id aur dependency se DB session milta hai.
def get_product(product_id: int, db: Session = Depends(get_db)):
    # Product id ke basis par database mein product dhoondhte hain.
    product = db.query(Product).filter(Product.id == product_id).first()
    # Agar product nahi mila to 404 error.
    if not product:
        # Client ko product not found error return karte hain.
        raise HTTPException(status_code=404, detail="Product not found")
    # Product mila to return karte hain.
    return product


# GET /products/ endpoint saare products list karta hai.
@router.get("/", response_model=list[ProductOut])
# List products function sirf DB session leta hai.
def list_products(db: Session = Depends(get_db)):
    # Products table ke saare rows fetch karke return karte hain.
    return db.query(Product).all()
