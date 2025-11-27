"""캘린더 이미지 생성 테스트 스크립트"""
from datetime import datetime, timedelta
from image_generator import CalendarImageGenerator
import structlog

# 로깅 설정
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()


def create_sample_events():
    """테스트용 샘플 이벤트 데이터 생성"""
    now = datetime.now()
    year = now.year
    month = now.month
    
    # 해당 월의 첫 날
    first_day = datetime(year, month, 1)
    
    # 해당 월의 마지막 날 계산
    if month == 12:
        last_day = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = datetime(year, month + 1, 1) - timedelta(days=1)
    
    total_days = (last_day - first_day).days + 1
    
    # 샘플 이벤트 생성
    sample_events = [
        # 단일 일정
        {
            'id': 'test-1',
            'summary': '회의',
            'description': '팀 회의',
            'start': first_day + timedelta(days=2),
            'end': first_day + timedelta(days=2),
            'is_all_day': True,
            'location': '회의실 A',
            'color_id': '1',
        },
        # 2일간 이벤트
        {
            'id': 'test-2',
            'summary': '2일간 프로젝트',
            'description': '2일간 진행되는 프로젝트',
            'start': first_day + timedelta(days=5),
            'end': first_day + timedelta(days=6),
            'is_all_day': True,
            'location': '',
            'color_id': '2',
        },
        # 3일간 이벤트
        {
            'id': 'test-3',
            'summary': '3일 워크샵',
            'description': '3일간 진행되는 워크샵',
            'start': first_day + timedelta(days=8),
            'end': first_day + timedelta(days=10),
            'is_all_day': True,
            'location': '컨퍼런스 홀',
            'color_id': '3',
        },
        # 5일간 이벤트 (주간)
        {
            'id': 'test-4',
            'summary': '5일 휴가',
            'description': '5일간의 휴가',
            'start': first_day + timedelta(days=12),
            'end': first_day + timedelta(days=16),
            'is_all_day': True,
            'location': '',
            'color_id': '4',
        },
        # 7일간 이벤트 (일주일)
        {
            'id': 'test-5',
            'summary': '일주일 캠프',
            'description': '7일간 진행되는 캠프',
            'start': first_day + timedelta(days=18),
            'end': first_day + timedelta(days=24),
            'is_all_day': True,
            'location': '',
            'color_id': '5',
        },
        # 10일간 이벤트 (2주)
        {
            'id': 'test-6',
            'summary': '2주 프로젝트',
            'description': '10일간 진행되는 대규모 프로젝트',
            'start': first_day + timedelta(days=3),
            'end': first_day + timedelta(days=12),
            'is_all_day': True,
            'location': '',
            'color_id': '6',
        },
        # 월 초부터 시작하는 이벤트
        {
            'id': 'test-7',
            'summary': '월초 이벤트',
            'description': '월 초부터 시작하는 이벤트',
            'start': first_day,
            'end': first_day + timedelta(days=4),
            'is_all_day': True,
            'location': '',
            'color_id': '7',
        },
        # 월 말까지 이어지는 이벤트
        {
            'id': 'test-8',
            'summary': '월말까지 이벤트',
            'description': '월 말까지 계속되는 이벤트',
            'start': first_day + timedelta(days=total_days - 5),
            'end': last_day,
            'is_all_day': True,
            'location': '',
            'color_id': '8',
        },
        # 거의 한 달 전체를 차지하는 이벤트
        {
            'id': 'test-9',
            'summary': '장기 프로젝트',
            'description': '거의 한 달 전체를 차지하는 장기 프로젝트',
            'start': first_day + timedelta(days=7),
            'end': first_day + timedelta(days=total_days - 3),
            'is_all_day': True,
            'location': '',
            'color_id': '9',
        },
        # 주말에 걸치는 이벤트 (금요일부터 일요일까지)
        {
            'id': 'test-10',
            'summary': '주말 이벤트',
            'description': '금요일부터 일요일까지',
            'start': first_day + timedelta(days=5),  # 금요일
            'end': first_day + timedelta(days=7),    # 일요일
            'is_all_day': True,
            'location': '',
            'color_id': '10',
        },
        # 같은 날 여러 이벤트 (겹치는 날짜)
        {
            'id': 'test-11',
            'summary': '이벤트 A',
            'description': '',
            'start': first_day + timedelta(days=14),
            'end': first_day + timedelta(days=14),
            'is_all_day': True,
            'location': '',
            'color_id': '1',
        },
        {
            'id': 'test-12',
            'summary': '이벤트 B',
            'description': '',
            'start': first_day + timedelta(days=14),
            'end': first_day + timedelta(days=14),
            'is_all_day': True,
            'location': '',
            'color_id': '2',
        },
        {
            'id': 'test-13',
            'summary': '이벤트 C',
            'description': '',
            'start': first_day + timedelta(days=14),
            'end': first_day + timedelta(days=14),
            'is_all_day': True,
            'location': '',
            'color_id': '3',
        },
        {
            'id': 'test-14',
            'summary': '이벤트 D',
            'description': '4개 이상의 이벤트 테스트',
            'start': first_day + timedelta(days=14),
            'end': first_day + timedelta(days=14),
            'is_all_day': True,
            'location': '',
            'color_id': '4',
        },
        # 겹치는 여러 날짜 이벤트
        {
            'id': 'test-15',
            'summary': '겹치는 이벤트 1',
            'description': '다른 이벤트와 겹침',
            'start': first_day + timedelta(days=20),
            'end': first_day + timedelta(days=22),
            'is_all_day': True,
            'location': '',
            'color_id': '5',
        },
        {
            'id': 'test-16',
            'summary': '겹치는 이벤트 2',
            'description': '위 이벤트와 겹침',
            'start': first_day + timedelta(days=21),
            'end': first_day + timedelta(days=23),
            'is_all_day': True,
            'location': '',
            'color_id': '6',
        },
        # 짧은 기간 이벤트 (2일)
        {
            'id': 'test-17',
            'summary': '짧은 이벤트',
            'description': '2일간만 진행',
            'start': first_day + timedelta(days=25),
            'end': first_day + timedelta(days=26),
            'is_all_day': True,
            'location': '',
            'color_id': '7',
        },
        # 긴 기간 이벤트 (15일)
        {
            'id': 'test-18',
            'summary': '긴 기간 이벤트',
            'description': '15일간 진행되는 긴 이벤트',
            'start': first_day + timedelta(days=1),
            'end': first_day + timedelta(days=15),
            'is_all_day': True,
            'location': '',
            'color_id': '8',
        },
    ]
    
    return sample_events


def main():
    """메인 테스트 함수"""
    print("=" * 60)
    print("캘린더 이미지 생성 테스트")
    print("=" * 60)
    
    # 현재 날짜
    now = datetime.now()
    year = now.year
    month = now.month
    
    print(f"\n📅 테스트 대상: {year}년 {month}월")
    
    # 이미지 생성기 초기화
    try:
        generator = CalendarImageGenerator()
        print("✅ 이미지 생성기 초기화 완료")
    except Exception as e:
        print(f"❌ 이미지 생성기 초기화 실패: {e}")
        return
    
    # 샘플 이벤트 생성
    sample_events = create_sample_events()
    print(f"✅ 샘플 이벤트 {len(sample_events)}개 생성 완료")
    
    # 이미지 생성
    try:
        print("\n🖼️  이미지 생성 중...")
        image = generator.generate_month_image(year, month, sample_events)
        print("✅ 이미지 생성 완료")
    except Exception as e:
        print(f"❌ 이미지 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 이미지 저장
    output_filename = f"test_calendar_{year}_{month:02d}.png"
    try:
        generator.save_image(image, output_filename)
        print(f"✅ 이미지 저장 완료: {output_filename}")
        print(f"\n📁 파일 위치: {output_filename}")
        print(f"📏 이미지 크기: {image.size[0]} x {image.size[1]} px")
    except Exception as e:
        print(f"❌ 이미지 저장 실패: {e}")
        return
    
    print("\n" + "=" * 60)
    print("✅ 테스트 완료!")
    print("=" * 60)
    print(f"\n💡 팁: 생성된 이미지 파일({output_filename})을 열어서 확인하세요.")


if __name__ == "__main__":
    main()

