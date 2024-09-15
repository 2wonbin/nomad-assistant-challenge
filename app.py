import streamlit as st

st.set_page_config(page_title="파이썬 스터디 GPT 스터디", page_icon="🧊")

st.title("파이썬 스터디 GPT 스터디")
st.caption("이 앱은 streamlit으로 작성한 파이썬 스터디 GPT 졸업과제 입니다")
st.caption(
    "좌측에 있는 사이드바에서 'assistant gpt'를 클릭하시면 OPEN AI에서 제공하는 어시스턴트 API를 지원하는 챗봇을 사용할 수 있습니다."
)
st.link_button("assistant gpt로 이동", "/assistant_gpt")
