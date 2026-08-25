# SQLAlchemy column types aur relationship helpers import kar rahe hain.
from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, TIMESTAMP, Boolean

# Database side current timestamp function use karne ke liye func import.
from sqlalchemy.sql import func

# Base import kar rahe hain; isi se SQLAlchemy ko pata chalta hai ye classes tables hain.
from app.database import Base

from sqlalchemy.orm import relationship


# User class database ke users table ko represent karti hai.
class User(Base):
    # Actual database table ka naam users hoga.
    __tablename__ = "users"
    # User ka unique id; primary key har row ko uniquely identify karti hai.
    id = Column(Integer, primary_key=True, index=True)
    # User email; unique hai aur empty/null nahi ho sakta.
    email = Column(String(255), unique=True, nullable=False)
    # Password ka hash store hota hai, plain password kabhi store nahi karna chahiye.
    password_hash = Column(String(255), nullable=False)
    # User ne apna email verify kiya hai ya nahi; default False (naya user unverified hota hai).
    is_verified = Column(Boolean, default=False)
    # Temporary 6-digit verification code; verify hone ke baad None kar dete hain.
    verification_code = Column(String(6), nullable=True)
    # Row create hote hi database current timestamp set karega.
    created_at = Column(TIMESTAMP, server_default=func.now())


# Product class database ke products table ko represent karti hai.
class Product(Base):
    # Actual database table ka naam products hoga.
    __tablename__ = "products"
    # Product ka unique id.
    id = Column(Integer, primary_key=True, index=True)
    # Product ka naam; required field hai.
    name = Column(String(255), nullable=False)
    # Product price; Numeric money values ke liye better hai because decimal precision stable rehti hai.
    price = Column(Numeric(10, 2), nullable=False)
    # Product ka total available stock.
    total_stock = Column(Integer, nullable=False)
    # Product create hone ka timestamp database khud set karega.
    created_at = Column(TIMESTAMP, server_default=func.now())


# FlashSale class flash sale events ko database mein store karti hai.
class FlashSale(Base):
    # Actual database table ka naam flash_sales hoga.
    __tablename__ = "flash_sales"
    # Flash sale ka unique id.
    id = Column(Integer, primary_key=True, index=True)
    # Ye batata hai flash sale kis product ke liye hai; products.id se link hai.
    product_id = Column(Integer, ForeignKey("products.id"))
    # Sale kab start hogi.
    start_time = Column(TIMESTAMP, nullable=False)
    # Sale kab end hogi.
    end_time = Column(TIMESTAMP, nullable=False)
    # Ek user maximum kitni quantity le sakta hai; default 1.
    max_per_user = Column(Integer, default=1)
    # Sale ka status, jaise scheduled/active/ended; default scheduled.
    status = Column(String(20), default="scheduled")
    # Flash sale create hone ka timestamp.
    created_at = Column(TIMESTAMP, server_default=func.now())


# Order class user ke purchase/order records ko store karti hai.
class Order(Base):
    # Actual database table ka naam orders hoga.
    __tablename__ = "orders"
    # Order ka unique id.
    id = Column(Integer, primary_key=True, index=True)
    # Order kis user ne kiya; users.id se link hai.
    user_id = Column(Integer, ForeignKey("users.id"))
    # Order kis flash sale mein hua; flash_sales.id se link hai.
    flash_sale_id = Column(Integer, ForeignKey("flash_sales.id"))
    # User ne kitni quantity order ki; default 1.
    quantity = Column(Integer, default=1)
    # Order ka current status; default pending.
    status = Column(String(20), default="pending")
    # Duplicate order requests rokne ke liye unique key.
    idempotency_key = Column(String(255), unique=True, nullable=False)

    refund_status = Column(String(20), nullable=True)
    berth_preference = Column(String(20), nullable=True)   # <-- naya column
    passenger_names = Column(String(500), nullable=True)   
    # Order create hone ka timestamp.
    created_at = Column(TIMESTAMP, server_default=func.now())


    flash_sale = relationship("FlashSale")