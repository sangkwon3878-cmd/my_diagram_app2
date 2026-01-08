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
    page_title="AI 자연어 다이어그램 에디터",
    page_icon="💬",
    layout="wide"
)

# 세션 상태 초기화 (상태 관리 - 가장 중요)
if 'mermaid_code' not in st.session_state:
    st.session_state.mermaid_code = ""
if 'original_code' not in st.session_state:
    st.session_state.original_code = ""  # 에러 시 복구용 원본 코드
if 'diagram_generated' not in st.session_state:
    st.session_state.diagram_generated = False
if 'edit_history' not in st.session_state:
    st.session_state.edit_history = []  # 수정 이력

# 제목
st.title("💬 AI 자연어 다이어그램 에디터")
st.markdown("손그림을 AI로 분석하고, **자연어로 대화하듯이** 다이어그램을 수정해보세요. Mermaid 코드를 몰라도 OK! 🎨")

# .env 파일에서 API 키 불러오기
default_api_key = os.getenv("GEMINI_API_KEY", "")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    
    # .env 파일에서 키가 있는지 표시
    if default_api_key:
        st.success("✅ .env 파일에서 API 키를 불러왔습니다.")
        use_env_key = st.checkbox("환경 변수에서 불러온 키 사용", value=True)
    else:
        use_env_key = False
        st.info("💡 .env 파일에 GEMINI_API_KEY를 설정하면 매번 입력할 필요가 없습니다.")
    
    # API 키 입력 필드
    api_key_input = st.text_input(
        "Google Gemini API Key (선택사항)",
        type="password",
        help=".env 파일에 키가 없거나 다른 키를 사용하려면 여기에 입력하세요.",
        disabled=use_env_key
    )
    
    st.markdown("---")
    st.header("📝 추가 정보")
    
    # 추가 설명 입력칸
    additional_context = st.text_area(
        "추가 설명 (선택사항)",
        height=100,
        help="이미지가 흐릿하거나 특정 부분을 강조하고 싶을 때 추가 정보를 입력하세요.",
        placeholder="예: 이 다이어그램은 웹 애플리케이션의 사용자 인증 흐름을 나타냅니다..."
    )
    
    st.markdown("---")
    st.markdown("### 📖 사용 방법")
    st.markdown("""
    1. API 키를 설정하세요
    2. 손그림 다이어그램 이미지를 업로드하세요
    3. AI가 자동으로 변환합니다
    4. 자연어로 수정 요청을 입력하세요
       - "시작 상자를 파란색 원으로 바꿔줘"
       - "두 번째 단계를 더 구체적으로 설명해줘"
       - "전체적으로 파스텔 톤으로 꾸며줘"
    """)

# API 키 결정
if use_env_key and default_api_key:
    api_key = default_api_key
elif api_key_input:
    api_key = api_key_input
else:
    api_key = default_api_key

# API 키 확인
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

# 이미지 업로드 섹션
st.header("📤 이미지 업로드")
uploaded_file = st.file_uploader(
    "이미지 파일을 업로드하세요 (JPG, PNG, JPEG)",
    type=['jpg', 'png', 'jpeg'],
    help="손으로 그린 다이어그램 이미지를 선택하세요."
)

# 이미지가 업로드되었을 때
if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    # 이미지 미리보기
    st.image(image, caption="업로드된 이미지", use_container_width=True)
    
    # 변환 버튼
    if st.button("🔄 AI로 다이어그램 변환하기", type="primary", use_container_width=True):
        with st.spinner("AI가 이미지를 매우 상세하게 분석하고 전문적인 Mermaid 코드를 생성하는 중..."):
            try:
                # 고도화된 초기 생성 프롬프트
                base_prompt = """이미지를 매우 상세하게 분석하고 전문적인 Mermaid.js 다이어그램 코드로 변환해주세요.

요구사항:
1. 다이어그램의 구조, 관계, 흐름을 정확히 파악하여 적절한 Mermaid 다이어그램 타입(flowchart, sequenceDiagram, classDiagram, stateDiagram 등)을 선택하세요.

2. 노드(상자) 내용은 단순히 단어만 나열하지 말고, 의미를 분석하여 구체적이고 명확한 문장으로 작성하세요.
   예: "시작" → "사용자 로그인 프로세스 시작"
   예: "검증" → "사용자 자격 증명 검증 및 인증"
   예: "데이터" → "고객 데이터베이스에서 사용자 정보 조회"

3. 반드시 스타일링(classDef)을 포함하여 PPT처럼 시각적으로 아름답게 만들어주세요:
   - 시작/종료 노드: 둥근 모서리 (()), 파란색 배경 (#4A90E2), 흰색 텍스트
   - 중요 단계/프로세스: 직사각형 ([]), 주황색 배경 (#FF6B6B), 흰색 텍스트
   - 결정/조건 노드: 다이아몬드 모양 ({}), 노란색 배경 (#FFD93D), 검은색 텍스트
   - 일반 단계: 직사각형 ([]), 연한 회색 배경 (#E8E8E8), 검은색 텍스트
   - 성공/완료: 둥근 모서리 (()), 초록색 배경 (#6BCB77), 흰색 텍스트
   - 에러/실패: 직사각형 ([]), 빨간색 배경 (#FF4757), 흰색 텍스트
   
4. Mermaid의 style 문법을 적극 활용:
   - classDef를 사용하여 각 노드 타입별 스타일 정의
   - class 문으로 노드에 스타일 적용
   - 폰트 크기, 굵기, 색상 등을 세밀하게 조정
   - 다이어그램 배경은 깔끔하게 처리

5. 응답에는 오직 Mermaid 코드만 포함하고, 마크다운 코드 블록 기호(```)나 설명은 포함하지 마세요."""

                # 추가 설명이 있으면 프롬프트에 추가
                if additional_context.strip():
                    prompt = f"""{base_prompt}

추가 정보: {additional_context}

위의 추가 정보를 참고하여 더 정확한 다이어그램을 생성해주세요."""
                else:
                    prompt = base_prompt

                response = model.generate_content([prompt, image])
                
                # 응답에서 Mermaid 코드 추출
                mermaid_code = response.text.strip()
                
                # 마크다운 코드 블록 제거
                mermaid_code = re.sub(r'```mermaid\s*', '', mermaid_code)
                mermaid_code = re.sub(r'```\s*', '', mermaid_code)
                mermaid_code = mermaid_code.strip()
                
                # 세션 상태에 저장 (원본도 함께 저장)
                st.session_state.mermaid_code = mermaid_code
                st.session_state.original_code = mermaid_code  # 원본 백업
                st.session_state.diagram_generated = True
                st.session_state.edit_history = []  # 수정 이력 초기화
                
                st.success("✅ 변환 완료! 이제 자연어로 다이어그램을 수정할 수 있습니다.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ 변환 중 오류가 발생했습니다: {str(e)}")
                st.info("다시 시도해주세요. 이미지가 명확한지 확인하거나 다른 이미지를 업로드해보세요.")

# AI 자연어 에디터 모드 (다이어그램이 생성된 경우)
if st.session_state.diagram_generated and st.session_state.mermaid_code:
    st.markdown("---")
    st.header("✏️ 자연어로 다이어그램 수정하기")
    st.markdown("**예시:** '시작 상자를 파란색 원으로 바꿔줘', '두 번째 단계 설명을 더 구체적으로', '전체적으로 파스텔 톤으로 꾸며줘'")
    
    # 좌우 2단 컬럼 레이아웃
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("💬 다이어그램 수정 요청")
        
        # 자연어 수정 요청 입력창
        edit_request = st.text_area(
            "수정하고 싶은 내용을 자연어로 입력하세요:",
            height=150,
            placeholder="예: 시작 상자를 파란색 원으로 바꿔줘\n예: 두 번째 단계 설명을 '데이터 전처리 및 분석'으로 구체화해줘\n예: 전체적으로 파스텔 톤으로 꾸며줘",
            help="원하는 수정사항을 자연어로 자유롭게 입력하세요."
        )
        
        # 수정하기 버튼
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            if st.button("✨ 수정하기", type="primary", use_container_width=True):
                if edit_request.strip():
                    with st.spinner("AI가 요청사항을 반영하여 다이어그램을 수정하는 중..."):
                        try:
                            # 수정 요청 프롬프트
                            modification_prompt = f"""너는 전문 다이어그램 디자이너야. 기존 Mermaid 코드의 구조를 유지하되, 사용자의 요청을 정확히 반영해서 코드를 수정해줘.

현재 Mermaid 코드:
```
{st.session_state.mermaid_code}
```

사용자의 수정 요청:
{edit_request}

요구사항:
1. 기존 다이어그램의 전체 구조와 노드 간 연결 관계를 유지해줘.
2. 사용자의 요청을 정확히 반영하여 수정해줘.
3. Mermaid의 style 문법을 적극 활용해서 색상, 도형 모양((), {{}}, ([]) 등), 폰트 스타일을 PPT처럼 예쁘게 꾸며줘.
4. classDef를 사용하여 스타일을 정의하고, class 문으로 적용해줘.
5. 색상은 시각적으로 조화롭고 전문적으로 보이도록 선택해줘.
6. 응답에는 오직 수정된 Mermaid 코드만 포함하고, 마크다운 코드 블록 기호(```)나 설명은 포함하지 마세요."""

                            response = model.generate_content(modification_prompt)
                            
                            # 응답에서 Mermaid 코드 추출
                            modified_code = response.text.strip()
                            
                            # 마크다운 코드 블록 제거
                            modified_code = re.sub(r'```mermaid\s*', '', modified_code)
                            modified_code = re.sub(r'```\s*', '', modified_code)
                            modified_code = modified_code.strip()
                            
                            # 수정된 코드로 업데이트
                            st.session_state.mermaid_code = modified_code
                            st.session_state.edit_history.append({
                                'request': edit_request,
                                'code': modified_code
                            })
                            
                            st.success("✅ 수정 완료!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ 수정 중 오류가 발생했습니다: {str(e)}")
                            st.warning("⚠️ 원본 코드로 복구되었습니다.")
                            # 에러 발생 시 원본 코드로 복구
                            st.session_state.mermaid_code = st.session_state.original_code
                            st.rerun()
                else:
                    st.warning("⚠️ 수정 요청을 입력해주세요.")
        
        with col_btn2:
            if st.button("🔄 원본으로 복구", use_container_width=True):
                st.session_state.mermaid_code = st.session_state.original_code
                st.success("✅ 원본 코드로 복구되었습니다.")
                st.rerun()
        
        st.markdown("---")
        
        # 코드 보기 (Expander)
        with st.expander("📋 현재 적용된 Mermaid 코드 보기"):
            st.code(st.session_state.mermaid_code, language="mermaid")
            
            # 코드 다운로드 버튼
            st.download_button(
                label="💾 코드 다운로드",
                data=st.session_state.mermaid_code,
                file_name="diagram.mmd",
                mime="text/plain",
                use_container_width=True
            )
        
        # 수정 이력 표시
        if st.session_state.edit_history:
            with st.expander("📜 수정 이력"):
                for i, edit in enumerate(reversed(st.session_state.edit_history[-5:]), 1):
                    st.markdown(f"**{i}.** {edit['request']}")
    
    with col_right:
        st.subheader("📊 다이어그램 미리보기")
        
        # 다이어그램 렌더링
        if st.session_state.mermaid_code:
            try:
                from streamlit_mermaid import st_mermaid
                st_mermaid(st.session_state.mermaid_code, height=700)
            except ImportError:
                # streamlit-mermaid가 없는 경우 HTML로 렌더링
                mermaid_html = f"""
                <div class="mermaid">
                {st.session_state.mermaid_code}
                </div>
                <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
                <script>
                    mermaid.initialize({{
                        startOnLoad: true,
                        theme: 'default',
                        themeVariables: {{
                            primaryColor: '#4A90E2',
                            primaryTextColor: '#fff',
                            primaryBorderColor: '#357ABD',
                            lineColor: '#333',
                            secondaryColor: '#E8E8E8',
                            tertiaryColor: '#fff'
                        }}
                    }});
                </script>
                """
                components.html(mermaid_html, height=700)
        else:
            st.info("다이어그램이 생성되면 여기에 표시됩니다.")

else:
    if uploaded_file is None:
        st.info("👆 위에서 이미지 파일을 업로드하고 변환 버튼을 클릭해주세요.")
    else:
        st.info("👆 위의 'AI로 다이어그램 변환하기' 버튼을 클릭하여 다이어그램을 생성하세요.")
