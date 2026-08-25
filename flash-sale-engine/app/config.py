# Environment variables read karne ke liye Python ka os module.
import os

# .env file load karne ke liye helper import.
from dotenv import load_dotenv

# .env file ki values ko environment variables mein load karta hai.
load_dotenv()

# JWT token sign/verify karne ke liye secret key .env se uthate hain.
SECRET_KEY = os.getenv("SECRET_KEY")

# JWT signing algorithm; HS256 common symmetric signing algorithm hai.
ALGORITHM = "HS256"

# Access token kitne minutes tak valid rahega.
ACCESS_TOKEN_EXPIRE_MINUTES = 120
