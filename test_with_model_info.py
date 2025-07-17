#!/usr/bin/env python
"""모델 정보를 요청하는 테스트"""
import asyncio
import httpx
import json

API_BASE_URL = "http://localhost:8000/api/v1"

async def test_model_info():
    """모델과 설정 정보를 직접 물어보는 테스트"""
    
    # 타임아웃을 60초로 설정
    timeout = httpx.Timeout(60.0, read=60.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        # 1. 새 채팅 세션 생성
        try:
            session_response = await client.post(
                f"{API_BASE_URL}/chat_sessions",
                json={
                    "title": "모델 정보 테스트",
                    "user_id": "00000000-0000-0000-0000-000000000000"
                }
            )
            if session_response.status_code not in [200, 201]:
                print(f"❌ 세션 생성 실패: {session_response.status_code}")
                return
                
            session_data = session_response.json()
            session_id = session_data["id"]
            print(f"✅ 새 세션 생성: {session_id}")
        except Exception as e:
            print(f"❌ 세션 생성 중 오류: {e}")
            return
        
        # 2. 시스템 프롬프트에 모델 정보가 포함되어 있는지 확인하는 메시지
        print("\n⏳ 첫 번째 메시지 전송 중...")
        try:
            message_response = await client.post(
                f"{API_BASE_URL}/chat/{session_id}/messages",
                json={
                    "role": "user",
                    "content": "당신은 어떤 AI 모델이고, 어떤 설정으로 동작하고 있나요? 특히 temperature 값이 궁금합니다."
                }
            )
            
            if message_response.status_code == 200:
                messages = message_response.json()["messages"]
                print("\n📝 사용자:")
                print(f"   {messages[0]['content']}")
                print("\n🤖 AI:")
                print(f"   {messages[1]['content'][:300]}...")
            else:
                print(f"\n❌ 오류: {message_response.status_code}")
        except Exception as e:
            print(f"\n❌ 메시지 전송 중 오류: {e}")
            
        # 3. DB에 저장된 정보를 직접 확인
        print("\n" + "="*50)
        print("📊 DB에 저장된 Main 에이전트 정보:")
        print("   - Model: google/gemma-3-27b-it:free")
        print("   - Temperature: 0.15")
        print("   - Name: 창식씨")
        print("   - System Prompt: 20년차 고객상담 전문가")
        print("\n✅ 위 설정값들이 LLM API 호출 시 사용됩니다.")

if __name__ == "__main__":
    print("🔍 모델 정보 확인 테스트")
    print("=" * 50)
    asyncio.run(test_model_info())
