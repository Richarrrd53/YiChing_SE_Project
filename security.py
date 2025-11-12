import bcrypt

def verify_pwd(plain_pwd: str, hashed_pwd: str) -> bool:
    hashed_pwd = hashed_pwd.strip()
    
    plain_pwd_bytes = plain_pwd.encode('utf-8')
    hashed_pwd_bytes = hashed_pwd.encode('utf-8')

    truncated_plain_pwd_bytes = plain_pwd_bytes[:72]

    try:
        return bcrypt.checkpw(truncated_plain_pwd_bytes, hashed_pwd_bytes)
    except Exception as e:
        return False

def get_pwd_hash(pwd: str) -> str:
    pwd_bytes = pwd.encode('utf-8')

    truncated_pwd_bytes = pwd_bytes[:72]

    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(truncated_pwd_bytes, salt)

    return hashed_bytes.decode('utf-8')