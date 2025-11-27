# Calendar to Discord Bot

<img width="1200" height="1600" alt="Image" src="https://github.com/user-attachments/assets/90bba4fc-b093-4fbb-81f0-68a357697a3f" />

구글 캘린더 정보를 읽어서 한달치 스케줄 이미지를 생성하고 디스코드 채널에 게시하는 봇입니다.

## 기능

- 구글 캘린더에서 이벤트 정보 읽기
- 한달치 캘린더를 이미지로 생성 (Pillow 기반)
- 디스코드 채널에 이미지 자동 게시
- `/일정` 슬래시 커맨드로 수동 업데이트
- 주기적인 캘린더 체크 및 자동 업데이트 (ETag 기반 변경 감지)
- 여러 날짜에 걸친 이벤트 표시 지원
- 한글 폰트 지원 (MaruBuri)

## 설치 방법

### 1. 저장소 클론 및 가상환경 설정

```bash
# 가상환경 생성 (Windows)
python -m venv venv
venv\Scripts\activate

# 가상환경 생성 (Linux/Mac)
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. Google Calendar API 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Calendar API 활성화
3. OAuth 2.0 클라이언트 ID 생성 (데스크톱 앱)
4. `credentials.json` 파일을 프로젝트 루트에 저장

### 3. Discord Bot 생성

1. [Discord Developer Portal](https://discord.com/developers/applications)에서 애플리케이션 생성
2. Bot 섹션에서 봇 생성 및 토큰 복사
3. OAuth2 > URL Generator에서 `bot`과 `applications.commands` 스코프 선택
4. 생성된 URL로 봇을 서버에 초대
5. 채널 ID 확인 (디스코드 개발자 모드 활성화 후 채널 우클릭 > ID 복사)

### 4. 환경 변수 설정

`.env` 파일을 생성하고 다음 값들을 설정:

```env
# Discord 설정
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_CHANNEL_ID=your_channel_id

# Google Calendar 설정
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json
GOOGLE_CALENDAR_ID=primary

# 스케줄링 설정
CALENDAR_CHECK_INTERVAL=30  # 분 단위

# 이미지 생성 설정 (선택사항)
IMAGE_WIDTH=1200
IMAGE_HEIGHT=1400
BACKGROUND_COLOR=#FDFEF0
TEXT_COLOR=#323232
HEADER_COLOR=#5865F2
TIMEZONE=Asia/Seoul
TITLE_FORMAT=english  # "english" or "korean"
```

### 5. 초기 인증

Google Calendar API 인증을 위해 `save_credentials.py`를 실행합니다:

```bash
python save_credentials.py
```

브라우저가 열리고 구글 계정 인증을 요청합니다. 인증 후 `token.json` 파일이 생성됩니다.

## 실행 방법

```bash
# 가상환경 활성화 (Windows)
venv\Scripts\activate

# 가상환경 활성화 (Linux/Mac)
source venv/bin/activate

# 봇 실행
python main.py
```

## 사용법

### 슬래시 커맨드

- `/일정`: 현재 달의 캘린더 이미지를 생성하여 채널에 새 메시지로 게시

### 자동 업데이트

설정된 간격(기본 30분)마다 캘린더를 체크하고 변경사항이 있으면 자동으로 새 이미지를 게시합니다. 기존 메시지는 수정하지 않고 항상 새로운 메시지로 게시됩니다.

### 테스트

이미지 생성 기능을 테스트하려면:

```bash
python test_image_generator.py
```

생성된 이미지 파일을 확인하여 캘린더 레이아웃과 이벤트 표시를 검증할 수 있습니다.

## 프로젝트 구조

```
calendar_to_discord/
├── main.py                 # 봇 메인 파일
├── calendar_service.py     # 구글 캘린더 API 연동
├── image_generator.py      # 캘린더 이미지 생성
├── config.py               # 설정 관리
├── save_credentials.py     # Google OAuth 초기 인증 스크립트
├── test_image_generator.py # 이미지 생성 테스트 스크립트
├── requirements.txt        # 의존성 목록
├── fonts/                  # 폰트 파일 디렉토리
│   └── MaruBuri-*.ttf      # 한글 폰트 파일들
├── credentials.json        # Google OAuth 클라이언트 정보 (생성 필요)
├── token.json              # Google OAuth 토큰 (save_credentials.py 실행 후 생성)
└── README.md               # 이 파일
```

## 주요 특징

- **이미지 생성**: Pillow를 사용한 커스텀 캘린더 레이아웃
- **다중 날짜 이벤트**: 여러 날짜에 걸친 이벤트를 자동으로 분할하여 표시
- **한글 지원**: MaruBuri 폰트를 사용한 한글 이벤트 제목 표시 (이 봇에는 네이버에서 제공한 마루부리 글꼴이 적용되어 있습니다.)
- **자동 업데이트**: ETag 기반 변경 감지로 효율적인 캘린더 모니터링
- **새 메시지 게시**: 기존 메시지를 수정하지 않고 항상 새로운 메시지로 게시

## 라이선스

MIT

