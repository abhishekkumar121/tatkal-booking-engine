# Pydantic BaseModel API request/response validation ke liye use hota hai.
from pydantic import BaseModel, EmailStr

# Decimal price jaise exact money values ke liye use hota hai.
from decimal import Decimal

from datetime import datetime


# Register request ka data shape define karta hai.
class UserCreate(BaseModel):
    # User ka email; EmailStr valid email format check karta hai.
    email: EmailStr
    # User ka plain password request mein aata hai; DB mein hash store hoga.
    password: str

# Login request ka data shape define karta hai.
class UserLogin(BaseModel):
    # Login ke liye email.
    email: EmailStr
    # Login ke liye password.
    password: str

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str

# Login success hone ke baad token response ka shape.
class Token(BaseModel):
    # JWT access token jo client future requests mein bhejega.
    access_token: str
    # Token type usually bearer hota hai.
    token_type: str


# Product create karne ke request body ka shape.
class ProductCreate(BaseModel):
    # Product ka naam.
    name: str
    # Product ka price exact decimal value mein.
    price: Decimal
    # Product ka total stock.
    total_stock: int

# Product response ka shape; ye client ko wapas bheja jayega.
class ProductOut(BaseModel):
    # Database generated product id.
    id: int
    # Product ka naam.
    name: str
    # Product ka price.
    price: Decimal
    # Product ka total stock.
    total_stock: int

    # Pydantic configuration class.
    class Config:
        # SQLAlchemy object ke attributes se response banana allow karta hai.
        from_attributes = True


class FlashSaleCreate(BaseModel):
    product_id: int
    start_time: datetime
    end_time: datetime
    max_per_user: int = 1

class FlashSaleOut(BaseModel):
    id: int
    product_id: int
    start_time: datetime
    end_time: datetime
    max_per_user: int
    status: str

    class Config:
        from_attributes = True

        

class OrderCreate(BaseModel):
    flash_sale_id: int
    quantity: int = 1
    idempotency_key: str
    berth_preference: str | None = None
    passenger_names: str | None = None

class OrderOut(BaseModel):
    id: int
    user_id: int
    flash_sale_id: int
    quantity: int
    status: str
    refund_status: str | None = None
    berth_preference: str | None = None
    passenger_names: str | None = None

    class Config:
        from_attributes = True



class PaymentRequest(BaseModel):
    simulate_failure: bool = False

class BulkItem(BaseModel):
    name: str
    price: Decimal
    total_stock: int
    start_time: datetime
    end_time: datetime
    max_per_user: int = 1

class BulkCreateRequest(BaseModel):
    items: list[BulkItem]

class BulkCreateResult(BaseModel):
    product: ProductOut
    flash_sale: FlashSaleOut


class FlashSaleWithProduct(BaseModel):
    id: int
    product_id: int
    product_name: str
    price: Decimal
    total_stock: int
    start_time: datetime
    end_time: datetime
    status: str
    max_per_user: int       