import numpy as np
import torch
import torch.nn as nn
import pandas as pd
from fastapi import FastAPI, Form
from fastapi.responses import JSONResponse
from sklearn.preprocessing import MinMaxScaler
from pymongo import MongoClient
from app.config import MONGO_URI

# FastAPI 앱 생성
app = FastAPI()

# 모델 클래스
class TimeSeriesLSTMModel(nn.Module):
    def __init__(self, input_size, output_size, hidden_size=256, num_layers=2, dropout=0.2):
        super(TimeSeriesLSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out.unsqueeze(1)

# 최근 데이터 로딩 함수
def load_recent_data(feature_cols, target_cols, window_size):
    try:
        client = MongoClient(MONGO_URI)
        db = client["financeai"]
        collection = db["financial_data"]
        cursor = collection.find({}, {
            "_id": 0,
            "TIME": 1,
            "GDP": 1,
            "환율": 1,
            "생산자물가지수": 1,
            "소비자물가지수": 1,
            "금리": 1
        })
        mongo_data = list(cursor)
        df = pd.DataFrame(mongo_data)
        if df.empty:
            raise ValueError("MongoDB에 데이터가 없습니다.")
    except Exception as e:
        raise RuntimeError(f"MongoDB 연결 실패: {e}")

    df = df.sort_values("TIME").reset_index(drop=True)

    # 숫자형 변환
    num_cols = ["GDP", "환율", "생산자물가지수", "소비자물가지수", "금리"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce")

    # Feature Engineering
    for col in num_cols:
        df[f"{col}_MA3"] = df[col].rolling(window=3).mean()
        df[f"{col}_DIFF"] = df[col].diff()
        df[f"{col}_PCT"] = df[col].pct_change()

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.ffill()
    df = df.bfill()
    df = df.dropna(subset=feature_cols)

    # 핵심: input feature 따로, target 따로 스케일링
    feature_vals = df[feature_cols].values
    target_vals = df[target_cols].values

    feature_scaler = MinMaxScaler().fit(feature_vals)
    target_scaler = MinMaxScaler().fit(target_vals)

    scaled_input = feature_scaler.transform(feature_vals)
    sequence_data = torch.tensor(scaled_input, dtype=torch.float32)

    recent_input = sequence_data[-window_size:]
    last_time = df["TIME"].iloc[-1]

    return recent_input, target_scaler, last_time

# 예측 함수
def predict_nth_future(model, recent_data, device="cpu"):
    model.eval()
    model.to(device)
    with torch.no_grad():
        inp = recent_data.unsqueeze(0).to(device)
        out = model(inp)
        pred = out[:, 0, :]
    return pred.squeeze(0).cpu().numpy()