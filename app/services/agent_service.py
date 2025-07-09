from typing import Dict, Any, List, Optional
from langchain.agents import Tool, AgentExecutor
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chat_models import ChatOpenAI
import os

# 환경 변수에서 API 키 가져오기
from dotenv import load_dotenv
load_dotenv()

# 서브 에이전트 1: 환불 정책 전문가
def handle_refund_inquiry(query: str) -> str:
    """
    환불 정책과 관련된 질문에 답변합니다.
    
    Args:
        query: 사용자 질문
        
    Returns:
        str: 환불 정책에 대한 답변
    """
    # TODO: 실제 환불 정책 로직으로 대체
    return """
    [환불 정책 전문가]
    
    현재 환불 정책에 따르면:
    - 제품 수령 후 7일 이내에 환불이 가능합니다.
    - 미개봉 제품에 한해 전액 환불이 가능합니다.
    - 배송비는 고객 부담이며, 반품 시 왕복 배송비가 발생할 수 있습니다.
    
    더 자세한 문의사항이 있으시면 언제든지 말씀해 주세요.
    """

# 서브 에이전트 2: 주문 상태 조회
def check_order_status(order_id: str) -> str:
    """
    주문 상태를 조회합니다.
    
    Args:
        order_id: 주문 번호
        
    Returns:
        str: 주문 상태 정보
    """
    # TODO: 실제 주문 조회 로직으로 대체
    return f"""
    [주문 조회 전문가]
    
    주문 번호: {order_id}
    상태: 배송 중
    예상 도착일: 2025-07-10
    택배사: 로지스택
    운송장 번호: 123-456-7890
    
    자세한 배송 조회는 택배사 홈페이지에서 가능합니다.
    """

# 서브 에이전트를 위한 도구 설정
SUB_AGENT_TOOLS = [
    Tool(
        name="refund_policy_expert",
        func=handle_refund_inquiry,
        description="""
        환불 정책과 관련된 질문에 답변합니다. 
        예를 들어 '환불 기간이 어떻게 되나요?', '반품 절차가 어떻게 되나요?'와 같은 질문에 답변할 때 사용하세요.
        입력은 사용자의 질문 그대로 전달해 주세요.
        """
    ),
    Tool(
        name="order_status_checker",
        func=check_order_status,
        description="""
        주문 상태를 조회합니다.
        사용자가 주문 번호를 알려주면 주문 상태를 확인할 때 사용하세요.
        입력은 반드시 주문 번호만 포함해야 합니다.
        """
    )
]

# 메인 에이전트 프롬프트 템플릿
MAIN_AGENT_PROMPT = """
당신은 사용자의 질문에 가장 적합한 전문가 에이전트에게 작업을 위임하는 메인 에이전트입니다.

사용자의 질문을 분석하여 다음 중 가장 적합한 도구를 선택하세요:
1. refund_policy_expert: 환불 정책 관련 질문
2. order_status_checker: 주문 상태 조회

사용자의 질문이 도구를 사용해야 하는 경우, 반드시 도구를 호출하세요.
도구를 사용하지 않아도 되는 일반적인 질문은 직접 답변하세요.

도구를 사용할 때는 사용자의 질문을 그대로 전달하거나, 필요한 경우 요약하여 전달하세요.
"""

# LangChain 에이전트 초기화
def initialize_agent() -> AgentExecutor:
    """
    LangChain 에이전트를 초기화합니다.
    
    Returns:
        AgentExecutor: 초기화된 에이전트 실행기
    """
    # LLM 초기화
    llm = ChatOpenAI(
        model="gpt-4-turbo-preview",
        temperature=0.2,
        api_key=os.getenv("OPENAI_API_KEY")
    )
    
    # 프롬프트 템플릿 설정
    prompt = ChatPromptTemplate.from_messages([
        ("system", MAIN_AGENT_PROMPT),
        MessagesPlaceholder("chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder("agent_scratchpad")
    ])
    
    # 도구 바인딩
    llm_with_tools = llm.bind_tools(SUB_AGENT_TOOLS)
    
    # 에이전트 파이프라인 설정
    agent = (
        {
            "input": lambda x: x["input"],
            "agent_scratchpad": lambda x: format_to_openai_tool_messages(
                x["intermediate_steps"]
            ),
            "chat_history": lambda x: x.get("chat_history", []),
        }
        | prompt
        | llm_with_tools
        | OpenAIToolsAgentOutputParser()
    )
    
    # 에이전트 실행기 생성
    agent_executor = AgentExecutor(
        agent=agent,
        tools=SUB_AGENT_TOOLS,
        verbose=True,
        handle_parsing_errors=True
    )
    
    return agent_executor

# 메인 에이전트 실행 함수
async def run_main_agent(user_message: str, session_id: str) -> Dict[str, Any]:
    """
    메인 에이전트를 실행하여 사용자 메시지에 대한 응답을 생성합니다.
    
    Args:
        user_message: 사용자 메시지
        session_id: 채팅 세션 ID (향후 대화 기록 관리를 위해 사용 예정)
        
    Returns:
        Dict[str, Any]: 에이전트 응답을 포함한 딕셔너리
    """
    try:
        # 에이전트 초기화
        agent = initialize_agent()
        
        # TODO: 세션 ID를 사용하여 대화 기록 로드 (향후 구현)
        # chat_history = load_chat_history(session_id)
        
        # 에이전트 실행
        response = await agent.ainvoke({
            "input": user_message,
            # "chat_history": chat_history,  # 향후 대화 기록 연동 시 사용
        })
        
        # TODO: 응답을 대화 기록에 저장 (향후 구현)
        # save_chat_message(session_id, "user", user_message)
        # save_chat_message(session_id, "assistant", response["output"])
        
        return {
            "status": "success",
            "message": response["output"],
            "session_id": session_id,
            "metadata": {
                "tool_used": response.get("intermediate_steps", []),
                "timestamp": str(response.get("timestamp", ""))
            }
        }
        
    except Exception as e:
        # 에러 처리
        error_message = f"에이전트 실행 중 오류가 발생했습니다: {str(e)}"
        print(f"[ERROR] {error_message}")
        
        return {
            "status": "error",
            "message": "죄송합니다. 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해 주세요.",
            "error": str(e),
            "session_id": session_id
        }