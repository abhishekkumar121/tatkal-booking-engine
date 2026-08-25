# Date/time helpers token expiry calculate karne ke liye.
from datetime import datetime, timedelta

# Password hashing context import kar rahe hain.
from passlib.context import CryptContext

# JWT encode/decode ke liye jose library ka jwt helper.
from jose import jwt

# Auth settings config file se import kar rahe hain.
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

# FastAPI dependency aur HTTP error helpers.
from fastapi import Depends, HTTPException

# Bearer token security classes import kar rahe hain.
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# JWT helper aur JWTError import; JWTError invalid/expired token par aata hai.
from jose import jwt, JWTError

# SQLAlchemy Session type hint ke liye.
from sqlalchemy.orm import Session

# DB session dependency import kar rahe hain.
from app.database import get_db

# User model import kar rahe hain taaki DB se user fetch kar sakein.
from app.models import User

# HTTP Bearer scheme setup; Authorization: Bearer <token> header expect karega.
security = HTTPBearer()

# Password hashing setup; bcrypt secure password hash algorithm hai.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Plain password ko hashed string mein convert karta hai.
def hash_password(password: str) -> str:
    # passlib ka hash method password ko one-way hash bana deta hai.
    return pwd_context.hash(password)

# Plain password aur stored hash ko compare karta hai.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    # True return hoga agar password correct hai, warna False.
    return pwd_context.verify(plain_password, hashed_password)

# JWT access token banane wala helper function.
def create_access_token(data: dict) -> str:
    # Original data ka copy banate hain taaki input dictionary mutate na ho.
    to_encode = data.copy()
    # Current UTC time se expiry time calculate karte hain.
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    # JWT payload mein exp claim add karte hain, jisse token expire ho sake.
    to_encode.update({"exp": expire})
    # Payload ko SECRET_KEY se sign karke JWT token string return karte hain.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Protected routes ke liye current logged-in user fetch karta hai.
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    # Authorization header se actual token string nikaal rahe hain.
    token = credentials.credentials
    # Common 401 error object bana rahe hain jo invalid token/user par throw hoga.
    credentials_exception = HTTPException(
        # HTTP status 401 ka matlab unauthorized.
        status_code=401,
        # Error message client ko dikhane ke liye.
        detail="Could not validate credentials",
        # Browser/client ko batata hai ki Bearer auth required hai.
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Token decode karne ki koshish karenge.
    try:
        # SECRET_KEY aur algorithm se token verify/decode hota hai.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # JWT payload ke sub field se user id nikaalte hain.
        user_id: str = payload.get("sub")
        # Agar token mein user id nahi hai to token invalid maana jayega.
        if user_id is None:
            # Invalid credentials error throw karte hain.
            raise credentials_exception
    # JWT decode fail ho gaya, expire ho gaya, ya tampered hai to yahan aayega.
    except JWTError:
        # Invalid token ke case mein 401 error throw karte hain.
        raise credentials_exception

    # Token valid hai, ab DB mein user id se actual user dhoondhte hain.
    user = db.query(User).filter(User.id == int(user_id)).first()
    # Agar DB mein user nahi mila to token ko invalid maana jayega.
    if user is None:
        # Invalid credentials error throw karte hain.
        raise credentials_exception
    # Valid user object route ko return karte hain.
    return user
