"""설정 관리 모듈"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """애플리케이션 설정"""
    
    # Discord 설정
    DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
    DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
    
    # Google Calendar 설정
    GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    GOOGLE_TOKEN_FILE = os.getenv("GOOGLE_TOKEN_FILE", "token.json")
    GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
    
    # 스케줄링 설정
    CALENDAR_CHECK_INTERVAL = int(os.getenv("CALENDAR_CHECK_INTERVAL", "30"))
    
    # 이미지 생성 설정
    IMAGE_WIDTH = int(os.getenv("IMAGE_WIDTH", "1200"))
    IMAGE_HEIGHT = int(os.getenv("IMAGE_HEIGHT", "1400"))
    BACKGROUND_COLOR = os.getenv("BACKGROUND_COLOR", "#FDFEF0")
    TEXT_COLOR = os.getenv("TEXT_COLOR", "#323232")
    HEADER_COLOR = os.getenv("HEADER_COLOR", "#5865F2")
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")
    TITLE_FORMAT = os.getenv("TITLE_FORMAT", "english")  # "english" or "korean"
    
    @classmethod
    def validate(cls):
        """필수 설정값 검증"""
        errors = []
        if not cls.DISCORD_BOT_TOKEN:
            errors.append("DISCORD_BOT_TOKEN이 설정되지 않았습니다.")
        if not cls.DISCORD_CHANNEL_ID:
            errors.append("DISCORD_CHANNEL_ID가 설정되지 않았습니다.")
        if not os.path.exists(cls.GOOGLE_CREDENTIALS_FILE):
            errors.append(f"{cls.GOOGLE_CREDENTIALS_FILE} 파일이 존재하지 않습니다.")
        
        if errors:
            raise ValueError("\n".join(errors))
        
        return True

