# Day 2 — Race Condition Demo + Redis Atomic Fix (Explained)

Yeh document batata hai humne race condition kaise **create** ki, kaise **prove** ki, aur kaise **Redis se fix** ki. Yeh tera project ka sabse important technical piece hai — interview mein isi ko sabse zyada discuss kiya jayega.

---

## Sabse Pehle — "Race Condition" Kya Hoti Hai (Simple Words Mein)

Jab **do ya zyada requests ek hi cheez ko ek hi samay pe change** karne ki koshish karti hain, aur unke beech koi coordination nahi hoti, to unexpected/galat result aa sakta hai. Isko **race condition** kehte hain — kyunki requests ek "race" mein hain, aur jo bhi pehle/last finish kare uske hisaab se result badal sakta hai (jo galat hai — result **consistent** hona chahiye, chahe requests kitni bhi ho ya kis order mein aayein).

**Real-life analogy:** Socho ek movie ka sirf 1 ticket bacha hai counter pe. Do log ek saath counter pe aakar poochte hain "ticket hai kya?" — dono ko "haan hai" sunayi deta hai (kyunki abhi tak koi bika nahi), dono paise de dete hain, lekin ticket sirf ek hi hai. Yeh hi race condition hai — **check karne** aur **book karne** ke beech ka gap problem create karta hai.

---

## Part 1: Unsafe Version — Jaan-Boojh Ke Buggy Code Likha

Humne `orders.py` mein pehle yeh likha tha:

```python
if product.total_stock < order.quantity:
    raise HTTPException(status_code=400, detail="Out of stock")

product.total_stock -= order.quantity
```

**Yeh 2 steps hain:**
1. **Check karo** — stock kaafi hai kya?
2. **Update karo** — stock kam karo

Dikhne mein normal lagta hai, lekin problem yeh hai: in do steps ke **beech ek chhota sa time gap** hota hai. Agar 50 requests **exact same milisecond** mein aayein, sabhi Step 1 pe pahunch jaati hain **stock update hone se pehle** — sabko dikhta hai "haan stock available hai," aur sab apna order confirm kar leti hain.

---

## Part 2: Race Condition Ko Proof Ke Saath Dikhaya

### Test Setup

Humne ek Python script (`concurrency_test.py`) banaya jo `httpx` (async HTTP library) use karke **50 requests ek saath (parallel)** bhejta hai `POST /orders/` endpoint pe — using `asyncio.gather()`.

```python
tasks = [place_order(client, i) for i in range(NUM_REQUESTS)]
results = await asyncio.gather(*tasks)
```

**`asyncio.gather()` kya karta hai:** Normal loop mein agar 50 requests bhejte, woh ek-ek karke jaati (sequential) — pehli poori hoke response aane ke baad hi dusri jaati. `asyncio.gather()` saari requests **ek saath fire** karta hai, bina ek dusre ka wait kiye — yehi asli "concurrent traffic" simulate karta hai jaisa real flash-sale mein hota hai.

### Result Jo Mila (Unsafe Version)

- Product ka stock tha: **5**
- 50 concurrent requests bheji
- **15 orders successful ho gaye!**
- Final DB stock: **0** (negative nahi, but phir bhi galat)

**Yeh kyun hua — "Lost Update Problem":**

Jab Python `product.total_stock -= order.quantity` karta hai, woh:
1. Pehle current value **memory mein padhta hai** (jaise `5`)
2. Us par calculation karta hai (`5 - 1 = 4`)
3. Naya poora value **wapas likhta hai** database mein

Agar 2 requests yeh **saath-saath** karein:
- Request A: stock `5` padha, `4` banaya, likhne wala hai
- Request B: (isi waqt) stock **abhi bhi `5` padha** (kyunki A ka likhna abhi register nahi hua), `4` banaya
- Dono ne apna `4` likha — lekin **do orders confirm ho gaye, stock sirf 1 hi kam hua** — ek update **"lost"** ho gaya

Yeh baar-baar hone se, 15 orders confirm ho gaye jabki stock sirf 5 tha — company ne aisi cheezein "bech" di jo unke paas thi hi nahi.

---

## Part 3: Redis Se Fix Kiya — Atomic Operations

### "Atomic" Ka Matlab Kya Hai

Ek operation **atomic** hoti hai jab woh **ek hi, bina-todi-ja-sakne-wali step** mein poori ho — beech mein koi doosri process aa hi nahi sakti. Jaise ek building block — ya to poora hoga, ya bilkul nahi hoga, lekin "aadha" nahi ho sakta.

**Humara problem tha:** "check + decrement" do alag steps the (na-atomic), jinke beech dusri requests ghus sakti thi.
**Fix:** Dono steps ko **ek hi atomic operation** mein convert kiya — Redis Lua script se.

### Redis Kyun, Database Kyun Nahi

Postgres mein bhi `SELECT FOR UPDATE` jaisa lock feature hota hai jo yeh fix kar sakta tha, lekin humne Redis use kiya kyunki:
1. Redis **single-threaded** hai internally — matlab ek waqt mein sirf **ek hi command** chalta hai, bilkul naturally koi race condition ho hi nahi sakti
2. Redis **bahut fast** hai (in-memory), high-traffic scenarios (jaise flash sale) mein perform karna zaroori hai
3. Redis **Lua scripts** ko atomically execute karta hai — poora script ek "single command" ki tarah treat hota hai

### Lua Script Ka Kaam

```lua
local current_stock = tonumber(redis.call('GET', KEYS[1]))
if current_stock == nil then
    return -2
end
if current_stock < tonumber(ARGV[1]) then
    return -1
end
redis.call('DECRBY', KEYS[1], ARGV[1])
return current_stock - tonumber(ARGV[1])
```

**Step by step:**
1. `KEYS[1]` — Redis mein woh key jahan stock stored hai (jaise `"stock:6"`)
2. `ARGV[1]` — kitni quantity order ki ja rahi hai
3. Current stock padhta hai
4. Agar key exist nahi karti → `-2` return (error signal: "stock initialize hi nahi hua")
5. Agar stock kam hai requested quantity se → `-1` return (error signal: "out of stock")
6. Warna, stock **kam karta hai** (`DECRBY`)
7. Naya stock return karta hai (success signal)

**Sabse important baat:** Yeh **poora script** Redis ke andar **ek hi atomic unit** ki tarah chalta hai. Jab tak yeh script ek request ke liye chal raha hai, koi doosri request beech mein aake stock nahi padh sakti — usse **wait** karna padega apni baari ka. Isi wajah se "check" aur "decrement" ke beech ka woh khतरnak gap **poori tarah khatam** ho gaya.

### Python Code Mein Kaise Use Kiya

```python
decrement_script = redis_client.register_script(DECREMENT_STOCK_SCRIPT)

result = decrement_script(keys=[stock_key], args=[order.quantity])

if result == -2:
    raise HTTPException(status_code=500, detail="Stock not initialized in Redis")
if result == -1:
    raise HTTPException(status_code=400, detail="Out of stock")

# Yahan tak pahunche, matlab Redis ne confirm kar diya stock available tha
# Ab hi DB mein order create karo
```

**`register_script(...)`:** Yeh Lua script ko Redis server mein "register" kar deta hai (ek baar), taaki har request pe poora script text bhejna na pade — bas ek chhota reference use hota hai, jo fast hai.

**Logic ka order important hai:** Pehle Redis se **permission** lete hain ("kya order allowed hai?"), aur **sirf tabhi** DB mein order record banate hain jab Redis "haan" kahe. Isse guarantee milti hai ki DB mein utni hi orders bane jitna stock tha.

---

## Part 4: Fix Ke Baad Ka Test — Proof Ki Fix Kaam Kar Raha Hai

Same setup: stock = 5, 50 concurrent requests.

| Metric | Before Fix | After Fix |
|---|---|---|
| Stock available | 5 | 5 |
| Concurrent requests | 50 | 50 |
| Successful orders | **15** ❌ | **5** ✅ |
| Rejected orders | 35 | 45 |
| Final stock | 0 | 0 |

**Yeh exactly wahi result hai jo hona chahiye tha:** Chahe kitni bhi requests ek saath aayein, sirf utni hi confirm hongi jitna stock available hai — na kam, na zyada. **Zero overselling.**

---

## Yeh Interview Mein Kaise Explain Karna Hai (Practice Kar Le)

Agar koi poochhe "concurrency kaise handle ki tumne booking system mein," yeh bol sakta hai:

> "Maine pehle jaan-boojh ke ek unsafe version banaya jisme check-then-decrement do alag steps the, aur concurrent load test se prove kiya ki isse overselling hoti hai — 5 stock hote hue 15 orders confirm ho gaye. Fir maine Redis ke Lua scripting use karke stock check aur decrement ko ek atomic operation mein convert kiya — Redis single-threaded hone ki wajah se yeh guarantee deta hai ki ek waqt mein sirf ek hi request stock modify kar sakti hai. Isके बाद same load test mein exactly 5 successful orders aayi, baaki sab cleanly 'out of stock' reject hui — zero overselling."

Yeh answer **specific numbers ke saath** hai (5 stock, 15 vs 5 orders) — yehi cheez isko generic answer se alag banati hai aur interviewer ko convince karti hai ki tune sach mein khud test karke dekha hai, sirf padha nahi hai.

---

## Part 5: DB-Redis Sync Bhi Fix Kiya

Jab humne pehli baar Redis wala fix lagaya, ek gap reh gaya tha: **Redis ka stock update ho raha tha, lekin Postgres ke `products.total_stock` column ko humne touch hi nahi kiya tha.** Matlab Redis mein stock `0` tha, lekin DB mein abhi bhi purani value (`5`) dikh rahi thi — dono jagah **out of sync**.

**Fix:**

```python
result = decrement_script(keys=[stock_key], args=[order.quantity])
# ... error checks ...

new_order = Order(...)
db.add(new_order)

# DB ke product stock ko bhi Redis ke saath sync karo
product = db.query(Product).filter(Product.id == flash_sale.product_id).first()
product.total_stock = result  # Lua script ne jo naya stock return kiya, wahi use karo

db.commit()
```

**Kyun yeh safe hai:** Pehle DB khud calculate karta tha (`product.total_stock -= quantity`) — isi calculation ne race condition create ki thi. Ab hum **Redis ke calculate kiye hue authoritative value** (`result`, jo Lua script ne return kiya) ko seedha DB mein **daal** rahe hain — koi naya calculation DB ke upar nahi ho raha, isliye race hone ka koi chance hi nahi bacha. Redis "decide" karta hai naya stock kya hai, DB sirf usse **record** karta hai.

**Test se confirm hua:** Naya product (stock=5), 50 concurrent requests, result:
- Redis stock: `0`
- DB `total_stock`: `0`
- Confirmed orders: `5`

Dono jagah ab perfectly sync hain.

---

## Abhi Baaki Kya Hai (Updated)

Redis mein stock sahi update ho raha hai, aur ab PostgreSQL ka `products.total_stock` bhi sync mein hai — is part ka core kaam complete hai.

**Next kaam (in order):**
1. **Idempotency** — abhi agar user (ya koi buggy client) same request 2 baar bheje (double-click), koi graceful handling nahi hai
2. **Auto-cancel unpaid orders** — cron/background job jo purane "pending" orders ko cancel kare aur stock wapas release kare
3. **k6 se proper load test** — Python script se aage badhke industry-standard tool se numbers nikalna