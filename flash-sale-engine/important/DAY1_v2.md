# Day 3 — Auth System + Product APIs Explanation

Yeh document batata hai Day 0-2 mein kya hua (quick recap) aur Day 3 mein humne kya naya banaya — auth system (register/login/JWT/protected routes) aur Product APIs.

---

## Quick Recap — Ab Tak Ka Safar

- **Day 0:** Docker (Postgres, Redis, RabbitMQ) setup, Python venv, FastAPI project structure
- **Day 1:** `models.py` mein 4 tables define ki (User, Product, FlashSale, Order), Alembic se database mein actually create ki
- **Day 3 (aaj):** Auth system poora banaya (register, login, JWT tokens, protected routes) + Product APIs shuru ki

(Detailed explanation Day 0 aur Day 1 ki `DAY0_SETUP_NOTES.md` aur `DAY1_TABLES_EXPLAINED.md` files mein hai.)

---

## 1. Naya Files Jo Banayi

```
app/
├── config.py          (naya — settings ek jagah)
├── schemas.py          (naya — request/response ka shape)
├── auth_utils.py        (naya — password hashing + JWT logic)
├── routers/
│   ├── auth.py          (naya — register/login/me endpoints)
│   └── products.py      (naya — product create/get/list endpoints)
```

---

## 2. `app/config.py` — Settings Ek Jagah

```python
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

**Kyun banaya:** JWT token banane ke liye baar-baar `SECRET_KEY`, `ALGORITHM`, expiry time chahiye hoti hai. Ek jagah rakh diya taaki har file mein `.env` dobara load na karni pade, aur agar kal expiry time change karna ho, sirf ek jagah edit karni pade.

---

## 3. `app/schemas.py` — Pydantic Models (Request/Response Ka Shape)

```python
from pydantic import BaseModel, EmailStr
from decimal import Decimal

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class ProductCreate(BaseModel):
    name: str
    price: Decimal
    total_stock: int

class ProductOut(BaseModel):
    id: int
    name: str
    price: Decimal
    total_stock: int

    class Config:
        from_attributes = True
```

**Yeh `models.py` se alag kyun hai:** `models.py` batata hai **database ka structure** kaisa hai. `schemas.py` batata hai **API ka structure** kaisa hai — matlab jab koi request bheje ya response paaye, uska shape kya hoga. Dono alag isliye rakhte hain kyunki kabhi API ka shape DB se thoda alag hota hai — jaise `UserCreate` mein `password` hai (plain text, jo user bhejta hai), lekin DB (`User` table) mein `password_hash` hai (encrypted version) — yeh dono ek jaisa nahi ho sakta, isliye alag classes chahiye.

**`EmailStr`:** Yeh ek special Pydantic type hai jo khud check karta hai "kya yeh sach mein ek valid email format hai" (jaise `@` hona chahiye, domain hona chahiye). Isko kaam karne ke liye `email-validator` package chahiye hoti hai (isliye humne woh install kiya tha).

**`ProductCreate` vs `ProductOut`:** `ProductCreate` mein sirf woh fields hain jo user **dega** product banate waqt (naam, price, stock). `ProductOut` mein `id` bhi hai kyunki jab response **wapas** bhejte hain, tab ID bhi dikhani hai (jo database ne khud generate ki). Input aur output ka shape alag hone ki wajah se dono classes alag banayi.

**`class Config: from_attributes = True`:** Yeh Pydantic ko batata hai "yeh data seedha ek Python object (SQLAlchemy row) se aa raha hai, normal dictionary se nahi." Isse Pydantic khud `product.id`, `product.name` jaise attributes padh leta hai object se.

---

## 4. `app/auth_utils.py` — Password Hashing + JWT Logic

### Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Kyun password ko direct store nahi karte:** Agar database leak ho jaye kabhi (hack ho jaye), to attacker ko seedha sab logon ka password mil jayega. Iski jagah hum password ka ek **hash** (scrambled, one-way encrypted version) store karte hain — jaise `flashsale123` ban jata hai `$2b$12$dvWKB3.LQPbouihCvaFYf...`. Yeh process **irreversible** hai — hash se wapas original password nikaalna practically impossible hai.

**Login ke time kya hota hai:** User jo password deta hai, usko bhi hash kiya jata hai, aur dono hashes ko compare kiya jata hai (`verify_password`) — original passwords kabhi directly compare nahi hote.

**`bcrypt` version issue jo aaya tha:** Humein `bcrypt==4.0.1` specifically install karna pada kyunki `passlib` library naye `bcrypt` (4.1+) versions ke internal changes ke saath compatible nahi thi — yeh ek library compatibility bug tha, humare code ki galti nahi.

### JWT Token Banana

```python
from datetime import datetime, timedelta
from jose import jwt
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**JWT kya hota hai (bahut simple):** Ek "signed" text string jisme kuch data chhupa hota hai (jaise "yeh user ID 5 hai, aur yeh token 30 min tak valid hai"). "Signed" ka matlab hai — `SECRET_KEY` se yeh is tarah lock kiya jata hai ki koi bhi is data ko change nahi kar sakta bina secret key jaane. Agar koi token ke andar ka data tamper karne ki koshish kare, verification fail ho jayegi.

**Real-life analogy:** Yeh ek movie ticket jaisa hai jisme cinema ka stamp laga hai — tu ticket dikha ke andar ja sakta hai, lekin agar tu khud se ticket pe seat number badal de, stamp match nahi karega aur guard pakad lega.

### Protected Route Ka Logic (`get_current_user`)

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    token = credentials.credentials
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception
    return user
```

**Yeh function kya karta hai step-by-step:**
1. Request ke `Authorization` header se token nikaalta hai
2. `jwt.decode(...)` se token ko "unlock" karta hai `SECRET_KEY` se — agar galat key se bana hai ya expire ho gaya, error aayega
3. Token ke andar se `user_id` nikaalta hai
4. Us ID se database mein user dhoondhta hai
5. Sab sahi ho to user return karta hai, warna `401 Unauthorized` error

**`HTTPBearer` vs `OAuth2PasswordBearer` (issue jo aaya tha):** Shuru mein humne `OAuth2PasswordBearer` use kiya tha, jisse Swagger UI ek **username/password form** dikhata hai "Authorize" click karne pe — kyunki yeh scheme assume karta hai tera login endpoint form-data leta hai. Lekin humara `/auth/login` **JSON** leta hai, form-data nahi — mismatch ho gaya. `HTTPBearer` pe switch kiya, jisse Swagger UI sirf ek **plain text box** deta hai jahan seedha token paste kar sakte hain — zyada simple aur humare setup ke sahi match.

**Yeh function "dependency" ki tarah kaam karta hai:** Jab kisi route mein hum likhte hain:
```python
def some_route(current_user: User = Depends(get_current_user)):
```
Iska matlab: "Is route ko call karne se pehle, `get_current_user` chalao. Agar woh successfully user de, tabhi route ka code chalao. Warna turant error de do." Yeh FastAPI ka **Dependency Injection** pattern hai — isi wajah se humein har route mein manually token check karne ka code nahi likhna padta, ek dependency reuse ho jaati hai.

---

## 5. `app/routers/auth.py` — Register, Login, Me Endpoints

```python
router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(email=user.email, password_hash=hash_password(user.password))
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email}


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == credentials.email).first()
    if not db_user or not verify_password(credentials.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(data={"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me")
def read_current_user(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}
```

**`prefix="/auth"`:** Is file ki saari APIs `/auth/...` se shuru hongi.

**`register`:**
1. Pehle check karta hai email pehle se exist to nahi karta (duplicate account na bane)
2. Password ko hash karke naya user object banata hai
3. `db.add(new_user)` — DB session ko batata hai "yeh naya row insert karna hai" (abhi tak save nahi hua)
4. `db.commit()` — ab actually database mein permanently save hota hai
5. `db.refresh(new_user)` — database se wapas latest data le aata hai (jaise auto-generated `id`, `created_at`)

**`login`:**
1. Email se user dhoondhta hai
2. Password verify karta hai (hash compare karke)
3. Sab sahi ho to JWT token banake deta hai, jisme `"sub": str(db_user.id)` hota hai — `"sub"` (subject) JWT ka standard field hai jisme user ki identity store karte hain

**`/me`:** Yeh ek chhota test route hai jo confirm karta hai protection kaam kar raha hai — sirf valid token wala hi apna data dekh sakta hai.

---

## 6. `app/routers/products.py` — Product APIs

```python
router = APIRouter(prefix="/products", tags=["products"])

@router.post("/", response_model=ProductOut)
def create_product(product: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_product = Product(name=product.name, price=product.price, total_stock=product.total_stock)
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.get("/", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()
```

**`create_product` protected kyun hai, `get_product`/`list_products` public kyun hain:** Product **banana** ek sensitive action hai (koi bhi random insaan product create nahi kar sakta) — isliye `current_user: User = Depends(get_current_user)` lagaya. Lekin product **dekhna/search karna** ek normal, public action hai (jaise Amazon pe bina login kiye bhi product dekh sakte ho) — isliye yeh do routes bina protection ke hain.

**`{product_id}` ka matlab:** Yeh ek **path parameter** hai — matlab URL mein `/products/5` jaise hit karoge to `product_id = 5` ban jayega function ke andar. FastAPI khud isko sahi Python type (`int`) mein convert kar deta hai.

**`response_model=list[ProductOut]`:** Batata hai yeh endpoint ek **list** return karega, jisme har item `ProductOut` shape ka hoga.

---

## 7. `app/main.py` Mein Routers Jodna

```python
from app.routers import auth, products

app.include_router(auth.router)
app.include_router(products.router)
```

**Kyun zaroori hai:** Sirf router file banane se kaam nahi hota — FastAPI app ko batana padta hai "yeh routes bhi include karo." `include_router` isi kaam ke liye hai — jitne bhi router files banate jayenge, sabko yahan register karna padega.

---

## Abhi Tak Ka Status

- Auth system fully working: register, login, JWT tokens, protected routes
- Password hashing secure hai (bcrypt), plain password kabhi store nahi hota
- Product create (protected), get, list (public) APIs kaam kar rahe hain
- Dependency Injection pattern samajh liya (`Depends(get_current_user)`)

## Abhi Tak Kya Nahi Kiya (Next Steps)

- `FlashSale` router abhi banana baaki hai
- Concurrency-safe booking logic (Day 2 ka planned core kaam, abhi tak nahi hua)
- Idempotency, Redis atomic stock decrement — abhi touch nahi kiya

**Next kaam:** `FlashSale` router banana (flash sale create/get APIs), phir asli interesting part shuru hoga — concurrent booking requests ko race-condition-safe banana.