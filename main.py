"""디스코드 봇 메인 파일"""
from datetime import datetime
from io import BytesIO
from typing import Optional

import discord
from discord import app_commands
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import structlog

from config import Config
from calendar_service import CalendarService
from image_generator import CalendarImageGenerator

# 로깅 설정
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer()
    ]
)
logger = structlog.get_logger()

# 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True

# 봇 클라이언트
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# 서비스 인스턴스
calendar_service: Optional[CalendarService] = None
image_generator: Optional[CalendarImageGenerator] = None

# 스케줄러
scheduler: Optional[AsyncIOScheduler] = None

# 캘린더 변경사항 추적용
last_calendar_etag: Optional[str] = None


@bot.event
async def on_ready():
    """봇이 준비되었을 때 실행"""
    global calendar_service, image_generator, scheduler
    
    logger.info("디스코드 봇 시작", bot_name=bot.user.name if bot.user else "Unknown")
    
    # 서비스 초기화
    try:
        calendar_service = CalendarService()
        image_generator = CalendarImageGenerator()
        logger.info("서비스 초기화 완료")
    except Exception as e:
        logger.error("서비스 초기화 실패", error=str(e))
        await bot.close()
        return
    
    # 슬래시 커맨드 동기화
    try:
        synced = await tree.sync()
        logger.info("슬래시 커맨드 동기화 완료", count=len(synced))
    except Exception as e:
        logger.error("슬래시 커맨드 동기화 실패", error=str(e))
    
    # 스케줄러 시작
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_calendar_updates,
        IntervalTrigger(minutes=Config.CALENDAR_CHECK_INTERVAL),
        id='calendar_check',
        replace_existing=True
    )
    scheduler.start()
    logger.info("스케줄러 시작", interval_minutes=Config.CALENDAR_CHECK_INTERVAL)
    
    # 초기 캘린더 이미지 게시
    await post_calendar_image()


@tree.command(name="일정", description="현재 달의 캘린더 이미지를 게시합니다")
async def schedule_command(interaction: discord.Interaction):
    """일정 슬래시 커맨드"""
    await interaction.response.defer()
    
    try:
        await post_calendar_image(interaction=interaction)
        logger.info("슬래시 커맨드 실행 완료", user=interaction.user.name)
    except Exception as e:
        logger.error("슬래시 커맨드 실행 실패", error=str(e))
        if not interaction.response.is_done():
            await interaction.followup.send(
                f"❌ 캘린더 이미지 생성 중 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )


async def post_calendar_image(interaction: Optional[discord.Interaction] = None):
    """
    캘린더 이미지를 생성하고 디스코드 채널에 새 메시지로 게시합니다.
    
    Args:
        interaction: 디스코드 인터랙션 (슬래시 커맨드용)
    """
    try:
        channel = bot.get_channel(Config.DISCORD_CHANNEL_ID)
        if not channel:
            logger.error("채널을 찾을 수 없음", channel_id=Config.DISCORD_CHANNEL_ID)
            if interaction:
                await interaction.followup.send(
                    "❌ 채널을 찾을 수 없습니다.",
                    ephemeral=True
                )
            return
        
        # 현재 날짜
        now = datetime.now()
        year = now.year
        month = now.month
        
        logger.info("캘린더 이미지 생성 시작", year=year, month=month)
        
        # 이벤트 가져오기
        events = calendar_service.get_events_for_month(year, month)
        
        # 이미지 생성
        image = image_generator.generate_month_image(year, month, events)
        
        # 이미지를 바이트로 변환
        img_bytes = BytesIO()
        image.save(img_bytes, format='PNG')
        img_bytes.seek(0)
        
        # 디스코드 파일 객체 생성
        file = discord.File(img_bytes, filename=f"calendar_{year}_{month:02d}.png")
        
        # 메시지 전송
        embed = discord.Embed(
            title=f"{year}년 {month}월 일정",
            description=f"총 {len(events)}개의 이벤트",
            color=discord.Color.blue()
        )
        embed.set_image(url=f"attachment://calendar_{year}_{month:02d}.png")
        embed.timestamp = datetime.now()
        
        # 항상 새 메시지로 게시
        message = await channel.send(embed=embed, file=file)
        logger.info("새 메시지 게시 완료", message_id=message.id)
        
        if interaction:
            await interaction.followup.send(
                "✅ 캘린더 이미지가 게시되었습니다!",
                ephemeral=True
            )
        
    except Exception as e:
        logger.error("캘린더 이미지 게시 실패", error=str(e))
        if interaction:
            await interaction.followup.send(
                f"❌ 오류가 발생했습니다: {str(e)}",
                ephemeral=True
            )


async def check_calendar_updates():
    """캘린더 변경사항을 체크하고 업데이트합니다"""
    global last_calendar_etag
    
    try:
        logger.info("캘린더 변경사항 체크 시작")
        
        # ETag로 변경 감지 시도
        current_etag = calendar_service.get_calendar_etag()
        
        if current_etag and last_calendar_etag:
            if current_etag == last_calendar_etag:
                logger.info("캘린더 변경사항 없음")
                return
        
        # ETag가 변경되었거나 처음 실행인 경우 이미지 업데이트
        logger.info("캘린더 변경사항 감지, 이미지 업데이트 시작")
        last_calendar_etag = current_etag
        await post_calendar_image()
        
    except Exception as e:
        logger.error("캘린더 변경사항 체크 실패", error=str(e))


def main():
    """메인 함수"""
    try:
        # 설정 검증
        Config.validate()
        logger.info("설정 검증 완료")
        
        # 봇 실행
        bot.run(Config.DISCORD_BOT_TOKEN)
    except ValueError as e:
        logger.error("설정 오류", error=str(e))
        print(f"\n❌ 설정 오류: {e}\n")
        print(".env 파일을 확인하고 필요한 값들을 설정해주세요.")
    except Exception as e:
        logger.error("봇 실행 실패", error=str(e))
        raise


if __name__ == "__main__":
    main()

