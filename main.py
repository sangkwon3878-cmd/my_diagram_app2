import streamlit as st
import google.generativeai as genai
from PIL import Image
import re
import streamlit.components.v1 as components
from dotenv import load_dotenv
import os

# .env 파일에서 환경 변수 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="손그림 다이어그램 변환기",
    page_icon="📊",
    layout="wide"
)

# 제목
st.title("📊 손그림 다이어그램 변환기")
st.markdown("손으로 그린 다이어그램을 Mermaid.js 코드로 변환합니다.")

# .env 파일에서 API 키 불러오기
default_api_key = os.getenv("GEMINI_API_KEY", "")

# 사이드바에 API 키 입력
with st.sidebar:
    st.header("⚙️ 설정")
    
    # .env 파일에서 키가 있는지 표시
    if default_api_key:
        st.success("✅ .env 파일에서 API 키를 불러왔습니다.")
        use_env_key = st.checkbox("환경 변수에서 불러온 키 사용", value=True)
    else:
        use_env_key = False
        st.info("💡 .env 파일에 GEMINI_API_KEY를 설정하면 매번 입력할 필요가 없습니다.")
    
    # API 키 입력 필드 (환경 변수 키를 사용하지 않을 때만 활성화)
    api_key_input = st.text_input(
        "Google Gemini API Key (선택사항)",
        type="password",
        help=".env 파일에 키가 없거나 다른 키를 사용하려면 여기에 입력하세요.",
        disabled=use_env_key
    )
    
    st.markdown("---")
    st.markdown("### 📝 사용 방법")
    st.markdown("""
    1. Google Gemini API 키를 입력하세요 (또는 .env 파일에 설정)
    2. 손그림 다이어그램 이미지를 업로드하세요
    3. AI가 자동으로 Mermaid 코드로 변환합니다
    """)

# API 키 결정: 환경 변수 또는 사용자 입력
if use_env_key and default_api_key:
    api_key = default_api_key
elif api_key_input:
    api_key = api_key_input
else:
    api_key = default_api_key

# API 키가 입력되었는지 확인
if not api_key:
    st.warning("⚠️ .env 파일에 GEMINI_API_KEY를 설정하거나 사이드바에서 API 키를 입력해주세요.")
    st.info("💡 .env 파일을 만들고 다음 내용을 추가하세요:\n```\nGEMINI_API_KEY=your_api_key_here\n```")
    st.stop()

# Gemini API 설정
try:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"❌ API 설정 중 오류가 발생했습니다: {str(e)}")
    st.stop()

# 이미지 업로드
uploaded_file = st.file_uploader(
    "이미지 파일을 업로드하세요 (JPG, PNG, JPEG)",
    type=['jpg', 'png', 'jpeg'],
    help="손으로 그린 다이어그램 이미지를 선택하세요."
)

if uploaded_file is not None:
    # 이미지 표시
    image = Image.open(uploaded_file)
    st.image(image, caption="업로드된 이미지", use_container_width=True)
    
    # 변환 버튼
    if st.button("🔄 다이어그램 변환하기", type="primary"):
        with st.spinner("AI가 이미지를 분석하고 Mermaid 코드를 생성하는 중..."):
            try:
                # Gemini에 이미지와 프롬프트 전송
                prompt = """이 이미지를 분석하고 Mermaid.js 다이어그램 코드로 변환해주세요. 
다이어그램의 구조, 관계, 흐름을 정확히 파악하여 적절한 Mermaid 다이어그램 타입(flowchart, sequenceDiagram, classDiagram, stateDiagram 등)을 선택하세요.
응답에는 오직 Mermaid 코드만 포함하고, 마크다운 코드 블록 기호(```)나 설명은 포함하지 마세요."""

                response = model.generate_content([prompt, image])
                
                # 응답에서 Mermaid 코드 추출
                mermaid_code = response.text.strip()
                
                # 마크다운 코드 블록 제거
                # ```mermaid ... ``` 또는 ``` ... ``` 패턴 제거
                mermaid_code = re.sub(r'```mermaid\s*', '', mermaid_code)
                mermaid_code = re.sub(r'```\s*', '', mermaid_code)
                mermaid_code = mermaid_code.strip()
                
                # 결과 표시
                st.success("✅ 변환 완료!")
                
                # Mermaid 다이어그램 시각화
                st.subheader("📊 변환된 다이어그램")
                
                # streamlit-mermaid 사용
                try:
                    from streamlit_mermaid import st_mermaid
                    st_mermaid(mermaid_code)
                except ImportError:
                    # streamlit-mermaid가 없는 경우 HTML로 렌더링
                    st.warning("streamlit-mermaid 라이브러리를 사용할 수 없습니다. HTML로 렌더링합니다.")
                    mermaid_html = f"""
                    <div class="mermaid">
                    {mermaid_code}
                    </div>
                    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                    <script>
                        mermaid.initialize({{startOnLoad:true}});
                    </script>
                    """
                    components.html(mermaid_html, height=600)
                
                # 코드 표시
                st.subheader("📝 생성된 Mermaid 코드")
                st.code(mermaid_code, language="mermaid")
                
                # 코드 다운로드 버튼
                st.download_button(
                    label="💾 코드 다운로드",
                    data=mermaid_code,
                    file_name="diagram.mmd",
                    mime="text/plain"
                )
                
            except Exception as e:
                st.error(f"❌ 변환 중 오류가 발생했습니다: {str(e)}")
                st.info("다시 시도해주세요. 이미지가 명확한지 확인하거나 다른 이미지를 업로드해보세요.")

else:
    st.info("👆 위에서 이미지 파일을 업로드해주세요.")
