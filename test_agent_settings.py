#!/usr/bin/env python
"""Main 에이전트 설정값 반영 확인 테스트"""
import asyncio
import httpx
import json

API_BASE_URL = "http://localhost:8000/api/v1"

async def test_agent_settings():
    """Main 에이전트의 설정값이 채팅 API에 반영되는지 테스트"""
    
    # 타임아웃을 60초로 설정
    timeout = httpx.Timeout(60.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1. 서버 상태 확인 (루트 엔드포인트)
        try:
            response = await client.get("http://localhost:8000/")
            if response.status_code == 200:
                print(f"✅ 서버가 실행 중입니다")
        except httpx.ConnectError:
            print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.")
            return
        
        # 2. 새 채팅 세션 생성
        try:
            session_response = await client.post(
                f"{API_BASE_URL}/chat_sessions",  
                json={
                    "title": "Agent 설정 테스트",
                    "user_id": "00000000-0000-0000-0000-000000000000"
                }
            )
            if session_response.status_code not in [200, 201]:  
                print(f"❌ 세션 생성 실패: {session_response.status_code}")
                print(session_response.text)
                return
                
            session_data = session_response.json()
            session_id = session_data["id"]
            print(f"\n✅ 새 세션 생성: {session_id}")
        except Exception as e:
            print(f"❌ 세션 생성 중 오류: {e}")
            return
        
        # 3. 테스트 메시지 전송 (temperature 값 확인)
        print("\n⏳ AI 응답 생성 중... (최대 60초 소요)")
        try:
            message_response = await client.post(
                f"{API_BASE_URL}/chat/{session_id}/messages",
                json={
                    "role": "user",
                    "content": "안녕하세요. 제가 설정한 temperature 값이 얼마인지 알려주세요."
                }
            )
            
            if message_response.status_code == 200:
                messages = message_response.json()["messages"]
                print("\n✅ 메시지 전송 성공")
                print("\n📝 사용자 메시지:")
                print(f"   {messages[0]['content']}")
                print("\n🤖 AI 응답:")
                print(f"   {messages[1]['content'][:200]}...")
            else:
                print(f"\n❌ 오류 발생: {message_response.status_code}")
                print(message_response.json())
        except httpx.ReadTimeout:
            print("\n❌ 타임아웃: AI 응답 생성이 60초를 초과했습니다.")
            print("   서버 로그를 확인하세요.")
        except Exception as e:
            print(f"\n❌ 메시지 전송 중 오류: {e}")

if __name__ == "__main__":
    print("🔍 Main 에이전트 설정값 반영 테스트")
    print("=" * 50)
    asyncio.run(test_agent_settings())
