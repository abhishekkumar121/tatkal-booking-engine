# FastAPI router, dependency, aur HTTP error helpers import kar rahe hain.
from fastapi import APIRouter, Depends, HTTPException

# SQLAlchemy database session type hint.
from sqlalchemy.orm import Session

# DB session dependency import kar rahe hain.
from app.database import get_db

# User database model import kar rahe hain.
from app.models import User

# Request/response schemas import kar rahe hain.
from app.schemas import UserCreate, UserLogin, Token, VerifyEmailRequest

# Password hashing, verification, aur token creation helpers.
from app.auth_utils import hash_password, verify_password, create_access_token

# Current logged-in user dependency import kar rahe hain.
from app.auth_utils import get_current_user

import random

from app.email_utils import send_verification_email

# Auth router bana rahe hain; saare endpoints /auth prefix se start honge.
router = APIRouter(prefix="/auth", tags=["auth"])



# POST /auth/register endpoint define kar rahe hain.
@router.post("/register")
# Register function user input aur DB session leta hai.
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Same email wala user already DB mein hai ya nahi check karte hain.
    existing_user = db.query(User).filter(User.email == user.email).first()
    # Agar user mil gaya to duplicate registration rok dete hain.
    if existing_user:
        # Client ko 400 error bhejte hain because email already registered hai.
        raise HTTPException(status_code=400, detail="Email already registered")

    # 6-digit random verification code generate karte hain.
    code = str(random.randint(100000, 999999))

    # Naya User object banate hain jo DB mein insert hoga.
    new_user = User(
        # Request se email leke model mein set karte hain.
        email=user.email,
        # Plain password ko hash karke password_hash mein store karte hain.
        password_hash=hash_password(user.password),
        # Naya user abhi verified nahi hai.
        is_verified=False,
        # Generated code ko DB mein temporarily store karte hain.
        verification_code=code
    )
    # New user ko DB session mein add karte hain.
    db.add(new_user)
    # Transaction commit karke user ko database mein permanently save karte hain.
    db.commit()
    # DB se latest values reload karte hain, jaise generated id.
    db.refresh(new_user)

    # Real email bhejne ki koshish karte hain SMTP se.
    email_sent = send_verification_email(new_user.email, code)
    # Agar email bhejna fail ho jaye, terminal mein fallback code print karte hain.
    if not email_sent:
        print(f"[FALLBACK] Verification code for {new_user.email}: {code}")

    # Client ko created user ka safe data return karte hain; password/hash return nahi karte.
    return {"id": new_user.id, "email": new_user.email, "message": "Verification code sent"}


# POST /auth/verify-email endpoint define kar rahe hain.
@router.post("/verify-email")
# Verify function email + code leta hai aur user ko verified mark karta hai.
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    # Email ke basis par user dhoondhte hain.
    user = db.query(User).filter(User.email == payload.email).first()
    # User exist nahi karta to error.
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Already verified ho to seedha success bata dete hain.
    if user.is_verified:
        return {"message": "Already verified"}
    # Code match nahi karta to error.
    if user.verification_code != payload.code:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    # Code sahi hai — user ko verified mark karte hain aur code clear kar dete hain.
    user.is_verified = True
    user.verification_code = None
    db.commit()
    return {"message": "Email verified successfully"}


# POST /auth/login endpoint define kar rahe hain; response Token schema jaisa hoga.
@router.post("/login", response_model=Token)
# Login function credentials aur DB session leta hai.
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    # Email ke basis par user DB mein dhoondhte hain.
    db_user = db.query(User).filter(User.email == credentials.email).first()
    # Agar user nahi mila ya password galat hai to login fail.
    if not db_user or not verify_password(credentials.password, db_user.password_hash):
        # Unauthorized error return karte hain.
        raise HTTPException(status_code=401, detail="Invalid email or password")
    # Email verify nahi hui to login block karte hain.
    if not db_user.is_verified:
        raise HTTPException(status_code=403, detail="Please verify your email before logging in")

    # User id ko JWT subject mein daal kar access token banate hain.
    token = create_access_token(data={"sub": str(db_user.id)})
    # Client ko token return karte hain; future protected requests mein ye token use hoga.
    return {"access_token": token, "token_type": "bearer"}


# GET /auth/me endpoint; current logged-in user ki info return karta hai.
@router.get("/me")
# get_current_user dependency token validate karke user object deti hai.
def read_current_user(current_user: User = Depends(get_current_user)):
    # Logged-in user ka safe data return karte hain.
    return {"id": current_user.id, "email": current_user.email}