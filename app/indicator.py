#1

import requests
import pandas as pd
import numpy as np
from datetime import datetime

api_key = "DU39KYMCPH849TZL4ELE"
url = "https://ecos.bok.or.kr/api/StatisticSearch"

start_year = 2023
end_year = datetime.today().year
code_list = {'722Y001': 'M', '901Y009': 'M', '200Y102': 'Q', '731Y004': 'M', '404Y014':'M'}
num_list = ['0101000','0','10111', '0000001/0000100','*AA']
num = ''
data_list = []

for year in range(start_year, end_year + 1):
    for code, freq in code_list.items():
        # 월/분기 날짜를 따로 지정해줘야 함
        if freq == 'M':
            start_date = f"{year}01"
            end_date = f"{year}12"
        elif freq == 'Q':
            start_date = f"{year}Q1"
            end_date = f"{year}Q4"

        # 각 데이터에 들어있는 내용이 여러가지임에 따라 필요한 내용을 매핑
        if code == '722Y001':
            num = num_list[0]
        elif code == '901Y009':
            num = num_list[1]
        elif code == '200Y102':
            num = num_list[2]
        elif code == '731Y004':
            num = num_list[3]
        elif code == '404Y014':
            num = num_list[4]

        response = requests.get(f"{url}/{api_key}/json/kr/1/100/{code}/{freq}/{start_date}/{end_date}/{num}")
        data = response.json()
        print(data)

        if "StatisticSearch" in data:
            data_list.extend(data['StatisticSearch']['row'])

df = pd.DataFrame(data_list)
print(df)

#2
df.loc[df.STAT_CODE == '404Y014', 'ITEM_NAME1'] = '총지수(생산자물가지수)'
df.loc[df.STAT_CODE == '901Y009', 'ITEM_NAME1'] = '총지수(소비자물가지수)'
df = df.drop(columns=['STAT_CODE', 'STAT_NAME', 'ITEM_CODE1', 'ITEM_CODE2', 'ITEM_NAME2', 'ITEM_CODE3', 'ITEM_NAME3', 'ITEM_CODE4', 'ITEM_NAME4', 'WGT'])

#3 TIME 인덱스를 문자열로 변환
df.index = df.index.map(str)

def is_quarter(str_idx):
    return ("Q" in str_idx)

df_quarter = df[df.index.map(is_quarter)]
df_monthly = df[~df.index.map(is_quarter)]


#4 분기 ex)2023Q1과 같은 것을 202301,202302,202303으로 확장
import re


def quarter_to_months(q_string):
    """
        '2023Q1' -> ['202301','202302','202303']
        '2023Q2' -> ['202304','202305','202306']
        '2023Q3' -> ['202307','202308','202309']
        '2023Q4' -> ['202310','202311','202312']
    """
    pattern = r'(\d{4})Q([1-4])'
    match = re.match(pattern, q_string)
    if not match:
        return []
    year = int(match.group(1))
    q = int(match.group(2))
    quarter_map = {
        1: [1,2,3],
        2: [4,5,6],
        3: [7,8,9],
        4: [10,11,12]
    }
    months = quarter_map[q]
    return [f"{year}{m:02d}" for m in months]


df['TIME'] = df['TIME'].astype(str)
df_quarter = df[df['TIME'].str.contains('Q')]
df_monthly = df[~df['TIME'].str.contains('Q')]


expanded_rows = []
for idx, row in df_quarter.iterrows():
    q_str = row['TIME']
    month_list = quarter_to_months(q_str)
    for m_str in month_list:
        new_row = row.copy()
        new_row['TIME'] = m_str
        expanded_rows.append(new_row)

df_quarter_expanded = pd.DataFrame(expanded_rows)

df_result = pd.concat([df_monthly, df_quarter_expanded], ignore_index=True)


df = df_result.pivot(
    index='TIME',
    columns='ITEM_NAME1',
    values='DATA_VALUE'
)

df.columns.name = None
df = df.reset_index()

df = df.rename(columns={
    "국내총생산(GDP)(실질, 계절조정, 전기비)": "GDP",
    "원/미국달러(매매기준율)": "환율",
    "총지수(생산자물가지수)": "생산자물가지수",
    "총지수(소비자물가지수)": "소비자물가지수",
    "한국은행 기준금리": "금리"
})