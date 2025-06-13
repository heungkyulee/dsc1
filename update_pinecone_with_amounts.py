#!/usr/bin/env python3
"""
통합 데이터 Pinecone 업데이트 스크립트
사용자 생성 데이터와 K-Startup API 데이터를 모두 포함하여 Pinecone에 저장
"""

import json
import os
import sys
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# 필요한 모듈 임포트
try:
    from config import config
    from logger import get_logger
    from rag_system import ingest_announcements_to_pinecone
    import data_handler
    
    logger = get_logger(__name__)
    
except ImportError as e:
    print(f"모듈 임포트 실패: {e}")
    print("필요한 패키지가 설치되어 있는지 확인하세요.")
    sys.exit(1)

def load_all_data_sources():
    """
    모든 데이터 소스에서 지원사업 정보를 로드합니다.
    """
    print("🔄 모든 데이터 소스 로드 시작...")
    
    all_data = {}
    
    # 1. K-Startup API 데이터 (kstartup_contest_info.json)
    try:
        if os.path.exists("kstartup_contest_info.json"):
            with open("kstartup_contest_info.json", 'r', encoding='utf-8') as f:
                api_data = json.load(f)
                if isinstance(api_data, dict):
                    for contest_id, contest_info in api_data.items():
                        if isinstance(contest_info, dict):
                            contest_info['data_source'] = 'api_data'
                            contest_info['source_type'] = 'K-Startup API'
                            all_data[str(contest_id)] = contest_info
                    print(f"📊 K-Startup API 데이터: {len(api_data)}개")
                else:
                    print("⚠️ kstartup_contest_info.json 형식이 올바르지 않습니다.")
    except Exception as e:
        print(f"⚠️ K-Startup API 데이터 로드 실패: {e}")
    
    # 2. 사용자 생성 데이터 (data_handler를 통해)
    try:
        data_handler.load_all_data()
        user_contests = data_handler.get_all_contests()
        
        user_count = 0
        for contest in user_contests:
            if isinstance(contest, dict):
                contest_id = contest.get('pblancId', contest.get('id', f"user_{user_count}"))
                
                # 사용자 생성 데이터 표시
                if contest.get('data_source') == 'user_created' or contest.get('is_user_generated'):
                    contest['data_source'] = 'user_created'
                    contest['source_type'] = '사용자 생성'
                    user_count += 1
                elif str(contest_id) not in all_data:
                    # 기존 데이터가 없으면 추가
                    contest['data_source'] = 'data_handler'
                    contest['source_type'] = 'Data Handler'
                
                all_data[str(contest_id)] = contest
        
        print(f"👤 사용자 생성 데이터: {user_count}개")
        print(f"📄 Data Handler 총 데이터: {len(user_contests)}개")
        
    except Exception as e:
        print(f"⚠️ 사용자 데이터 로드 실패: {e}")
    
    # 3. announcements.json 데이터
    try:
        if os.path.exists("announcements.json"):
            with open("announcements.json", 'r', encoding='utf-8') as f:
                announcements_data = json.load(f)
                if isinstance(announcements_data, dict):
                    announcements_count = 0
                    for ann_id, ann_info in announcements_data.items():
                        if str(ann_id) not in all_data and isinstance(ann_info, dict):
                            ann_info['data_source'] = 'announcements_json'
                            ann_info['source_type'] = 'Announcements JSON'
                            all_data[str(ann_id)] = ann_info
                            announcements_count += 1
                    print(f"📄 announcements.json 추가 데이터: {announcements_count}개")
    except Exception as e:
        print(f"⚠️ announcements.json 로드 실패: {e}")
    
    print(f"🎯 통합 데이터 총계: {len(all_data)}개")
    
    # 데이터 소스별 통계
    source_stats = {}
    for contest in all_data.values():
        source = contest.get('data_source', 'unknown')
        source_stats[source] = source_stats.get(source, 0) + 1
    
    print("📊 데이터 소스별 통계:")
    for source, count in source_stats.items():
        emoji = {
            'user_created': '👤',
            'api_data': '🏛️',
            'data_handler': '📄',
            'announcements_json': '📋',
            'unknown': '❓'
        }.get(source, '📄')
        print(f"   {emoji} {source}: {count}개")
    
    return all_data

def main():
    """메인 실행 함수"""
    print("=" * 80)
    print("🚀 통합 데이터 Pinecone 업데이트 시작")
    print("=" * 80)
    
    start_time = datetime.now()
    
    try:
        # 1. 모든 데이터 소스 로드
        all_contests_data = load_all_data_sources()
        
        if not all_contests_data:
            print("❌ 로드할 데이터가 없습니다.")
            return False
        
        print(f"\n📝 총 {len(all_contests_data)}개 지원사업 데이터 처리 시작...")
        
        # 2. Pinecone에 통합 데이터 저장
        print("\n🔄 Pinecone 업데이트 시작...")
        success, message = ingest_announcements_to_pinecone(all_contests_data)
        
        if success:
            print(f"✅ {message}")
            
            # 3. 결과 통계 출력
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            print("\n" + "=" * 80)
            print("🎉 통합 데이터 Pinecone 업데이트 완료!")
            print("=" * 80)
            print(f"⏱️  소요 시간: {duration:.2f}초")
            print(f"📊 처리된 데이터: {len(all_contests_data)}개")
            print(f"📅 완료 시간: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 데이터 소스별 통계 재출력
            source_stats = {}
            for contest in all_contests_data.values():
                source = contest.get('data_source', 'unknown')
                source_stats[source] = source_stats.get(source, 0) + 1
            
            print("\n📈 최종 통계:")
            for source, count in source_stats.items():
                emoji = {
                    'user_created': '👤',
                    'api_data': '🏛️', 
                    'data_handler': '📄',
                    'announcements_json': '📋',
                    'unknown': '❓'
                }.get(source, '📄')
                print(f"   {emoji} {source}: {count}개")
            
            print("\n💡 이제 챗봇에서 사용자 생성 데이터와 공식 데이터가 통합되어 검색됩니다!")
            return True
            
        else:
            print(f"❌ Pinecone 업데이트 실패: {message}")
            return False
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        logger.error(f"통합 데이터 업데이트 실패: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 