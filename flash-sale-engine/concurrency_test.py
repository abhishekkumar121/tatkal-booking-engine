import httpx
import asyncio
import uuid

BASE_URL = "http://localhost:8000"
TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwiZXhwIjoxNzg1NjcwNTMzfQ.CU-gxiU8ns8HWhYJmKj6EE_JFX7vEsdDyYEMTq227uc" 
FLASH_SALE_ID = 6

HEADERS = {"Authorization": f"Bearer {TOKEN}"}

NUM_REQUESTS = 50  


async def place_order(client, i):
    payload = {
        "flash_sale_id": FLASH_SALE_ID,
        "quantity": 1,
        "idempotency_key": str(uuid.uuid4())  
    }
    try:
        response = await client.post(f"{BASE_URL}/orders/", json=payload, headers=HEADERS)
        return response.status_code, response.json()
    except Exception as e:
        return "ERROR", str(e)


async def main():
    async with httpx.AsyncClient() as client:
        tasks = [place_order(client, i) for i in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)

    success_count = sum(1 for status, _ in results if status == 200)
    fail_count = sum(1 for status, _ in results if status != 200)

    print(f"\nTotal Requests: {NUM_REQUESTS}")
    print(f"Successful Orders: {success_count}")
    print(f"Failed/Rejected: {fail_count}")


if __name__ == "__main__":
    asyncio.run(main())