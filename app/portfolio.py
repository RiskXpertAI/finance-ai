import requests
import pandas as pd
import zipfile
import io
from xml.etree import ElementTree as ET
from datetime import datetime, timedelta

# ----------------------------
# 1. DART 오픈 API 설정
# ----------------------------
API_KEY = "e7e9c4b8525309ddf99f64d1ab9ff7be58646784"  # 사용자 API 키(샘플)
corp_code_url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={API_KEY}"

# ----------------------------
# 2. 우리은행 corp_code 조회
# ----------------------------
res = requests.get(corp_code_url)
res.raise_for_status()  # 요청 실패 시 예외 발생

with zipfile.ZipFile(io.BytesIO(res.content)) as z:
    corp_code_xml = z.read('CORPCODE.xml').decode('utf-8')

root = ET.fromstring(corp_code_xml)
woori_code = None
for company in root.findall('list'):
    name = company.findtext('corp_name')
    if name == "우리은행":
        woori_code = company.findtext('corp_code')
        break

if woori_code is None:
    raise Exception("우리은행의 회사 고유번호를 찾을 수 없습니다.")

print("[Info] 우리은행 corp_code:", woori_code)

# ----------------------------
# 3. 조회 기간 및 보고서 설정
# ----------------------------
end_date = datetime.today()
start_date = end_date - timedelta(days=365)
print("[Info] 조회기간:", start_date.strftime('%Y-%m-%d'), "부터", end_date.strftime('%Y-%m-%d'), "까지")

# 예시: 최근 1년이므로, 현재 연도-1 을 사업연도로 설정(또는 상황에 맞춰 수정)
target_year = end_date.year - 1  
report_code = "11011"  # 11011 = 사업보고서(연간)
print("[Info] 대상 사업연도:", target_year, "| 보고서 코드:", report_code)

# ----------------------------
# 4. 우리은행 재무제표 데이터 조회
# ----------------------------
fin_url = "https://opendart.fss.or.kr/api/fnlttSinglAcntAll.json"
params = {
    'crtfc_key': API_KEY,
    'corp_code': woori_code,
    'bsns_year': str(target_year),
    'reprt_code': report_code,
    'fs_div': 'OFS'  # 개별재무제표
}

response = requests.get(fin_url, params=params)
fin_data = response.json()

if fin_data.get('status') != '000':
    raise Exception(f"[Error] 재무정보 조회 실패: {fin_data.get('message')}")

fs_df = pd.DataFrame(fin_data['list'])
# 주요 컬럼만 추출
fs_df = fs_df[['account_nm', 'thstrm_amount', 'frmtrm_amount', 'fs_div', 'sj_div']]

# ----------------------------
# 5. 대출 포트폴리오 데이터
# ----------------------------
loan_accounts = fs_df[fs_df['account_nm'].str.contains('대출채')].copy()
loan_accounts['thstrm_amount'] = loan_accounts['thstrm_amount'].str.replace(',', '', regex=False).astype(float)
loan_accounts['frmtrm_amount'] = loan_accounts['frmtrm_amount'].str.replace(',', '', regex=False).astype(float)

total_loans_current = loan_accounts['thstrm_amount'].sum()  # 당기 대출채권 합계
total_loans_previous = loan_accounts['frmtrm_amount'].sum() if 'frmtrm_amount' in loan_accounts else total_loans_current
avg_loans = (total_loans_current + total_loans_previous) / 2

# 손익계산서(IS)에서 이자수익 항목 추출
interest_income_account = fs_df[
    (fs_df['account_nm'].str.contains('이자수익')) & (fs_df['sj_div'] == 'IS')
].copy()
interest_income = 0.0
if not interest_income_account.empty:
    # 쉼표 제거 후 float 변환
    interest_income = float(interest_income_account.iloc[0]['thstrm_amount'].replace(',', ''))

loan_yield = (interest_income / avg_loans * 100) if avg_loans else 0.0

loan_portfolio_df = pd.DataFrame([{
    "Loan_Balance_Current": total_loans_current,
    "Loan_Balance_Previous": total_loans_previous,
    "Interest_Income": interest_income,
    "Approx_Avg_Rate(%)": round(loan_yield, 2)
}])
print("\n[대출 포트폴리오 요약]")
print(loan_portfolio_df)

# ----------------------------
# 6. 채권(채무증권) 보유 현황
# ----------------------------
bond_accounts = fs_df[fs_df['account_nm'].str.contains('채무증권')].copy()
bond_accounts['thstrm_amount'] = bond_accounts['thstrm_amount'].str.replace(',', '', regex=False).astype(float)
if bond_accounts.empty:
    print("\n[채권 보유 현황] 재무제표 상에 '채무증권' 계정을 찾지 못했습니다.")
else:
    total_bonds = bond_accounts['thstrm_amount'].sum()
    bonds_df = bond_accounts[['account_nm', 'thstrm_amount']].reset_index(drop=True)
    bonds_df.columns = ["Category", "Amount"]
    print("\n[채권 보유 현황]")
    print(bonds_df)
    print(f"총 채권투자 자산: {total_bonds:,.0f}")

# ----------------------------
# 7. 주식(타법인 출자현황) 조회
# ----------------------------
inv_url = "https://opendart.fss.or.kr/api/otrCprInvstmntSttus.json"
params_inv = {
    'crtfc_key': API_KEY,
    'corp_code': woori_code,
    'bsns_year': str(target_year),
    'reprt_code': report_code
}
res_inv = requests.get(inv_url, params=params_inv)
inv_data = res_inv.json()

if inv_data.get('status') != '000':
    print(f"\n[주식 보유 현황] 조회 실패 또는 데이터 없음: {inv_data.get('message')}")
    stock_holdings_df = pd.DataFrame()
else:
    stock_holdings_df = pd.DataFrame(inv_data['list'])
    # 필요한 컬럼만 추출
    # 참고: inv_prm(출자법인명), trmend_blce_qy(기말잔액_수량), trmend_blce_qota_rt(기말잔액_지분율), trmend_blce_acntbk_amount(기말잔액_장부가액)
    stock_holdings_df = stock_holdings_df[["inv_prm", "trmend_blce_qy", "trmend_blce_qota_rt", "trmend_blce_acntbk_amount"]]
    stock_holdings_df.columns = ["Company", "Shares", "Ownership(%)", "BookValue"]
    # 타입 변환
    stock_holdings_df["Shares"] = stock_holdings_df["Shares"].str.replace(',', '', regex=False).astype(float)
    stock_holdings_df["Ownership(%)"] = stock_holdings_df["Ownership(%)"].str.replace(',', '', regex=False).astype(float)
    stock_holdings_df["BookValue"] = stock_holdings_df["BookValue"].str.replace(',', '', regex=False).astype(float)
    # 주당 평균 취득단가 (참고용)
    stock_holdings_df["Avg_Cost_per_Share"] = (stock_holdings_df["BookValue"] / 
                                               stock_holdings_df["Shares"]).round(2)

if not stock_holdings_df.empty:
    print(f"\n[주식 보유 현황] (총 {len(stock_holdings_df)}개 종목)")
    print(stock_holdings_df)
else:
    print("\n[주식 보유 현황] 해당 데이터가 없습니다.")

# ----------------------------
# 8. 파생상품(파생금융자산/부채) 조회
# ----------------------------
deriv_accounts = fs_df[fs_df['account_nm'].str.contains('파생')].copy()
deriv_accounts['thstrm_amount'] = deriv_accounts['thstrm_amount'].str.replace(',', '', regex=False).astype(float)

deriv_asset_val = deriv_accounts[deriv_accounts['account_nm'].str.contains('자산')]['thstrm_amount'].sum()
deriv_liab_val = deriv_accounts[deriv_accounts['account_nm'].str.contains('부채')]['thstrm_amount'].sum()

deriv_df = pd.DataFrame([{
    "DerivAsset_FairValue": deriv_asset_val,
    "DerivLiability_FairValue": deriv_liab_val
}])
print("\n[파생상품 포지션 평가잔액]")
print(deriv_df)

# ----------------------------
# 9. 기타 리스크 지표
# ----------------------------
# NPL률, BIS비율, LCR 등은 DART 표준 API로 직접 제공되지 않음
# -> 사업보고서의 '주석' 부분 또는 경영공시/리스크관리 보고서를 텍스트 크롤링/파싱해야 함.
stress_metrics = {
    "NPL_ratio(%)": None,
    "BIS_capital_ratio(%)": None,
    "LCR(%)": None
}
print("\n[기타 위험관리 지표] (별도 자료 필요):", stress_metrics)

# -------------------------------------------------------
# 최종적으로 아래 DataFrame/변수들을 활용 가능:
# 1) loan_portfolio_df (대출요약)
# 2) bonds_df (채권투자)
# 3) stock_holdings_df (주식보유)
# 4) deriv_df (파생상품평가)
# -------------------------------------------------------

print("\n[Done] 우리은행 주요 포트폴리오(대출, 채권, 주식, 파생상품) 데이터를 수집하였습니다.")