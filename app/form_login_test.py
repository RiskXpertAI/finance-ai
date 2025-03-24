# from fastapi import FastAPI, HTTPException, Header
# import jwt
# import datetime
#
# app = FastAPI()
# SECRET_KEY = "my_secret_key"
#
# # JWT 생성
# def create_jwt_tokn(dta: dict):
#     expiration = datetime.datetime.utcnow() + datetime.timedelta(minutes=30)
#     data["exp"] = expiration
#     return jwt.encode(dta, SECRET_KEY, algorithm='HS256')
#
# # JWT 검증
# def verify_jwt_token(token: str):
#     try:
#         return jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
#     except
#         raise HTTPException(status_code=401, detail="Token expired")
#
# @app.get("/token")
# def generate_token(username: str):
#     return {"token": create_jwt_tokn({"username": username})}
#
# @app.get("/protected")
# def read_protected_route(token: str = Header(None)):
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#     verify_jwt_token(token)
#     return {"message": "Protected"}