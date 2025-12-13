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
        
        # 토큰이 만료된 경우 refresh_token으로 갱신 시도
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("토큰 만료 감지, refresh_token으로 갱신 시도")
                creds.refresh(Request())
                logger.info("토큰 갱신 완료")
                
                # 갱신된 토큰 저장
                with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                logger.info("갱신된 토큰 파일 저장 완료")
            except Exception as e:
                logger.error("토큰 갱신 실패", error=str(e))
                # refresh_token도 만료되었거나 취소된 경우
                raise RuntimeError(
                    "토큰 갱신에 실패했습니다. refresh_token이 만료되었거나 취소되었을 수 있습니다.\n"
                    "서버 환경에서는 자동 인증이 불가능합니다.\n"
                    f"로컬 환경에서 다음 명령을 실행하여 새로운 토큰을 생성하세요:\n"
                    f"  python save_credentials.py\n"
                    f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
                )
        
        # 토큰이 없거나 유효하지 않은 경우
        if not creds or not creds.valid:
            if not creds:
                if not os.path.exists(Config.GOOGLE_CREDENTIALS_FILE):
                    raise FileNotFoundError(
                        f"{Config.GOOGLE_CREDENTIALS_FILE} 파일이 없습니다. "
                        "구글 클라우드 콘솔에서 credentials.json을 다운로드하세요."
                    )
                
                # 서버 환경에서는 브라우저 인증 불가능
                raise RuntimeError(
                    f"{Config.GOOGLE_TOKEN_FILE} 파일이 없거나 유효하지 않습니다.\n"
                    "서버 환경에서는 자동 인증이 불가능합니다.\n"
                    "로컬 환경에서 다음 명령을 실행하여 토큰을 생성하세요:\n"
                    "  python save_credentials.py\n"
                    f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
                )
            
            # 토큰 저장
            with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            logger.info("토큰 파일 저장 완료")
        
        self.credentials = creds
        self.service = build('calendar', 'v3', credentials=creds)
        logger.info("구글 캘린더 서비스 초기화 완료")
    
    def _ensure_valid_credentials(self):
        """
        토큰이 유효한지 확인하고 필요시 갱신합니다.
        API 호출 전에 항상 호출해야 합니다.
        """
        if not self.credentials:
            logger.error("토큰이 없음")
            raise RuntimeError(
                f"{Config.GOOGLE_TOKEN_FILE} 파일이 없습니다.\n"
                "로컬 환경에서 다음 명령을 실행하여 토큰을 생성하세요:\n"
                "  python save_credentials.py\n"
                f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
            )
        
        # 토큰이 만료되었거나 곧 만료될 경우 갱신
        if self.credentials.expired and self.credentials.refresh_token:
            try:
                logger.info("토큰 만료 감지, 갱신 시도")
                self.credentials.refresh(Request())
                
                # 갱신된 토큰 저장
                with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                    token.write(self.credentials.to_json())
                logger.info("토큰 갱신 및 저장 완료")
                
                # 서비스 재생성 (새로운 토큰으로)
                self.service = build('calendar', 'v3', credentials=self.credentials)
            except Exception as e:
                logger.error("토큰 갱신 실패", error=str(e))
                # 서버 환경에서는 재인증 불가능하므로 에러 발생
                raise RuntimeError(
                    "토큰 갱신에 실패했습니다. 서버 환경에서는 자동 인증이 불가능합니다.\n"
                    "로컬 환경에서 다음 명령을 실행하여 새로운 토큰을 생성하세요:\n"
                    "  python save_credentials.py\n"
                    f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
                )
        elif not self.credentials.valid:
            logger.error("토큰이 유효하지 않음")
            raise RuntimeError(
                f"{Config.GOOGLE_TOKEN_FILE} 파일이 유효하지 않습니다.\n"
                "로컬 환경에서 다음 명령을 실행하여 새로운 토큰을 생성하세요:\n"
                "  python save_credentials.py\n"
                f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
            )
    
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
        # API 호출 전 토큰 유효성 확인
        self._ensure_valid_credentials()
        
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
        
        try:
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
            # 인증 에러인 경우 토큰 갱신 후 재시도
            error_str = str(error)
            if 'invalid_grant' in error_str or 'Token has been expired' in error_str:
                logger.error("인증 에러 감지", error=error_str)
                # 토큰 갱신 시도
                try:
                    if self.credentials and self.credentials.refresh_token:
                        logger.info("토큰 갱신 시도")
                        self.credentials.refresh(Request())
                        with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                            token.write(self.credentials.to_json())
                        self.service = build('calendar', 'v3', credentials=self.credentials)
                        logger.info("토큰 갱신 완료, 재시도")
                        
                        # 재시도
                        events_result = self.service.events().list(
                            calendarId=Config.GOOGLE_CALENDAR_ID,
                            timeMin=time_min,
                            timeMax=time_max,
                            maxResults=2500,
                            singleEvents=True,
                            orderBy='startTime'
                        ).execute()
                        
                        events = events_result.get('items', [])
                        logger.info("이벤트 조회 완료 (재시도)", count=len(events))
                        
                        formatted_events = []
                        for event in events:
                            formatted_event = self._format_event(event)
                            if formatted_event:
                                formatted_events.append(formatted_event)
                        
                        return formatted_events
                except Exception as refresh_error:
                    logger.error("토큰 갱신 실패", error=str(refresh_error))
                    # 서버 환경에서는 재인증 불가능하므로 에러 발생
                    raise RuntimeError(
                        "토큰 갱신에 실패했습니다. 서버 환경에서는 자동 인증이 불가능합니다.\n"
                        "로컬 환경에서 다음 명령을 실행하여 새로운 토큰을 생성하세요:\n"
                        "  python save_credentials.py\n"
                        f"생성된 {Config.GOOGLE_TOKEN_FILE} 파일을 서버에 업로드하세요."
                    )
            else:
                logger.error("구글 캘린더 API 오류", error=error_str)
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
        # API 호출 전 토큰 유효성 확인
        self._ensure_valid_credentials()
        
        try:
            calendar = self.service.calendars().get(
                calendarId=Config.GOOGLE_CALENDAR_ID
            ).execute()
            return calendar.get('etag')
        except HttpError as error:
            # 인증 에러인 경우 토큰 갱신 후 재시도
            error_str = str(error)
            if 'invalid_grant' in error_str or 'Token has been expired' in error_str:
                logger.error("인증 에러 감지 (ETag)", error=error_str)
                try:
                    if self.credentials and self.credentials.refresh_token:
                        logger.info("토큰 갱신 시도 (ETag)")
                        self.credentials.refresh(Request())
                        with open(Config.GOOGLE_TOKEN_FILE, 'w') as token:
                            token.write(self.credentials.to_json())
                        self.service = build('calendar', 'v3', credentials=self.credentials)
                        logger.info("토큰 갱신 완료 (ETag), 재시도")
                        
                        calendar = self.service.calendars().get(
                            calendarId=Config.GOOGLE_CALENDAR_ID
                        ).execute()
                        return calendar.get('etag')
                except Exception as refresh_error:
                    logger.error("토큰 갱신 실패 (ETag)", error=str(refresh_error))
                    # 서버 환경에서는 재인증 불가능하므로 None 반환 (에러 발생하지 않음)
                    # ETag 조회 실패는 치명적이지 않으므로 None 반환
                    return None
            else:
                logger.warning("ETag 조회 실패", error=error_str)
                return None
        except Exception as e:
            logger.warning("ETag 조회 실패", error=str(e))
            return None

