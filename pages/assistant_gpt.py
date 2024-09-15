import streamlit as st

import time
import json

from openai import OpenAI as client
from langchain_community.retrievers import WikipediaRetriever
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from langchain.schema import Document
from typing import Iterable

# streamlit setting
st.set_page_config(page_title="어시스턴트 API", page_icon="🧊")

st.title("assistant API")
st.caption("이 앱은 OPEN AI에서 제공하는 어시스턴트 API를 지원하는 챗봇입니다.")
with st.sidebar:
    st.link_button("github로 이동", "https://github.com/2wonbin/nomad-assistant-challenge", use_container_width=True)
openai_api_key = ""
with st.sidebar:
    openai_api_key = st.text_input("OPENAI API KEY", type="default")
client = client(api_key=openai_api_key)

# utilities


def wikipedia_search(query):
    print(f"위키피디아에서 {query} 검색중")
    retriever = WikipediaRetriever()
    result = retriever.invoke(query)
    result = [content.page_content for content in result]
    return result


def duckduckgo_search(query):
    print(f"덕덕고에서 {query} 검색중")
    search = DuckDuckGoSearchAPIWrapper()
    result = search.results(query, max_results=5)
    return result


functions_map = {
    "wikipedia_search": wikipedia_search,
    "duckduckgo_search": duckduckgo_search,
}

functions = [
    {
        "type": "function",
        "function": {
            "name": "wikipedia_search",
            "description": "Use this tool to search information on Wikipedia. Use 'query' as a parameter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query you want to search on Wikipedia",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "duckduckgo_search",
            "description": "Use this tool to search information on DuckDuckGo. Use 'query' as a parameter.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The query you want to search on DuckDuckGo",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


## Assistant
def set_assistant():
    return client.beta.assistants.create(
        name="researcher assistant",
        instructions="""
        This is a researcher assistant. and You are very good at Korean. please use Korean. If your answer is not Korean, tranlate it to Korean.
        You have two options. You can use wikipedia or you can use duckduckgo engine. 
        When you receive the keyword, you can use the keyword to search the information. 
        If you find the infomation, sumarize it, and make it Markdown format.
        """,
        model="gpt-4o-mini",
        tools=functions,
    )


def set_thread(content):
    return client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": content,
            }
        ]
    )


def set_run(assistant_id, thread_id):
    return client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )


def get_run(thread_id, run_id):
    return client.beta.threads.runs.retrieve(
        thread_id=thread_id,
        run_id=run_id,
    )


def get_messages(thread_id):
    raw_messages = client.beta.threads.messages.list(thread_id=thread_id)
    messages = list(raw_messages)
    # print(f"메시지: {messages}")
    assistant_message = ""
    for message in messages:
        # print(f"메시지: {message}")
        if message.role == "assistant":
            assistant_message = message.content[0].text.value
    return assistant_message


class ToolOutput:
    def __init__(self, tool_call_id, output):
        self.tool_call_id = tool_call_id
        self.output = output

    def to_dict(self):
        # Document 객체를 문자열로 변환
        if isinstance(self.output, Document):
            output_str = self.output.content
        else:
            output_str = str(self.output)

        return {
            "tool_call_id": self.tool_call_id,
            "output": output_str,
        }


def get_tool_outputs(thread_id, run_id):
    run = get_run(thread_id, run_id)
    outputs = []

    for action in run.required_action.submit_tool_outputs.tool_calls:
        action_id = action.id
        function = action.function.name
        output = functions_map[function](action.function.arguments)
        outputs.append(ToolOutput(tool_call_id=action_id, output=output))

    return outputs  # outputs 리스트를 반환


def submit_tool_outputs(thread_id, run_id):
    outputs = get_tool_outputs(thread_id, run_id)
    if outputs:  # output이 빈 리스트가 아닌 경우에만 호출
        # ToolOutput 객체를 딕셔너리로 변환
        output_list = [output.to_dict() for output in outputs]
        # print(f"출력 리스트: {output_list}")
        client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread_id,
            run_id=run_id,
            tool_outputs=output_list,  # 딕셔너리로 전달
        )
    else:
        print("No tool outputs to submit.")


# render


def send_message(message, role, save=True):
    with st.chat_message(role):
        st.markdown(message)
    if save:
        save_message(message, role)


def save_message(message, role):
    st.session_state["messages"].append({"message": message, "role": role})


# 이전 메시지 표시 함수
def paint_history():
    for message in st.session_state["messages"]:
        send_message(
            message["message"],
            message["role"],
            save=False,
        )


search_keyword = ""

if openai_api_key == "":
    st.error("API를 사용하기 위해서는 API Key가 필요합니다. API Key를 입력해주세요.")
else:
    # 초기화
    with st.status("초기화중입니다.") as loading:
        if "assistant" not in st.session_state:
            st.session_state["assistant"] = set_assistant()

        if "messages" not in st.session_state:
            st.session_state["messages"] = []

        # 다운로드 버튼 사라짐 방지를 위한 세션 상태 최고화
        if "download_clicked" not in st.session_state:
            st.session_state["download_clicked"] = False
        loading.update(label="초기화 완료", expanded=False, state="complete")

    assistant = st.session_state["assistant"]
    # 초기 메시지
    send_message(
        message="기다려주셔서 감사합니다. 검색어를 입력하세요.",
        role="assistant",
        save=False,
    )
    paint_history()
    search_keyword = st.chat_input("검색어를 입력하세요.")

    if search_keyword and search_keyword != "":
        send_message(
            message=search_keyword,
            role="user",
            save=True,
        )
        thread = set_thread(search_keyword)
        run = set_run(assistant.id, thread.id)

        is_completed = False

        with st.status("어시스턴트가 요청을 처리중입니다.") as loading:
            while True:
                time.sleep(0.5)
                run = get_run(thread.id, run.id)
                print(f"상태: {run.status}")

                if run.status == "completed":
                    loading.update(label="어시스턴트가 요청을 처리했습니다.", state="complete")
                    is_completed = True
                    break
                elif run.status == "failed":
                    loading.error("어시스턴트가 요청을 처리하지 못했습니다.")
                    break
                elif run.status == "requires_action":
                    submit_tool_outputs(thread.id, run.id)
                    continue
                elif run.status == "in_progress":
                    continue
                else:
                    print("상태: ", run.status)
                    continue

        if is_completed:
            result = get_messages(thread.id)
            if result != "":
                send_message(result, "assistant", save=True)
                save_button = st.download_button(
                    "텍스트 파일로 다운로드",
                    data=result,
                    file_name=f"report.txt",
                    mime="text/plain",
                )
                if save_button:
                    st.success("다운로드가 완료되었습니다.")

            else:
                send_message("검색 결과가 없습니다.", "assisant", save=True)
        else:
            send_message("검색 결과가 없습니다.", "assistant", save=True)
