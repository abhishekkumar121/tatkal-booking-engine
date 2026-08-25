# Flash-Engine Project Guide

Ye file tumhare project ka high-level guide hai. Isko read karke tumhe pata chalega ki har important file ka kya kaam hai, project ka flow kya hai, aur `models.py` aur `schemas.py` mein difference kya hota hai.

## Big Picture

Flash-Engine ek FastAPI backend project hai.

Basic request flow:

```text
Client request
    -> app/main.py
    -> router file, jaise app/routers/auth.py
    -> database.py se DB session
    -> models.py ke through PostgreSQL table access
    -> schemas.py se request/response validation
    -> client ko JSON response
```

Simple words mein:

- FastAPI API routes handle karta hai.
- SQLAlchemy database se baat karta hai.
- Pydantic request/response validate karta hai.
- Alembic database tables create/update karta hai.
- Docker Postgres, Redis, RabbitMQ services chalata hai.

## Root Files

### requirements.txt

Ye file Python packages ki list hai jo project ko chalane ke liye required hain.

Important packages:

- `fastapi`: API framework.
- `uvicorn`: FastAPI app run karne wala server.
- `sqlalchemy`: ORM, database tables ko Python classes ke through handle karta hai.
- `alembic`: database migration tool.
- `psycopg2-binary`: PostgreSQL driver.
- `redis`: Redis se connect karne ke liye.
- `pika`: RabbitMQ se connect karne ke liye.
- `python-jose`: JWT token banane/verify karne ke liye.
- `passlib[bcrypt]`: password hashing ke liye.
- `python-dotenv`: `.env` file load karne ke liye.
- `pydantic`: request/response validation ke liye.
- `email-validator`: email format validate karne ke liye.

### docker-compose.yml

Ye file Docker services define karti hai.

Is project mein 3 services hain:

- `postgres`: main database.
- `redis`: fast cache/atomic stock logic ke liye future use.
- `rabbitmq`: background queue/order processing ke liye future use.

Postgres ka host port `5433` hai, container port `5432` hai. Matlab app local machine se `localhost:5433` par connect karegi.

### alembic.ini

Ye Alembic migration tool ki configuration file hai.

Alembic ka kaam hai database schema changes ko track karna. Jaise jab `models.py` mein new table/column add karte ho, Alembic migration generate karke database update karta hai.

## app Folder

### app/__init__.py

Ye file Python ko batati hai ki `app` folder ek Python package hai.

Iski wajah se imports kaam karte hain:

```python
from app.database import get_db
```

### app/main.py

Ye FastAPI app ka entry point hai.

Is file mein:

- FastAPI app create hoti hai.
- Routers app ke saath connect hote hain.
- `/health` endpoint define hota hai.

Current important route:

```text
GET /health
```

Ye route server alive hai ya nahi check karta hai.

Important note:

`products.py` router bana hua hai, lekin agar `main.py` mein include nahi hoga to product APIs active nahi hongi.

Products router active karne ke liye:

```python
from app.routers import auth, products

app.include_router(auth.router)
app.include_router(products.router)
```

### app/database.py

Ye database connection setup file hai.

Is file ka kaam:

- `.env` load karna.
- `DATABASE_URL` read karna.
- SQLAlchemy engine create karna.
- DB session factory create karna.
- `Base` create karna, jisse models inherit karte hain.
- `get_db()` dependency provide karna.

`get_db()` har API request ko ek DB session deta hai aur request complete hone ke baad session close karta hai.

### app/config.py

Ye project settings/config file hai.

Is file mein:

- `SECRET_KEY`: JWT sign/verify karne ke liye.
- `ALGORITHM`: JWT algorithm, currently `HS256`.
- `ACCESS_TOKEN_EXPIRE_MINUTES`: token expiry, currently 30 minutes.

Simple words mein, auth-related settings yahan rakhi hain.

### app/models.py

Ye database tables ka blueprint hai.

Is file mein SQLAlchemy models hain:

- `User`: users table.
- `Product`: products table.
- `FlashSale`: flash_sales table.
- `Order`: orders table.

Example:

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
```

Iska matlab database mein `users` table banegi jisme `id` aur `email` columns honge.

### app/schemas.py

Ye API request aur response ka shape define karta hai.

Is file mein Pydantic schemas hain:

- `UserCreate`: register request body.
- `UserLogin`: login request body.
- `Token`: login response.
- `ProductCreate`: product create request body.
- `ProductOut`: product response body.

Example:

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
```

Iska matlab jab user register karega, request body mein valid email aur password hona chahiye.

### app/auth_utils.py

Ye authentication helper file hai.

Is file ka kaam:

- Password hash karna.
- Password verify karna.
- JWT access token create karna.
- Token validate karke current user fetch karna.

Important functions:

- `hash_password(password)`: plain password ko hash banata hai.
- `verify_password(plain_password, hashed_password)`: login ke time password check karta hai.
- `create_access_token(data)`: JWT token banata hai.
- `get_current_user(...)`: protected route ke liye logged-in user nikaalta hai.

## app/routers Folder

### app/routers/__init__.py

Ye file Python ko batati hai ki `routers` folder ek Python package hai.

### app/routers/auth.py

Ye auth-related API endpoints define karta hai.

Routes:

```text
POST /auth/register
POST /auth/login
GET /auth/me
```

`/auth/register`:

- User email already exist karta hai ya nahi check karta hai.
- Password hash karta hai.
- New user DB mein save karta hai.
- User id aur email return karta hai.

`/auth/login`:

- Email se user dhoondhta hai.
- Password verify karta hai.
- Correct credentials par JWT token return karta hai.

`/auth/me`:

- Bearer token validate karta hai.
- Current logged-in user ka id aur email return karta hai.

### app/routers/products.py

Ye product-related API endpoints define karta hai.

Routes:

```text
POST /products/
GET /products/{product_id}
GET /products/
```

`POST /products/`:

- New product create karta hai.
- Protected route hai, token required.

`GET /products/{product_id}`:

- Given product id se product fetch karta hai.

`GET /products/`:

- Saare products list karta hai.

### app/routers/flash_sales.py

Ye file future flash sale APIs ke liye reserved hai.

Abhi isme actual endpoints implement nahi hue hain.

Future mein yahan ho sakta hai:

- Flash sale create.
- Flash sale list.
- Flash sale activate/end.
- Flash sale booking/order route.

## alembic Folder

### alembic/env.py

Ye Alembic ko app ke database models se connect karta hai.

Is file ka kaam:

- `.env` load karna.
- `DATABASE_URL` read karna.
- `Base.metadata` Alembic ko dena.
- Models import karna taaki Alembic ko tables ka structure pata chale.
- Online/offline migration run karna.

Simple words mein, ye file Alembic ko batati hai ki database schema ka source `app/models.py` hai.

### alembic/versions/7eb15e398194_create_initial_tables.py

Ye migration file hai.

Is file ka kaam:

- `upgrade()` mein tables create karna.
- `downgrade()` mein tables remove karna.

Ye tables create karti hai:

- `products`
- `users`
- `flash_sales`
- `orders`

## important Folder

### important/DAY0_SETUP_NOTES.md

Ye setup explanation notes hain.

Isme explain hai:

- Virtual environment kya hota hai.
- Docker ka setup.
- `requirements.txt`.
- `.env`.
- Folder structure.
- Database setup.
- Port conflict troubleshooting.

### important/DAY1.md

Ye database tables explanation file hai.

Isme explain hai:

- ORM kya hota hai.
- `models.py` ka role.
- `User`, `Product`, `FlashSale`, `Order` tables.
- Alembic migration ka flow.

### important/DAY3.md

Ye auth aur product APIs explanation file hai.

Isme explain hai:

- `config.py`.
- `schemas.py`.
- Password hashing.
- JWT tokens.
- Protected routes.
- Auth endpoints.
- Product endpoints.

## Difference Between Model and Schema

Ye project samajhne ke liye sabse important concept hai.

### Model kya hota hai?

Model database table ka blueprint hota hai.

Tumhare project mein models `app/models.py` mein hain.

Example:

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
```

Iska matlab:

- Database mein `users` table hogi.
- Usme `id`, `email`, `password_hash` columns honge.
- `email` unique hoga.
- `password_hash` required hoga.

Model ka use hota hai:

- Database table define karne ke liye.
- Database mein data insert/read/update/delete karne ke liye.
- SQLAlchemy queries mein.

Example:

```python
db.query(User).filter(User.email == user.email).first()
```

Yahan `User` model use ho raha hai database se user dhoondhne ke liye.

### Schema kya hota hai?

Schema API request aur response ka shape hota hai.

Tumhare project mein schemas `app/schemas.py` mein hain.

Example:

```python
class UserCreate(BaseModel):
    email: EmailStr
    password: str
```

Iska matlab:

- Register API mein client ko email aur password bhejna hoga.
- Email valid format mein hona chahiye.
- Password string hona chahiye.

Schema ka use hota hai:

- Request body validate karne ke liye.
- Response shape control karne ke liye.
- Sensitive fields hide karne ke liye.

Example:

```python
def register(user: UserCreate, db: Session = Depends(get_db)):
```

Yahan `UserCreate` schema use ho raha hai request body validate karne ke liye.

### Model vs Schema Simple Comparison

| Point | Model | Schema |
|------|-------|--------|
| File | `app/models.py` | `app/schemas.py` |
| Library | SQLAlchemy | Pydantic |
| Purpose | Database table ka structure | API request/response ka structure |
| Used for | DB operations | Validation and serialization |
| Example class | `User`, `Product` | `UserCreate`, `ProductOut` |
| Data source | Database rows | Client request / API response |

### User Example

Register request mein client ye bhejta hai:

```json
{
  "email": "test@example.com",
  "password": "mypassword"
}
```

Ye data pehle `UserCreate` schema validate karta hai.

Phir route password hash karta hai.

Phir `User` model se database row banata hai:

```python
new_user = User(
    email=user.email,
    password_hash=hash_password(user.password)
)
```

Notice karo:

- Schema mein `password` hai.
- Model mein `password_hash` hai.

Kyun?

Kyuki API mein user plain password bhejta hai, but database mein plain password store nahi karte. Database mein only hashed password store hota hai.

### Product Example

Product create request:

```json
{
  "name": "Phone",
  "price": "999.99",
  "total_stock": 100
}
```

Ye `ProductCreate` schema validate karta hai.

Phir DB mein `Product` model save hota hai:

```python
new_product = Product(
    name=product.name,
    price=product.price,
    total_stock=product.total_stock
)
```

Response mein `ProductOut` schema use hota hai:

```python
class ProductOut(BaseModel):
    id: int
    name: str
    price: Decimal
    total_stock: int
```

Request mein `id` nahi hota, kyunki DB generate karta hai. Response mein `id` hota hai, kyunki client ko batana hota hai ki product ka database id kya hai.

## Current Project Status

Implemented:

- FastAPI app setup.
- Database connection setup.
- SQLAlchemy models.
- Alembic migration.
- Auth register/login/me APIs.
- JWT token logic.
- Product router file.
- Docker services for Postgres, Redis, RabbitMQ.

Partially done:

- Product APIs written hain, but `main.py` mein router include karna baaki hai.

Not implemented yet:

- Flash sale APIs.
- Order booking API.
- Redis-based atomic stock decrement.
- RabbitMQ-based async order processing.
- Full concurrency-safe flash sale engine logic.

