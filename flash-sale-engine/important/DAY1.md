# Day 1 — Tables Kaise Banayi, Poora Samjhao

Yeh document batata hai `models.py` mein humne kya likha tha, aur woh actual database tables kaise ban gayi.

---

## Sabse Pehle — Basic Samajh

Tera database (PostgreSQL) ek bada Excel sheet jaisa system hai — jisme **tables** hote hain (jaise Excel ki sheets), aur har table mein **rows** (records) aur **columns** (fields) hote hain.

Humein normally SQL likhna padta — jaise:
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255)
);
```

Lekin humne yeh raw SQL nahi likha — humne **Python classes** likhi, aur ek tool (SQLAlchemy) ne unko khud SQL mein convert kar diya. Isi tarike ko **ORM** kehte hain.

---

## ORM Kya Hota Hai (Simple Words Mein)

**ORM = Object-Relational Mapping**

Matlab: Python ki cheezein (classes, objects) ↔ Database ki cheezein (tables, rows) — dono ko aapas mein "map" (jodna) karna.

**Kyun use karte hain, seedha SQL kyun nahi likhte:**
- Python code likhna aasan hai, SQL syntax har baar yaad nahi rakhna padta
- Agar kal Postgres se MySQL pe switch karna pade, code zyada change nahi karna padta
- Type-checking milti hai (Python khud bata deta hai agar galat data type daala)
- Relationships (jaise "yeh order kis user ka hai") likhna aasan ho jata hai

---

## Ab `models.py` Ko Line-by-Line Samajhte Hain

### Table 1: `User`

```python
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
```

**Kya ho raha hai:**
- `class User(Base):` — yeh keh raha hai "User naam ki ek cheez bana rahe hain, jo `Base` se properties leti hai" (`Base` woh cheez hai jo humne `database.py` mein banayi thi — yeh SQLAlchemy ko batati hai "yeh ek table hai")
- `__tablename__ = "users"` — database mein is table ka asli naam `users` hoga (Python class ka naam `User` hai, but DB table ka naam `users` — convention hai plural/lowercase)
- `id = Column(Integer, primary_key=True, index=True)`:
  - `Column(Integer, ...)` — yeh ek column hai jisme number store hoga
  - `primary_key=True` — yeh column har row ko **uniquely identify** karega (do rows ka same `id` kabhi nahi ho sakta, aur yeh automatically 1, 2, 3... badhta jayega)
  - `index=True` — database ko batate hain "is column pe searches fast honi chahiye" (jaise kitab ke index se topic dhoondhna fast hota hai)
- `email = Column(String(255), unique=True, nullable=False)`:
  - `String(255)` — text store hoga, max 255 characters
  - `unique=True` — do users ka email same nahi ho sakta
  - `nullable=False` — yeh field **khali nahi chhod sakte**, dena hi padega
- `password_hash` — password **direct nahi**, uska **hash** (encrypted version) store hota hai. Kabhi bhi real password DB mein save nahi karte, security ke liye
- `created_at = Column(TIMESTAMP, server_default=func.now())` — jab bhi naya row bane, database khud current time daal dega (humein manually dena nahi padega)

**Real-life analogy:** Yeh table basically ek "Users ki diary" hai — har user ka ek page (row), jisme uski ID, email, password (locked/hashed), aur kab account bana (created_at) likha hai.

---

### Table 2: `Product`

```python
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    total_stock = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
```

**Naya cheez yahan:** `Numeric(10, 2)` — yeh price ke liye hai. Iska matlab: total 10 digits ho sakte hain, jinme se 2 decimal ke baad (jaise `99999999.99`). Hum `Float` use nahi karte paison ke liye kyunki Float mein rounding errors aa sakte hain (jaise `0.1 + 0.2` kabhi kabhi `0.30000000004` ban jata hai computers mein) — paison ke calculations mein yeh galti nahi chal sakti.

**Yeh table kya represent karti hai:** Har product jo tu bech raha hai (jaise "Concert Ticket") — uska naam, price, aur total kitna stock available hai.

---

### Table 3: `FlashSale`

```python
class FlashSale(Base):
    __tablename__ = "flash_sales"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    start_time = Column(TIMESTAMP, nullable=False)
    end_time = Column(TIMESTAMP, nullable=False)
    max_per_user = Column(Integer, default=1)
    status = Column(String(20), default="scheduled")
    created_at = Column(TIMESTAMP, server_default=func.now())
```

**Sabse important naya concept: `ForeignKey`**

```python
product_id = Column(Integer, ForeignKey("products.id"))
```

Yeh line keh rahi hai: "`product_id` ek number hai, jo **`products` table ke `id` column** se link hai."

**Kyun zaroori hai:** Isse database ko pata chalta hai "yeh flash sale **kis product ke liye hai**." Bina iske, hum sirf ek random number store karte, database ko pata hi nahi chalta woh kis cheez ko refer kar raha hai. `ForeignKey` ek **relationship** banata hai do tables ke beech — jaise ek dhaaga jo `flash_sales` table ko `products` table se jodta hai.

**Real-life analogy:** Socho `products` table ek "master list" hai saare items ki. `flash_sales` table mein har row bolti hai "main is master list ke item number X ke liye ek sale hoon" — `product_id` woh reference hai.

**`default=1` aur `default="scheduled"` ka matlab:** Agar tu value nahi deta banate waqt, khud-ba-khud yeh default value lag jayegi.

---

### Table 4: `Order`

```python
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    flash_sale_id = Column(Integer, ForeignKey("flash_sales.id"))
    quantity = Column(Integer, default=1)
    status = Column(String(20), default="pending")
    idempotency_key = Column(String(255), unique=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
```

**Do ForeignKeys hain yahan:**
- `user_id` → `users.id` — batata hai yeh order **kis user ne** kiya
- `flash_sale_id` → `flash_sales.id` — batata hai yeh order **kis flash sale ke liye** hai

**`idempotency_key`:** Yeh ek unique random string hoga jo har order request ke saath aayega. Isse hum duplicate orders rok sakte hain (agar user do baar "Buy" button dabaye galti se, same key se dusra order reject ho jayega) — yeh Week 2 mein use hoga actual mein.

**Real-life analogy:** Yeh table "Receipt Book" jaisi hai — har order ek receipt hai, jisme likha hai kaunsa user (user_id), kaunsi sale (flash_sale_id), kitni quantity, aur order ka status (pending/confirmed/failed).

---

## Yeh Sab Likhne Ke Baad Kya Hua — Alembic Ka Kaam

Sirf Python classes likhne se database mein tables **nahi ban jati** — yeh sirf "definition" hoti hai, jaise blueprint. Actual tables banane ke liye humne **Alembic** use kiya.

### Command 1: Migration File Generate Karna

```bash
alembic revision --autogenerate -m "create initial tables"
```

**Kya hua yahan:** Alembic ne `models.py` ki saari classes padhi (`User`, `Product`, `FlashSale`, `Order`), aur automatically ek **migration file** ban gayi (`alembic/versions/7eb15e398194_create_initial_tables.py` jaisa naam) — is file ke andar actual SQL commands hain jo tables banayengi.

**"Migration" kya hota hai:** Yeh ek "history record" hota hai — batata hai database ko step-by-step kaise change karna hai. Har baar jab tu `models.py` mein kuch naya add karega (jaise ek naya column), tu ek nayi migration generate karega — isse database ka pura history track hota hai, kisi ko bhi pata chal sakta hai database kaise evolve hua time ke saath.

### Command 2: Migration Ko Actually Apply Karna

```bash
alembic upgrade head
```

**Kya hua yahan:** Yeh command woh migration file ko chalati hai — ab woh SQL commands actually Postgres database mein run hue, aur asli tables ban gayi.

**"head" ka matlab:** Yeh batata hai "latest wali migration tak le jao" — abhi humare paas ek hi migration hai, so yeh sidha wahi apply ho gayi.

### Verify Karna

```bash
docker exec -it flash-engine-postgres-1 psql -U flashsale -d flashsale_db -c "\dt"
```

Yeh command Postgres ke andar jaake poochti hai "saari tables dikhao" — aur humein 4 tables (`users`, `products`, `flash_sales`, `orders`) dikhi, plus ek `alembic_version` table jo Alembic khud banata hai yeh track karne ke liye ki konsi migration abhi tak apply hui hai.

---

## Poore Process Ka Flow (Recap)

```
1. Python mein classes likhi (models.py)
        ↓
2. Alembic ne classes padhi, ek migration file banayi
   (alembic revision --autogenerate)
        ↓
3. Migration file ko chalaya, database mein tables ban gayi
   (alembic upgrade head)
        ↓
4. Verify kiya ki tables sach mein ban gayi
   (\dt command)
```

**Simple analogy:** Socho tu ek architect hai. `models.py` tera **naksha/blueprint** hai (kagaz pe design). Alembic ka `--autogenerate` command woh naksha padhke ek **construction plan** banata hai (migration file). `upgrade head` command asal mein **building banwa deta hai** (database mein tables create karta hai).

---

## Abhi Tables Khali Hain

Important samajhna: humne sirf table ka **structure/shape** banaya hai — jaise ek khali Excel sheet jisme columns ke naam likhe hain but koi data nahi hai. Koi user, koi product, koi order — kuch bhi abhi database mein nahi hai. Woh Day 1 ke agle part mein hoga jab hum actual APIs banayenge (jaise "naya user banao" API) jo in tables mein data **insert** karengi.