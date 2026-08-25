# Day 0 — Project Setup Explanation

Yeh document batata hai humne setup mein kya kiya aur **kyun** kiya. Isko project folder mein rakh le, jab bhi bhool jaye ki kis file ka kya kaam hai, yahan wapas aa jana.

---

## 1. Virtual Environment (`venv`)

```bash
python -m venv venv
source venv/Scripts/activate
```

**Kya hua:** Ek isolated Python environment bana jo sirf is project ke liye hai.

**Kyun zaroori hai:** Agar tu system-wide Python mein packages install karta, to har project same package versions share karta. Ek project ko `fastapi 0.100` chahiye, dusre ko `0.115` — dono clash kar jaate. `venv` har project ka apna alag "box" bana deta hai jahan uske packages isolated rehte hain.

**`(venv)` kya hai:** Jab activate karta hai, terminal ke shuru mein `(venv)` dikhta hai — iska matlab ab jo bhi `pip install` karega, woh sirf is project ke andar jayega, system mein nahi.

**Is folder ka role:** `venv/` folder khud commit nahi hota Git mein (bahut bada hota hai, aur machine-specific hota hai) — sirf `requirements.txt` commit hoti hai jisse koi bhi dobara `venv` bana sake.

---

## 2. Docker Desktop + `docker-compose.yml`

**Kya hua:** Teen services ko Docker containers ke through chalaya:
- **PostgreSQL** (port 5432) — main database
- **Redis** (port 6379) — caching + atomic operations ke liye
- **RabbitMQ** (port 5672, management UI 15672) — async message queue ke liye

**Kyun Docker use kiya, native install nahi:**
- Har service ko manually install karna (Postgres installer, Redis Windows port, RabbitMQ + Erlang setup) time-consuming aur error-prone hota
- Docker ek command (`docker compose up -d`) se teeno start kar deta hai, isolated, bina system ko "dirty" kiye
- Jab project khatam ho ya kisi aur machine pe move kare, sirf `docker-compose.yml` file chahiye — same setup turant reproduce ho jata hai

**`docker compose up -d` mein `-d` kya hai:** "detached mode" — matlab containers background mein chalte hain, terminal block nahi hota.

**Yeh services abhi kis kaam ke hain:**
- Postgres: saara real data (users, products, orders) yahan store hoga
- Redis: Day 2 mein stock count yahan rakhenge fast atomic decrement ke liye
- RabbitMQ: Day 5 ke aas-paas order processing async karne ke liye use hoga (abhi touch nahi kiya)

### `docker-compose.yml` — Line-by-Line Explanation

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: flashsale
      POSTGRES_PASSWORD: flashsale123
      POSTGRES_DB: flashsale_db
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3-management
    ports:
      - "5672:5672"
      - "15672:15672"

volumes:
  pgdata:
```

**`version: '3.8'`** — Docker Compose file format ka version bata raha hai, taaki Docker jaane kaunse features/syntax support karne hain.

**`services:`** — iske andar har ek container ki definition hai. Humare paas 3 services hain: `postgres`, `redis`, `rabbitmq` — inke naam khud humne rakhe hain, Docker inhi naamon se containers ko andar-andar identify karta hai.

**Postgres block:**
- `image: postgres:16` — Docker Hub se official Postgres ka version 16 image pull karo (pehli baar chalne pe download hoga, phir cached rehta hai)
- `environment:` — container start hote hi yeh variables uske andar set ho jate hain, Postgres inko use karke khud database + user bana leta hai pehli baar:
  - `POSTGRES_USER: flashsale` — ek naya DB user banega isi naam ka
  - `POSTGRES_PASSWORD: flashsale123` — us user ka password
  - `POSTGRES_DB: flashsale_db` — ek database khud-ba-khud bana dega isi naam ka
- `ports: "5432:5432"` — format hai `"host_port:container_port"`. Matlab: tere laptop ka port 5432, container ke andar chal rahe Postgres ke port 5432 se connect hai. Isi wajah se tu `localhost:5432` pe apne laptop se Postgres tak pahunch pata hai
- `volumes: pgdata:/var/lib/postgresql/data` — yeh sabse important line hai: Postgres apna data container ke andar `/var/lib/postgresql/data` folder mein rakhta hai. Agar container delete/restart ho jaye bina volume ke, **saara data gayab ho jayega**. `pgdata` naam ka ek volume (Docker ke apne storage mein, laptop pe persist hota hai) is folder se link kar diya — ab container restart/delete ho bhi jaye, data volume mein safe rehta hai

**Redis block:**
- `image: redis:7` — official Redis version 7
- `ports: "6379:6379"` — Redis ka default port, same logic jaisa Postgres mein
- Note: Redis ke liye humne `volumes` nahi diya — matlab agar container restart hua to Redis ka data (cache) khali ho jayega. Yeh intentional hai, kyunki Redis ko hum cache/temporary fast-storage ki tarah use kar rahe hain, permanent data ke liye nahi

**RabbitMQ block:**
- `image: rabbitmq:3-management` — RabbitMQ ka woh version jisme ek built-in web dashboard bhi aata hai (management UI)
- `ports: "5672:5672"` — yeh actual queue port hai, isi se Python code (`pika` library) RabbitMQ se baat karega
- `ports: "15672:15672"` — yeh management dashboard ka port hai, browser mein `http://localhost:15672` khol ke queues/messages visually dekh sakte hain (login: guest/guest, default)

**`volumes:` (bottom-level, file ke end mein):**
- Yahan hum `pgdata` naam ke volume ko "declare" kar rahe hain — Docker ko bata rahe hain ki yeh ek named volume hai jo humne upar Postgres service mein use kiya. Isse Docker khud is volume ko manage karta hai (kahin apne internal storage mein banata hai), tujhe uski exact location se matlab nahi rakhna padta

**Ek important cheez samajhna:** Teeno services ek hi `docker-compose.yml` mein hone ki wajah se yeh ek hi "network" mein aa jate hain — matlab agar aage chal ke humara Python app bhi Docker ke andar chalta (abhi nahi chal raha, abhi wo directly laptop pe chal raha hai), to woh `postgres`, `redis`, `rabbitmq` naamo se hi seedha connect kar leta, bina IP address dhoondhe. Abhi ke liye humara app laptop pe hai, so hum `localhost` use kar rahe hain `.env` mein.

---

## 3. `requirements.txt`

```
fastapi
uvicorn[standard]
sqlalchemy
alembic
psycopg2-binary
redis
pika
python-jose[cryptography]
passlib[bcrypt]
python-dotenv
pydantic
```

Har package ka kaam:

| Package | Kaam |
|---------|------|
| `fastapi` | Web framework — APIs banane ke liye |
| `uvicorn` | Server jo FastAPI app ko actually run karta hai |
| `sqlalchemy` | ORM — Python code se database tables ko manage karna (raw SQL likhne ki jagah) |
| `alembic` | Database migrations — schema changes ko track/apply karna |
| `psycopg2-binary` | PostgreSQL driver — SQLAlchemy isko use karke Postgres se baat karta hai |
| `redis` | Python se Redis ko connect/use karne ke liye |
| `pika` | Python se RabbitMQ ko connect/use karne ke liye |
| `python-jose` | JWT tokens banane/verify karne ke liye (auth) |
| `passlib` | Password hashing (bcrypt) — plain password kabhi store nahi karte |
| `python-dotenv` | `.env` file se environment variables load karne ke liye |
| `pydantic` | Data validation — API request/response ka shape define karna |

---

## 4. `.env` File

```
DATABASE_URL=postgresql://flashsale:flashsale123@localhost:5432/flashsale_db
REDIS_URL=redis://localhost:6379/0
RABBITMQ_URL=amqp://guest:guest@localhost:5672/
SECRET_KEY=change-this-to-something-random
```

**Kya hua:** Saari sensitive/environment-specific settings (DB password, secret keys) ek alag file mein rakhi, code ke andar hardcode nahi ki.

**Kyun zaroori hai:**
- Agar yeh values seedhe code mein likhi hoti aur code GitHub pe push hota, to password/secrets public ho jaate
- `.env` file ko `.gitignore` mein daal denge (abhi nahi kiya — yeh important hai, jald karna) taaki yeh Git mein kabhi commit na ho
- Alag environments (local machine, production server) mein alag `.env` use kar sakte hain, code same rehta hai

**Important reminder:** `.gitignore` file banake usmein `.env` aur `venv/` add karna abhi baaki hai — yeh next step mein karenge.

---

## 5. Folder Structure

```
flash-engine/
├── venv/                  (isolated Python env — Git mein nahi jayega)
├── app/
│   ├── __init__.py        (batata hai Python ko "app" ek package hai)
│   ├── main.py             (FastAPI app yahan se start hota hai)
│   ├── models.py           (DB tables yahan define honge — abhi khali hai)
│   ├── database.py         (DB connection setup)
│   ├── config.py           (abhi khali — settings ke liye reserved)
│   └── routers/
│       ├── __init__.py
│       ├── auth.py         (login/signup APIs — abhi khali)
│       ├── products.py     (product APIs — abhi khali)
│       └── flash_sales.py  (flash sale APIs — abhi khali)
├── docker-compose.yml
├── requirements.txt
└── .env
```

**Kyun aise structure kiya, sab kuch ek hi file mein nahi:**
- Chhote projects mein sab ek `main.py` mein daal sakte hain, but jaise-jaise project badhta hai (auth, products, orders, payments) — ek hi file 1000+ lines ki ho jati hai, dhoondhna mushkil
- `routers/` folder se har feature (auth, products, flash sales) apni alag file mein rehta hai — code organize rehta hai, team mein kaam karna aasan hota hai
- Yeh industry-standard FastAPI project structure hai

---

## 6. `app/database.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Line-by-line kya ho raha hai:**
- `load_dotenv()` — `.env` file ko read karke uski values ko environment variables bana deta hai
- `DATABASE_URL = os.getenv(...)` — `.env` se DB connection string uthata hai
- `engine = create_engine(...)` — yeh "connection factory" hai, DB se actual baatcheet yahi karta hai
- `SessionLocal` — har API request ke liye ek naya "session" (temporary conversation with DB) banane ka tarika
- `Base` — yeh woh cheez hai jisse hum aage `models.py` mein tables define karenge (har table `Base` ko inherit karega)
- `get_db()` — yeh function har API call ke start mein ek DB session deta hai, aur request khatam hone pe usse close kar deta hai (connection leak na ho)

**Yeh abhi kaam nahi kar raha kyun:** Kyunki `models.py` khali hai — koi table define nahi hui, so DB se baat karne layak kuch hai hi nahi abhi. Yeh next step hai.

---

## 7. `app/main.py`

```python
from fastapi import FastAPI

app = FastAPI(title="Flash Sale Engine")

@app.get("/health")
def health():
    return {"status": "ok"}
```

**Kya hua:**
- `FastAPI()` — ek app instance banaya, yeh poore project ka "entry point" hai
- `/health` endpoint — ek simple check API, isse pata chalta hai server zinda hai ya nahi (production systems mein bhi yeh pattern hota hai — monitoring tools isko baar-baar hit karke check karte hain server up hai)

**`uvicorn app.main:app --reload` command ka matlab:**
- `app.main` — `app` folder ke andar `main.py` file
- `:app` — us file ke andar jo `app = FastAPI(...)` variable hai, wahi run karo
- `--reload` — jab bhi code change kare, server khud restart ho jaye (development mein useful, production mein nahi use karte)

**`/docs` kya hai:** FastAPI khud-ba-khud ek interactive API documentation page bana deta hai (`http://localhost:8000/docs`) jahan se tu directly browser mein APIs test kar sakta hai bina Postman khole.

---

## Troubleshooting Note — Port Conflict (Naya Laptop Pe Aaya Tha)

**Symptom:** `alembic revision --autogenerate` chalane pe baar-baar yeh error aaya:
```
psycopg2.OperationalError: ... FATAL: password authentication failed for user "flashsale"
```
Jabki `.env` file, `docker-compose.yml` credentials, sab match kar rahe the.

**Asli wajah:** Us laptop pe already ek **native PostgreSQL Windows Service** installed tha (kisi purane setup se), jo already port `5432` pe sun raha tha. Jab humara Docker wala Postgres bhi `5432:5432` pe map hua, to `localhost:5432` pe jo bhi request jaati thi, woh galti se **native Postgres** tak pahunch jaati thi — jiska password kuch aur tha, Docker wale se match nahi karta tha. Isiliye error "password authentication failed" aata raha, jabki asli Docker container bilkul theek tha.

**Kaise pakda:**
```bash
docker exec -it flash-engine-postgres-1 psql -U flashsale -d flashsale_db -c "SELECT 1;"
```
Yeh Docker network ke andar se seedha connect karta hai (port mapping bypass karke) — yeh **success** hua, isse confirm hua Docker container theek hai, problem bahar (port level) pe hai.

```bash
netstat -ano | grep 5432
tasklist | grep -i postgres
```
Inse dikha ki `postgres.exe` "Services" ke andar already chal raha tha — matlab native install hai.

**Fix:** `docker-compose.yml` mein Postgres ka host port badal diya `5432` se `5433`:
```yaml
ports:
  - "5433:5432"
```
Aur `.env` mein bhi `DATABASE_URL` ka port `5433` kar diya. Container ke andar wala port `5432` hi rakha (usse touch nahi karna padta).

**Seekh:** Agar kisi naye machine pe yeh setup dobara kare aur same "password authentication failed" error aaye jabki credentials sahi lag rahe hon, sabse pehle yeh check karo:
```bash
netstat -ano | grep 5432
tasklist | grep -i postgres
```
Agar koi native Postgres already us port pe hai, seedha Docker ka host port kisi aur (5433, 5434, etc.) pe map kar do — native service ko chhedne ki zaroorat nahi.

---

## Abhi Tak Ka Status

- Infrastructure (Postgres, Redis, RabbitMQ) chal raha hai Docker mein (Postgres host port `5433` pe, native Postgres clash ki wajah se)
- Python environment isolated hai, saare packages installed hain
- Basic FastAPI app chal raha hai, health check kaam kar raha hai
- Folder structure ready hai aage ke features ke liye
- `.gitignore` ban chuka hai (`venv/`, `.env`, etc. Git se bahar)
- `models.py` mein 4 tables define ki (User, Product, FlashSale, Order)
- Alembic set up ho chuka hai (`.env` se DATABASE_URL leta hai), migration generate + apply ho chuki hai
- Database mein saari 4 tables ban chuki hain (`users`, `products`, `flash_sales`, `orders`) — verify kiya `\dt` se

## Abhi Tak Kya Nahi Kiya (Next Steps)

- Koi real API endpoint nahi bana abhi (auth/products/flash_sales router files khali hain)
- Auth (JWT) logic likhna baaki hai
- Concurrency-safe booking logic (Day 2 ka core kaam) abhi shuru nahi hua

**Next kaam:** Auth system (register/login/JWT) aur basic Product/FlashSale CRUD APIs likhna.