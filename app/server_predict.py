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
def predict_nth_future(model, recent_data, months=1, device="cpu"):
    """
    현재 입력 데이터(recent_data)를 기준으로, months개월 후까지 반복 예측.
    """
    model.eval()
    model.to(device)

    input_seq = recent_data.clone().detach().to(device)  # (window_size, feature_dim)
    preds = []

    with torch.no_grad():
        for _ in range(months):
            inp = input_seq.unsqueeze(0)  # (1, window_size, feature_dim)
            out = model(inp)              # (1, 1, output_size)
            pred = out[:, 0, :]           # (1, output_size)
            preds.append(pred.cpu().numpy().squeeze())

            # 다음 입력 시퀀스 업데이트 (슬라이딩 윈도우 방식)
            new_input = pred  # (1, output_size)
            new_input_expanded = torch.zeros((1, input_seq.shape[1])).to(device)
            new_input_expanded[:, :pred.shape[1]] = new_input  # 부족한 feature는 zero padding
            input_seq = torch.cat([input_seq[1:], new_input_expanded], dim=0)  # shift window

    return np.array(preds[-1])  # 최종 months 번째 결과만 반환