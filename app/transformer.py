import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from pymongo import MongoClient
from app.config import MONGO_URI
import httpx
from transformers import PreTrainedModel, PretrainedConfig

from fastapi import FastAPI,HTTPException
from app.services import get_openai_response, save_generated_text, build_forecast_prompt
from pydantic import BaseModel

# -----------------------------
# 1. Dataset: 가변 window 및 horizon
# -----------------------------
class TimeSeriesHorizonDataset(Dataset):
    """
    - data_tensor: (N, num_features)
    - window_size: 과거 몇 개월 데이터를 입력으로 사용할지
    - horizon: 예) 5면, window_size 이후의 (5개월 후) 단일 시점 예측
    """
    def __init__(self, data_tensor, window_size=12, horizon=5):
        self.data = data_tensor
        self.window_size = window_size
        self.horizon = horizon

    def __len__(self):
        return len(self.data) - self.window_size - (self.horizon - 1)

    def __getitem__(self, idx):
        x = self.data[idx : idx + self.window_size]
        y = self.data[idx + self.window_size + (self.horizon - 1)]
        return x, y

# -----------------------------
# 2. Hugging Face 스타일의 시계열 Transformer 모델 구성
# -----------------------------
class TimeSeriesTransformerConfig(PretrainedConfig):
    model_type = "time-series-transformer"
    def __init__(
        self,
        feature_size=5,
        d_model=64,
        nhead=4,
        num_layers=2,
        dim_feedforward=128,
        dropout=0.1,
        max_seq_len=5000,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.feature_size = feature_size
        self.d_model = d_model
        self.nhead = nhead
        self.num_layers = num_layers
        self.dim_feedforward = dim_feedforward
        self.dropout = dropout
        self.max_seq_len = max_seq_len

class TimeSeriesTransformerModel(PreTrainedModel):
    config_class = TimeSeriesTransformerConfig
    base_model_prefix = "time_series_transformer"
    def __init__(self, config: TimeSeriesTransformerConfig):
        super().__init__(config)
        # 입력 선형 변환: feature_size -> d_model
        self.input_fc = nn.Linear(config.feature_size, config.d_model)
        # 학습형 위치 임베딩
        self.pos_embedding = nn.Embedding(config.max_seq_len, config.d_model)
        # Transformer Encoder 구성
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            batch_first=True
        )
        self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=config.num_layers)
        # 출력 선형 변환: d_model -> feature_size
        self.output_fc = nn.Linear(config.d_model, config.feature_size)
        self.init_weights()

    def forward(self, x):
        """
        x: (batch, seq_len, feature_size)
        """
        batch_size, seq_len, _ = x.shape
        x_embed = self.input_fc(x)
        positions = torch.arange(0, seq_len, device=x.device).unsqueeze(0)  # (1, seq_len)
        x_embed = x_embed + self.pos_embedding(positions)
        encoded = self.encoder(x_embed)
        output = self.output_fc(encoded)
        return output

# -----------------------------
# 3. 학습 및 예측 함수
# -----------------------------
def train_transformer(model, dataloader, epochs=10, lr=1e-3, device="cpu"):
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    model.train()
    model.to(device)
    for epoch in range(epochs):
        epoch_loss = 0.0
        for x, y in dataloader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)  # (batch, seq_len, feature_size)
            pred = out[:, -1, :]  # 마지막 타임스텝을 예측값으로 사용
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
        print(f"[Epoch {epoch+1}/{epochs}] Loss = {epoch_loss / len(dataloader):.6f}")

def predict_nth_future(model, recent_data, device="cpu"):
    """
    recent_data: (window_size, feature_size)
    모델의 출력 마지막 타임스텝을 반환
    """
    model.eval()
    model.to(device)
    with torch.no_grad():
        inp = recent_data.unsqueeze(0).to(device)  # (1, window_size, feature_size)
        out = model(inp)
        pred = out[:, -1, :]  # (1, feature_size)
    return pred.squeeze(0).cpu().numpy()

def run_forecasting(window_size=12, forecast_horizon=5):
    """
    - MongoDB에서 데이터를 로드하여 전처리한 후,
    - 입력 window와 horizon에 맞춰 Dataset을 생성,
    - Hugging Face 스타일의 시계열 Transformer를 학습 및 예측하여 결과를 dict로 반환.
    
    ※ DB, 컬렉션, 필드명 등은 실제 사용 환경에 맞게 수정 필요.
    """
    # (A) MongoDB 데이터 로드
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
            raise ValueError("MongoDB 컬렉션에 데이터가 없습니다.")
    except Exception as e:
        raise RuntimeError(f"MongoDB 연결/조회 실패: {e}")

    # (B) 정렬 및 스케일링
    df = df.sort_values("TIME").reset_index(drop=True)
    feature_cols = ["GDP", "환율", "생산자물가지수", "소비자물가지수", "금리"]
    data_vals = df[feature_cols].values
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(data_vals)
    sequence_data = torch.tensor(scaled_data, dtype=torch.float32)

    # (C) Dataset / DataLoader 생성
    ts_dataset = TimeSeriesHorizonDataset(sequence_data, window_size, forecast_horizon)
    ts_dataloader = DataLoader(ts_dataset, batch_size=16, shuffle=True)

    # (D) 모델 정의 및 학습
    config = TimeSeriesTransformerConfig(
        feature_size=len(feature_cols),
        d_model=64,
        nhead=4,
        num_layers=2,
        dim_feedforward=128,
        dropout=0.1,
        max_seq_len=5000
    )
    model = TimeSeriesTransformerModel(config)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_transformer(model, ts_dataloader, epochs=10, lr=1e-3, device=device)

    # (E) 최근 window_size 데이터를 이용해 forecast_horizon개월 후 예측
    recent_input = sequence_data[-window_size:]  # (window_size, num_features)
    pred_scaled = predict_nth_future(model, recent_input, device=device)
    pred_scaled_2d = pred_scaled.reshape(1, -1)
    pred_real = scaler.inverse_transform(pred_scaled_2d).flatten()

    # (F) 마지막 TIME에서 forecast_horizon개월 후의 날짜 계산 (YYYYMM 형태)
    last_time_str = str(df["TIME"].iloc[-1])
    base_year = int(last_time_str[:4])
    base_mon = int(last_time_str[4:])
    target_mon = base_mon + forecast_horizon
    target_year = base_year
    while target_mon > 12:
        target_mon -= 12
        target_year += 1
    future_time = f"{target_year}{target_mon:02d}"

    result = {**dict(zip(feature_cols, map(float, pred_real))), "TIME": future_time}
    return result

# -----------------------------
# 4. FastAPI 엔드포인트 정의 (예시 실행 부분 제거)
# -----------------------------
app = FastAPI()




# 1. Pydantic 모델을 정의하여 JSON 데이터 받기
from openai import OpenAI
from app.config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)
class ChatRequest(BaseModel):
    prompt: str
    months: int

