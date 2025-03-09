import requests
import pandas as pd
import numpy as np
from datetime import datetime
from app.database import financial_data_collection  # ✅ 금융 데이터 컬렉션 가져오기

API_KEY = "DU39KYMCPH849TZL4ELE"
BASE_URL = "https://ecos.bok.or.kr/api/StatisticSearch"

# ✅ 데이터 매핑 정보
code_list = {'722Y001': 'M', '901Y009': 'M', '200Y102': 'Q', '731Y004': 'M', '404Y014':'M'}
num_list = ['0101000','0','10111', '0000001/0000100','*AA']
num_map = { '722Y001': num_list[0], '901Y009': num_list[1], '200Y102': num_list[2], '731Y004': num_list[3], '404Y014': num_list[4] }

async def fetch_and_store_financial_data():
    start_year = 2000
    end_year = datetime.today().year
    data_list = []

    # ✅ API 요청하여 데이터 수집
    for year in range(start_year, end_year + 1):
        for code, freq in code_list.items():
            start_date = f"{year}01" if freq == 'M' else f"{year}Q1"
            end_date = f"{year}12" if freq == 'M' else f"{year}Q4"
            num = num_map[code]

            response = requests.get(f"{BASE_URL}/{API_KEY}/json/kr/1/100/{code}/{freq}/{start_date}/{end_date}/{num}")
            data = response.json()

            if "StatisticSearch" in data:
                data_list.extend(data['StatisticSearch']['row'])

    # ✅ 데이터프레임 변환
    df = pd.DataFrame(data_list)

    # ✅ 컬럼 정리
    df.loc[df.STAT_CODE == '404Y014', 'ITEM_NAME1'] = '총지수(생산자물가지수)'
    df.loc[df.STAT_CODE == '901Y009', 'ITEM_NAME1'] = '총지수(소비자물가지수)'
    df = df.drop(columns=['STAT_CODE', 'STAT_NAME', 'ITEM_CODE1', 'ITEM_CODE2', 'ITEM_NAME2',
                           'ITEM_CODE3', 'ITEM_NAME3', 'ITEM_CODE4', 'ITEM_NAME4', 'WGT'])

    df['TIME'] = df['TIME'].astype(str)

    # ✅ 분기 데이터 확장
    def quarter_to_months(q_string):
        """ 분기 데이터 -> 월별 데이터 변환 """
        import re
        pattern = r'(\d{4})Q([1-4])'
        match = re.match(pattern, q_string)
        if not match:
            return []
        year, q = int(match.group(1)), int(match.group(2))
        quarter_map = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
        return [f"{year}{m:02d}" for m in quarter_map[q]]

    df_quarter = df[df['TIME'].str.contains('Q')]
    df_monthly = df[~df['TIME'].str.contains('Q')]

    expanded_rows = []
    for _, row in df_quarter.iterrows():
        for month in quarter_to_months(row['TIME']):
            new_row = row.copy()
            new_row['TIME'] = month
            expanded_rows.append(new_row)

    df_quarter_expanded = pd.DataFrame(expanded_rows)
    df_result = pd.concat([df_monthly, df_quarter_expanded], ignore_index=True)

    # ✅ 데이터 정리
    df = df_result.pivot(index='TIME', columns='ITEM_NAME1', values='DATA_VALUE')
    df.columns.name = None
    df = df.reset_index()
    df = df.rename(columns={
        "국내총생산(GDP)(실질, 계절조정, 전기비)": "GDP",
        "원/미국달러(매매기준율)": "환율",
        "총지수(생산자물가지수)": "생산자물가지수",
        "총지수(소비자물가지수)": "소비자물가지수",
        "한국은행 기준금리": "금리"
    })

    # ✅ MongoDB 저장
    records = df.to_dict(orient="records")  # 데이터프레임 -> 딕셔너리 변환
    await financial_data_collection.delete_many({})  # 기존 데이터 삭제 (최신 데이터 유지)
    await financial_data_collection.insert_many(records)  # 새로운 데이터 삽입

    return {"message": "데이터 수집 및 저장 완료", "total_records": len(records)}
