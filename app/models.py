from pydantic import BaseModel

# 요청으로 받을 텍스트의 prompt 정의
class TextRequest(BaseModel):
    prompt: str

class ChatRequest(BaseModel):
    prompt: str
    months: int