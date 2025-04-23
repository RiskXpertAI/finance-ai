import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from pymongo import MongoClient

from config import MONGO_URI


# LSTM 모델 정의
class TimeSeriesLSTMModel(nn.Module):
    def __init__(self, input_size, output_size, hidden_size=256, num_layers=2, dropout=0.2):
        super(TimeSeriesLSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out.unsqueeze(1)

# 학습 함수
def train_lstm(model, train_loader, valid_loader, epochs=300, lr=0.0008, device="cpu"):
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    model.to(device)

    for epoch in range(epochs):
        model.train()
        epoch_loss = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            out = model(x)
            pred = out[:, 0, :]
            loss = criterion(pred, y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()

        if (epoch + 1) % 10 == 0 or epoch == 0:
            print(f"[Epoch {epoch+1}/{epochs}] Train Loss: {epoch_loss / len(train_loader):.6f}")

    # 검증
    model.eval()
    preds, targets = [], []
    with torch.no_grad():
        for x, y in valid_loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            pred = out[:, 0, :]
            preds.append(pred.cpu().numpy())
            targets.append(y.cpu().numpy())

    preds = np.concatenate(preds, axis=0)
    targets = np.concatenate(targets, axis=0)

    # scaler를 복구하는 건 따로 제공하지 않으니까 그냥 MSE 비교
    mse = mean_squared_error(targets, preds)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(targets, preds)
    r2 = r2_score(targets, preds)

    print("\n[Validation 성능]")
    print(f"MSE: {mse:.4f}, RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")

# 메인 학습+저장
def main(window_size=6, horizon=1):
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
    num_cols = ["GDP", "환율", "생산자물가지수", "소비자물가지수", "금리"]
    df[num_cols] = df[num_cols].apply(pd.to_numeric, errors="coerce").ffill()

    for col in num_cols:
        df[f"{col}_MA3"] = df[col].rolling(window=3).mean()
        df[f"{col}_DIFF"] = df[col].diff()
        df[f"{col}_PCT"] = df[col].pct_change()
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df = df.ffill()
    df = df.bfill()

    input_cols = [
        "GDP", "환율", "생산자물가지수", "소비자물가지수", "금리",
        "GDP_MA3", "GDP_DIFF", "GDP_PCT",
        "환율_MA3", "환율_DIFF", "환율_PCT",
        "생산자물가지수_MA3", "생산자물가지수_DIFF", "생산자물가지수_PCT",
        "소비자물가지수_MA3", "소비자물가지수_DIFF", "소비자물가지수_PCT",
        "금리_MA3", "금리_DIFF", "금리_PCT"
    ]
    target_cols = ["GDP", "환율", "생산자물가지수", "소비자물가지수", "금리"]

    input_vals = df[input_cols].values
    target_vals = df[target_cols].values
    input_scaler = MinMaxScaler()
    target_scaler = MinMaxScaler()
    scaled_input = input_scaler.fit_transform(input_vals)
    scaled_target = target_scaler.fit_transform(target_vals)

    # 슬라이딩 윈도우
    X, Y = [], []
    for i in range(len(scaled_input) - window_size - horizon + 1):
        X.append(scaled_input[i:i+window_size])
        Y.append(scaled_target[i+window_size+horizon-1])
    X = np.array(X)
    Y = np.array(Y)

    # 8:2 분리
    split_idx = int(len(X) * 0.8)
    X_train, X_val = X[:split_idx], X[split_idx:]
    Y_train, Y_val = Y[:split_idx], Y[split_idx:]

    train_dataset = torch.utils.data.TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(Y_train, dtype=torch.float32)
    )
    valid_dataset = torch.utils.data.TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(Y_val, dtype=torch.float32)
    )

    train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
    valid_loader = DataLoader(valid_dataset, batch_size=32, shuffle=False)

    # 모델 정의
    model = TimeSeriesLSTMModel(
        input_size=len(input_cols),
        output_size=len(target_cols),
        hidden_size=256,
        num_layers=2,
        dropout=0.2
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # 학습
    train_lstm(model, train_loader, valid_loader, epochs=300, lr=0.0005, device=device)

    # 모델 저장
    torch.save(model.state_dict(), "lstm_model.pt")
    print("\n모델이 lstm_model.pt 파일로 저장되었습니다!")

if __name__ == "__main__":
    main()