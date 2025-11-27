"""refactored_calendar_image.py
리팩토링된 캘린더 이미지 생성 모듈
- 모든 날짜 연산은 datetime.date로 통일
- calendar.monthdatescalendar로 주(row) 단위 날짜 배열 생성 (1일 누락 버그 해결)
- multi-day 이벤트는 주 단위로 분할(segment)하여 가로로 span 그리기 (셀 병합 스타일)
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import calendar
import structlog
import os

from config import Config

logger = structlog.get_logger()


def _to_date(obj) -> date:
    """입력값(event start/end)이 datetime/date/iso-string일 수 있으므로 date로 변환."""
    if isinstance(obj, date) and not isinstance(obj, datetime):
        return obj
    if isinstance(obj, datetime):
        return obj.date()
    if isinstance(obj, str):
        # 날짜만 있는 경우: YYYY-MM-DD, 또는 datetime ISO 형식 처리 시도
        try:
            # 먼저 date-only
            return date.fromisoformat(obj)
        except Exception:
            try:
                # datetime 형태일 수 있음
                return datetime.fromisoformat(obj).date()
            except Exception:
                raise ValueError(f"Unsupported date string format: {obj!r}")
    raise TypeError(f"Unsupported date/datetime type: {type(obj)}")


class CalendarImageGenerator:
    """캘린더 이미지 생성 클래스 (리팩토링 버전)"""

    def __init__(self):
        self.width = Config.IMAGE_WIDTH
        self.height = Config.IMAGE_HEIGHT
        self.bg_color = self._hex_to_rgb(Config.BACKGROUND_COLOR)
        self.text_color = self._hex_to_rgb(Config.TEXT_COLOR)
        self.header_color = self._hex_to_rgb(Config.HEADER_COLOR)

        # 색상 정의
        self.title_color = self._hex_to_rgb("#4A4A4A")
        self.weekday_header_bg = self._hex_to_rgb("#EAEAE0")
        self.weekday_sun_color = self._hex_to_rgb("#C16A64")
        self.weekday_sat_color = self._hex_to_rgb("#5188B7")
        self.weekday_normal_color = self._hex_to_rgb("#4B4B4A")
        self.row_divider_color = self._hex_to_rgb("#EAEAE0")

        # 폰트 설정 (월 60, 년 20 등)
        self.month_font = self._load_font("MaruBuri-Bold.ttf", 60, fallback_size=60)
        self.year_font = self._load_font("MaruBuri-Bold.ttf", 20, fallback_size=20)
        self.header_font = self._load_font("MaruBuri-SemiBold.ttf", 20, fallback_size=24)
        self.day_font = self._load_font("MaruBuri-SemiBold.ttf", 20, fallback_size=18)
        self.event_font = self._load_font("MaruBuri-SemiBold.ttf", 18, fallback_size=14)

    def _load_font(self, font_name: str, size: int, fallback_size: int) -> ImageFont.FreeTypeFont:
        font_paths = [
            font_name,
            os.path.join("fonts", font_name),
            os.path.join("assets", "fonts", font_name),
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    try:
                        font = ImageFont.truetype(font_path, size, encoding='unic')
                        logger.info("폰트 로드 성공 (unic)", path=font_path, size=size)
                    except (TypeError, ValueError):
                        font = ImageFont.truetype(font_path, size)
                        logger.info("폰트 로드 성공 (기본)", path=font_path, size=size)
                    return font
                except Exception as e:
                    logger.warning("폰트 로드 실패", path=font_path, error=str(e))
                    continue
        raise FileNotFoundError(f"폰트 파일을 찾을 수 없습니다: {font_name}")

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _draw_rounded_rectangle(
        self,
        draw: ImageDraw.Draw,
        xy: tuple,
        fill: Optional[tuple] = None,
        outline: Optional[tuple] = None,
        radius: int = 14
    ):
        try:
            if hasattr(draw, 'rounded_rectangle'):
                draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline)
            else:
                draw.rectangle(xy, fill=fill, outline=outline)
        except Exception as e:
            logger.warning("rounded_rectangle 그리기 실패, 일반 사각형으로 폴백", error=str(e))
            draw.rectangle(xy, fill=fill, outline=outline)

    def _prepare_events(self, events: List[Dict], year: int, month: int) -> List[Dict]:
        """이벤트 리스트의 start/end를 date로 정규화하고, 해당 월에 겹치는 이벤트만 필터링"""
        first_of_month = date(year, month, 1)
        if month == 12:
            first_next_month = date(year + 1, 1, 1)
        else:
            first_next_month = date(year, month + 1, 1)
        last_of_month = first_next_month - timedelta(days=1)

        prepared = []
        for ev in events:
            # 기대 형식: ev['summary'], ev['start'], ev['end'], optional ev['color_id']
            try:
                s = _to_date(ev.get('start'))
                e = _to_date(ev.get('end'))
            except Exception as exc:
                logger.warning("이벤트 날짜 파싱 실패, 건너뜀", error=str(exc), event_data=ev)
                continue

            # Google calendar에서 end는 통상 비포함(end date is exclusive for all-day events).
            # 사용자가 제공한 데이터가 exclusive인지 inclusive인지 불확실하므로
            # 만약 end == start: treat as single day. 만약 end > start: assume end is exclusive for all-day -> subtract 1 day.
            # (여기서는 일반적인 Google API 규칙을 따름: all-day event end is exclusive)
            # 만약 end > start and ev was all-day -> convert to inclusive end by -1
            # Heuristic: if event has zero time info we can't detect; we assume end is exclusive if end > start.
            if e > s:
                # assume exclusive -> inclusive
                e_inclusive = e - timedelta(days=1)
            else:
                e_inclusive = e

            # Clip to this month
            ev_start = max(s, first_of_month)
            ev_end = min(e_inclusive, last_of_month)

            if ev_start <= last_of_month and ev_end >= first_of_month:
                prepared.append({
                    'summary': ev.get('summary', '(No title)'),
                    'start_date': ev_start,
                    'end_date': ev_end,
                    'color_id': ev.get('color_id')
                })
        return prepared

    def generate_month_image(
        self,
        year: int,
        month: int,
        events: List[Dict]
    ) -> Image.Image:
        logger.info("이미지 생성 시작", year=year, month=month, event_count=len(events))

        bg_rgb = self._hex_to_rgb("#FDFEF0")
        img = Image.new('RGB', (self.width, self.height), bg_rgb)
        draw = ImageDraw.Draw(img)

        # 제목(월/년)
        if Config.TITLE_FORMAT == "english":
            month_text = datetime(year, month, 1).strftime('%B')
            year_text = str(year)
        else:
            month_text = f"{month}월"
            year_text = f"{year}년"

        title_x = 80
        title_y = 40
        month_bbox = draw.textbbox((0, 0), month_text, font=self.month_font)
        draw.text((title_x, title_y), month_text, fill=self.title_color, font=self.month_font)
        year_x = title_x + (month_bbox[2] - month_bbox[0]) + 10
        year_y = title_y + (month_bbox[3] - month_bbox[1]) - 20
        draw.text((year_x, year_y), year_text, fill=self.title_color, font=self.year_font)

        # 그리드 계산
        grid_start_y = title_y + 80
        grid_height = self.height - grid_start_y - 40
        grid_width = self.width - 80
        grid_x = 40

        weekdays = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
        day_width = grid_width // 7
        header_height = 50

        # 요일 헤더 배경
        header_radius = 8
        self._draw_rounded_rectangle(
            draw, (grid_x, grid_start_y, grid_x + grid_width, grid_start_y + header_height),
            fill=self.weekday_header_bg, outline=None, radius=header_radius
        )
        # 요일 텍스트
        for i, day in enumerate(weekdays):
            x = grid_x + i * day_width + day_width // 2
            day_bbox = draw.textbbox((0, 0), day, font=self.header_font)
            day_text_width = day_bbox[2] - day_bbox[0]
            day_x = x - day_text_width // 2
            if day == 'SUN':
                day_color = self.weekday_sun_color
            elif day == 'SAT':
                day_color = self.weekday_sat_color
            else:
                day_color = self.weekday_normal_color
            draw.text((day_x, grid_start_y + header_height // 2 - 12), day, fill=day_color, font=self.header_font)

        # 달력의 주별 날짜 배열 (each week is list of 7 date objects)
        cal = calendar.Calendar(firstweekday=6)  # 일요일 시작
        month_weeks = cal.monthdatescalendar(year, month)  # date objects, includes prev/next month dates
        max_weeks = len(month_weeks)  # 보통 5 또는 6

        calendar_start_y = grid_start_y + header_height + 10
        cell_height = (grid_height - header_height - 10) // max(6, max_weeks)  # 여유두기

        # 이벤트 전처리 (date로 정규화, 월 범위로 클리핑)
        prepared_events = self._prepare_events(events, year, month)

        # 주별로 이벤트 세그먼트 생성: 각 이벤트를 week-row 단위로 분할
        # week_segments[week_index] = list of segments {start_col, span, slot, summary, color_id}
        week_segments: List[List[Dict]] = [[] for _ in range(max_weeks)]

        def find_slot(segments_for_week, start_col, end_col, max_slots=3):
            """주 내에서 겹치지 않는 슬롯(수직 index)을 찾아 반환. 없으면 None."""
            for slot in range(max_slots):
                overlap = False
                for seg in segments_for_week:
                    if seg['slot'] != slot:
                        continue
                    # 겹침 검사: [a,b]와 [c,d]가 겹치면 True
                    if not (end_col < seg['start_col'] or start_col > seg['end_col']):
                        overlap = True
                        break
                if not overlap:
                    return slot
            return None

        # build segments
        for ev in prepared_events:
            ev_s = ev['start_date']
            ev_e = ev['end_date']
            # iterate weeks to see overlap
            for wi, week in enumerate(month_weeks):
                week_start = week[0]  # sunday
                week_end = week[-1]   # saturday
                # overlap?
                seg_start = max(ev_s, week_start)
                seg_end = min(ev_e, week_end)
                if seg_start <= seg_end:
                    # compute start_col and span within this week
                    start_col = (seg_start - week_start).days  # 0..6
                    span = (seg_end - seg_start).days + 1
                    end_col = start_col + span - 1
                    # find free slot
                    slot = find_slot(week_segments[wi], start_col, end_col, max_slots=3)
                    if slot is None:
                        # 만약 슬롯 부족하면 마지막 슬롯에 겹치게 넣지 않고 무시하거나 +n으로 표시.
                        # 여기서는 무시(레이아웃 안정성 우선)
                        logger.info("주별 슬롯 부족: 이벤트 일부 생략", week=wi, event_summary=ev.get('summary'))
                        continue
                    week_segments[wi].append({
                        'start_col': start_col,
                        'end_col': end_col,
                        'span': span,
                        'slot': slot,
                        'summary': ev['summary'],
                        'color_id': ev.get('color_id')
                    })

        # 그리기: 각 주(row)와 각 일자 셀 그리기 + 이벤트 세그먼트 렌더
        for wi, week in enumerate(month_weeks):
            # row 구분선
            row_top = calendar_start_y + wi * cell_height
            if wi > 0:
                draw.line([(grid_x, row_top), (grid_x + grid_width, row_top)],
                          fill=self.row_divider_color, width=1)

            for di, cell_date in enumerate(week):
                cell_x = grid_x + di * day_width
                cell_y = calendar_start_y + wi * cell_height
                # 표시할 달(현재 month인지) 판단
                is_current_month = (cell_date.month == month and cell_date.year == year)
                if is_current_month:
                    date_str = str(cell_date.day)
                    date_x = cell_x + 8
                    date_y = cell_y + 8
                    # weekday color: weekday() Mon=0..Sun=6 -> convert
                    wd = cell_date.weekday()  # Mon=0..Sun=6
                    if wd == 6:  # Sunday
                        date_color = self.weekday_sun_color
                    elif wd == 5:  # Saturday
                        date_color = self.weekday_sat_color
                    else:
                        date_color = self.weekday_normal_color
                    draw.text((date_x, date_y), date_str, fill=date_color, font=self.day_font)
                else:
                    # 다른 달 날짜는 연하게 처리(선택사항)
                    date_str = str(cell_date.day)
                    date_x = cell_x + 8
                    date_y = cell_y + 8
                    draw.text((date_x, date_y), date_str, fill=(200, 200, 200), font=self.day_font)

            # 이 주에 해당하는 이벤트 세그먼트 그리기
            for seg in week_segments[wi]:
                start_col = seg['start_col']
                end_col = seg['end_col']
                slot = seg['slot']
                summary = seg['summary']
                color_id = seg.get('color_id')

                # pill 위치 계산
                padding_x = 6
                padding_y = 6
                pill_top = (calendar_start_y + wi * cell_height) + 32 + slot * 34  # slot별 세로 오프셋
                pill_bottom = pill_top + 28
                pill_left = grid_x + start_col * day_width + padding_x
                pill_right = grid_x + (end_col + 1) * day_width - padding_x

                # 색상 매핑 (기본 파스텔)
                event_color = (220, 220, 240)
                if color_id:
                    cmap = {
                        '1': (230, 220, 250), '2': (255, 220, 200), '3': (200, 230, 255),
                        '4': (255, 240, 200), '5': (240, 220, 250), '6': (255, 220, 210),
                        '7': (220, 250, 220), '8': (250, 200, 220), '9': (230, 230, 240),
                        '10': (220, 240, 200), '11': (255, 220, 200),
                    }
                    event_color = cmap.get(str(color_id), event_color)

                # 너무 좁으면 최소 너비 보장
                min_width = 40
                if pill_right - pill_left < min_width:
                    center = (pill_left + pill_right) // 2
                    pill_left = center - min_width // 2
                    pill_right = center + min_width // 2

                # 그리기
                self._draw_rounded_rectangle(draw, (pill_left, pill_top, pill_right, pill_bottom),
                                             fill=event_color, outline=None, radius=12)

                # 텍스트: 요약을 잘라서 중앙 정렬
                text = summary
                max_chars = 20
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + "..."
                tb = draw.textbbox((0, 0), text, font=self.event_font)
                text_w = tb[2] - tb[0]
                text_h = tb[3] - tb[1]
                text_x = pill_left + (pill_right - pill_left - text_w) // 2
                text_y = pill_top + ( (pill_bottom - pill_top - text_h) // 2 )
                draw.text((text_x, text_y), text, fill=self.weekday_normal_color, font=self.event_font)

            # 주당 이벤트 +N 표시 (선택 기능): 슬롯 부족으로 생략된 이벤트을 추적하려면 로직 추가 필요

        # 마지막 row 구분선
        last_line_y = calendar_start_y + max_weeks * cell_height
        draw.line([(grid_x, last_line_y), (grid_x + grid_width, last_line_y)],
                  fill=self.row_divider_color, width=1)

        logger.info("이미지 생성 완료", year=year, month=month)
        return img

    def save_image(self, image: Image.Image, filepath: str) -> str:
        image.save(filepath, 'PNG', optimize=True)
        logger.info("이미지 저장 완료", filepath=filepath)
        return filepath
