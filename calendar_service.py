"""구글 캘린더 API 연동 서비스"""
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import structlog

from config import Config

logger = structlog.get_logger()

# 구글 캘린더 API 스코프
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


class CalendarService:
    """구글 캘린더 서비스 클래스"""
    
    def __init__(self):
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self):
        """구글 캘린더 API 인증"""
        creds = None
        
        # 기존 토큰 파일이 있으면 로드
        if os.path.exists(Config.GOOGLE_TOKEN_FILE):
            try:
                creds = Credentials.from_authorized_user_file(
                    Config.GOOGLE_TOKEN_FILE, SCOPES
                )
                logger.info("기존 토큰 파일 로드 완료")
            except Exception as e:
                logger.warning("토큰 파일 로드 실패", error=str(e))
        
        # 토큰이 없거나 만료된 경우 재인증
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("토큰 갱신 완료")
                except Exception as e:
                    logger.warning("토큰 갱신 실패", error=str(e))
                    creds = None
            
            if not creds:
                if not os.path.exists(Config.GOOGLE_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"{Config.GOOGLE_CREDENTIALS_FILE} 파일이 없습니다. "
                        "구글 클라우드 콘솔에서 credentials.json을 다운로드하세요."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    Config.GOOGLE_CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)
                logger.info("새로운 인증 완료")
            
            # 토큰 저장
            with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            logger.info("토큰 파일 저장 완료")
        
        self.credentials = creds
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("구글 캘린더 서비스 초기화 완료")
    
    def get_events_for_month(
        self, 
        year: int, 
        month: int,
        timezone: str = 'Asia/Seoul'
    ) -> List[Dict]:
        """
        특정 월의 모든 이벤트를 가져옵니다.
        
        Args:
            year: 연도
            month: 월 (1-12)
            timezone: 타임존 (기본값: Asia/Seoul)
        
        Returns:
            이벤트 리스트
        """
        try:
            # 타임존 설정
            local_tz = pytz.timezone(timezone)
            
            # 해당 월의 시작과 끝 시간 계산 (타임존 적용)
            start_date = local_tz.localize(datetime(year, month, 1, 0, 0, 0))
            if month == 12:
                end_date = local_tz.localize(datetime(year + 1, 1, 1, 0, 0, 0))
            else:
                end_date = local_tz.localize(datetime(year, month + 1, 1, 0, 0, 0))
            
            time_min = start_date.isoformat()
            time_max = end_date.isoformat()
            
            logger.info(
                "이벤트 조회 시작",
                calendar_id=Config.GOOGLE_CALENDAR_ID,
                year=year,
                month=month
            )
            
            events_result = self.service.events().list(
                calendarId=Config.GOOGLE_CALENDAR_ID,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=2500,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            logger.info("이벤트 조회 완료", count=len(events))
            
            # 이벤트 데이터 정리
            formatted_events = []
            for event in events:
                formatted_event = self._format_event(event)
                if formatted_event:
                    formatted_events.append(formatted_event)
            
            return formatted_events
            
        except HttpError as error:
            logger.error("구글 캘린더 API 오류", error=str(error))
            raise
        except Exception as e:
            logger.error("이벤트 조회 중 오류 발생", error=str(e))
            raise
    
    def _format_event(self, event: Dict) -> Optional[Dict]:
        """
        이벤트 데이터를 포맷팅합니다.
        
        Args:
            event: 구글 캘린더 이벤트 딕셔너리
        
        Returns:
            포맷팅된 이벤트 딕셔너리
        """
        try:
            start = event.get('start', {})
            end = event.get('end', {})
            
            # 날짜/시간 파싱
            if 'dateTime' in start:
                start_dt = datetime.fromisoformat(start['dateTime'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end['dateTime'].replace('Z', '+00:00'))
                is_all_day = False
            elif 'date' in start:
                start_dt = datetime.fromisoformat(start['date'])
                end_dt = datetime.fromisoformat(end['date'])
                is_all_day = True
            else:
                return None
            
            return {
                'id': event.get('id'),
                'summary': event.get('summary', '(제목 없음)'),
                'description': event.get('description', ''),
                'start': start_dt,
                'end': end_dt,
                'is_all_day': is_all_day,
                'location': event.get('location', ''),
                'color_id': event.get('colorId'),
            }
        except Exception as e:
            logger.warning("이벤트 포맷팅 실패", event_id=event.get('id'), error=str(e))
            return None
    
    def get_calendar_etag(self) -> Optional[str]:
        """
        캘린더의 ETag를 가져옵니다.
        변경 감지를 위해 사용됩니다.
        
        Returns:
            캘린더 ETag 또는 None
        """
        try:
            calendar = self.service.calendars().get(
                calendarId=Config.GOOGLE_CALENDAR_ID
            ).execute()
            return calendar.get('etag')
        except Exception as e:
            logger.warning("ETag 조회 실패", error=str(e))
            return None

