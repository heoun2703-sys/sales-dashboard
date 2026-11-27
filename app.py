# 지역·상품 카테고리별 매출 현황 대시보드
# 기획: 매장 관리자가 지역·상품 카테고리·기간을 선택해 매출 실적과 추이를 확인하는 화면

import streamlit as st  # 웹 화면을 만드는 라이브러리
import pandas as pd  # 표 형태 데이터를 다루는 라이브러리

# 페이지 설정: 브라우저 탭 제목, 화면을 넓게(wide) 사용 (반드시 다른 st 명령보다 먼저 써야 함)
st.set_page_config(page_title="지역·상품 카테고리별 매출 현황", layout="wide")

DATA_FILE = "sales_sample.csv"  # 읽을 CSV 파일 이름 (app.py와 같은 폴더에 있어야 함)
REQUIRED_COLUMNS = ["date", "region", "category", "sales", "quantity"]  # 꼭 있어야 하는 열


# 데이터 불러오기 함수
# @st.cache_data: 한 번 읽은 결과를 기억해 두어, 화면이 새로 그려질 때마다 파일을 다시 읽지 않게 한다.
# (파일이 없어서 오류가 나면 그 결과는 기억하지 않으므로, 파일을 넣은 뒤 새로고침하면 다시 읽는다.)
@st.cache_data
def load_data():
    # encoding="utf-8-sig": 파일 맨 앞의 보이지 않는 표시(BOM)를 없애 열 이름이 깨지지 않게 한다.
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    if "date" in df.columns:  # date 열이 있을 때만 날짜형으로 바꾼다 (없으면 아래에서 안내)
        df["date"] = pd.to_datetime(df["date"])
    return df


# 제목과 설명
st.title("지역·상품 카테고리별 매출 현황")  # 페이지 맨 위 큰 제목
st.write("지역·상품 카테고리·기간을 선택해 매출 실적과 추이를 확인합니다.")  # 화면 설명
st.caption("데이터 기준: 2026년 1~10월")  # 데이터 기간 안내 (작은 글씨)

# ── 방어 처리 1: CSV 파일이 없을 때 ──
try:
    df = load_data()  # 데이터를 불러와 df 변수에 저장
except FileNotFoundError:  # 파일을 찾지 못하면 이 부분이 실행된다
    st.error(
        f"데이터 파일 '{DATA_FILE}'을(를) 찾을 수 없습니다. "
        "파일 이름이 정확한지, app.py와 같은 폴더에 있는지 확인해 주세요."
    )
    st.stop()  # 아래 코드는 실행하지 않고 멈춘다

# ── 방어 처리 2: 필수 열이 빠져 있을 때 ──
missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]  # 없는 열만 모은다
if missing_columns:  # 빠진 열이 하나라도 있으면
    st.error(
        f"데이터 파일에 꼭 필요한 열이 없습니다: {', '.join(missing_columns)}. "
        "CSV 파일의 첫 줄(열 이름)을 확인해 주세요."
    )
    st.stop()

# ── 왼쪽 사이드바: 조건(필터) 선택 ──
st.sidebar.title("조건 선택")  # 사이드바 제목

# 1) 지역: 여러 개 선택 가능, 처음에는 모든 지역이 선택된 상태
region_list = sorted(df["region"].unique())  # 지역 이름 목록 (가나다순)
selected_regions = st.sidebar.multiselect("지역", region_list, default=region_list)

# 2) 상품 카테고리: 드롭다운에서 하나 선택, 맨 앞에 '전체' 추가
category_list = ["전체"] + sorted(df["category"].unique())
selected_category = st.sidebar.selectbox("상품 카테고리", category_list)

# 3) 기간: 시작일~종료일을 고르는 날짜 범위 슬라이더
min_date = df["date"].min().date()  # 데이터의 가장 이른 날짜 (.date()로 날짜만 꺼냄)
max_date = df["date"].max().date()  # 데이터의 가장 늦은 날짜
start_date, end_date = st.sidebar.slider(
    "기간",
    min_value=min_date,
    max_value=max_date,
    value=(min_date, max_date),  # 값을 두 개 주면 '범위' 슬라이더가 된다
    format="YYYY-MM-DD",  # 날짜 표시 형식
)

# ── 조건에 맞는 데이터만 골라 filtered 만들기 ──
# 지역을 모두 해제하면 isin([])이 전부 False가 되어 자동으로 0건이 된다.
condition = (
    df["region"].isin(selected_regions)  # 선택한 지역에 포함되는지
    & df["date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))  # 기간 안에 있는지 (양 끝 포함)
)
if selected_category != "전체":  # '전체'가 아니면 카테고리 조건도 추가
    condition = condition & (df["category"] == selected_category)

filtered = df[condition]  # 조건이 True인 행만 남긴 데이터

# 필터 아래에 선택된 건수 / 전체 건수 표시
st.sidebar.write(f"선택 조건: {len(filtered):,}건 / 전체 {len(df):,}건")

# 0건이면 안내 문구를 보여주고, 아래 코드(숫자 카드·그래프·표)는 실행하지 않고 멈춘다.
if len(filtered) == 0:
    st.warning("조건에 맞는 데이터가 없습니다. 조건을 넓혀 보세요.")
    st.stop()

# 본문 탭 두 개 만들기
tab_summary, tab_detail = st.tabs(["요약", "상세 데이터"])

with tab_summary:  # '요약' 탭
    # 요약 숫자 계산 (필터가 적용된 filtered 사용)
    total_sales = filtered["sales"].sum()  # 총매출: sales 열의 합계
    order_count = len(filtered)  # 주문 건수: 데이터 행 수
    avg_sales = filtered["sales"].mean()  # 평균 주문액: sales 열의 평균

    # 세 개의 칸(열)을 만들어 숫자를 가로로 나란히 보여준다.
    col1, col2, col3 = st.columns(3)
    col1.metric("총매출", f"{total_sales:,.0f}원")  # :,.0f → 천 단위 쉼표, 소수점 없음
    col2.metric("주문 건수", f"{order_count:,}건")
    col3.metric("평균 주문액", f"{avg_sales:,.0f}원")

    # ── 그래프 1: 월별 매출 합계 (두 달 이상: 선 그래프 / 한 달: 막대그래프) ──
    st.subheader("월별 매출 합계")
    # 날짜를 "2026-01" 같은 '연-월' 글자로 바꿔 month 열을 만든다. (글자 순서 = 월 순서)
    monthly = filtered.assign(month=filtered["date"].dt.strftime("%Y-%m"))
    # 월별로 묶어서 sales 합계를 구하고, 월 순서대로 정렬한다.
    monthly_sales = monthly.groupby("month")["sales"].sum().sort_index()

    # 선은 점이 2개 이상일 때만 그려진다. 한 달(점 1개)이면 선이 안 보이므로 막대로 그린다.
    if len(monthly_sales) == 1:
        st.bar_chart(monthly_sales)  # 한 달: 막대 1개로 표시
    else:
        st.line_chart(monthly_sales)  # 두 달 이상: 선 그래프 (가로축: 월, 세로축: 매출 합계)

    # ── 그래프 2: 지역별 매출 합계 (막대그래프) ──
    st.subheader("지역별 매출 합계")
    # 지역별로 묶어서 sales 합계를 구하고, 매출이 큰 순서대로 정렬한다.
    region_sales = (
        filtered.groupby("region", as_index=False)["sales"].sum()
        .sort_values("sales", ascending=False)
    )
    # st.bar_chart는 막대를 가나다순으로 바꿔 버리므로,
    # streamlit에 들어 있는 st.vega_lite_chart로 '매출 큰 순서' 정렬을 직접 지정한다.
    st.vega_lite_chart(
        region_sales,
        {
            "mark": "bar",  # 막대그래프
            "encoding": {
                # x축: 지역, sort "-y" → y값(매출)이 큰 순서대로 막대를 놓는다
                "x": {"field": "region", "type": "nominal", "sort": "-y", "title": "지역"},
                # y축: 매출 합계 (천 단위 쉼표 표시)
                "y": {"field": "sales", "type": "quantitative", "title": "매출(원)", "axis": {"format": ","}},
            },
        },
        use_container_width=True,  # 화면 너비에 맞춤
    )

with tab_detail:  # '상세 데이터' 탭
    st.dataframe(filtered, use_container_width=True)  # 조건에 맞는 데이터를 표로 보여준다 (화면 너비에 맞춤)
