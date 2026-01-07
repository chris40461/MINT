# 참고: docs/backend/08-notification.md

"""
텔레그램 알림 서비스

오전/오후 리포트 및 급등 조짐 알림을 텔레그램으로 전송합니다.
웹 리포트와 동일한 상세 정보를 포함합니다.
"""

import logging
import html
from typing import Dict, List, Optional
from datetime import datetime

from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

from app.core.config import settings

logger = logging.getLogger(__name__)


def escape(text: str) -> str:
    """HTML 특수문자 이스케이프"""
    if not text:
        return ''
    return html.escape(str(text))


class NotificationService:
    """텔레그램 알림 서비스"""

    def __init__(self):
        """서비스 초기화"""
        self.enabled = settings.TELEGRAM_ENABLED
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID

        if self.enabled and self.bot_token:
            self.bot = Bot(token=self.bot_token)
            logger.info("NotificationService 초기화 완료 (Telegram)")
        else:
            self.bot = None
            logger.warning("NotificationService 비활성화 (TELEGRAM_ENABLED=False 또는 토큰 없음)")

    async def send_message(self, text: str, parse_mode: str = ParseMode.HTML) -> bool:
        """텔레그램 메시지 전송"""
        if not self.enabled or not self.bot:
            logger.warning("텔레그램 알림 비활성화 상태")
            return False

        try:
            # 텔레그램 메시지 길이 제한 (4096자)
            if len(text) > 4096:
                chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
                for chunk in chunks:
                    await self.bot.send_message(
                        chat_id=self.chat_id,
                        text=chunk,
                        parse_mode=parse_mode
                    )
            else:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=text,
                    parse_mode=parse_mode
                )
            logger.info("텔레그램 메시지 전송 완료")
            return True

        except TelegramError as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")
            return False

    async def send_morning_report(self, report: Dict) -> bool:
        """
        오전 리포트 전송 (웹과 동일한 상세 정보)
        """
        try:
            date = report.get('date', datetime.now().strftime('%Y-%m-%d'))

            # ═══════════════════ 헤더 ═══════════════════
            message = f"""
<b>🌅 MINT 장 시작 리포트</b>

📅 <code>{date}</code>

"""
            # ═══════════════════ 시장 전망 ═══════════════════
            market_forecast = report.get('market_forecast', '')
            if market_forecast:
                message += f"""<b>📊 시장 전망</b>
{escape(market_forecast)}

"""
            # ═══════════════════ KOSPI 예상 범위 ═══════════════════
            kospi_range = report.get('kospi_range', {})
            if kospi_range:
                low = kospi_range.get('low', 0)
                high = kospi_range.get('high', 0)
                reasoning = kospi_range.get('reasoning', '')

                message += f"""<b>📈 KOSPI 예상 범위</b>
🔻 하단: <code>{low:,.0f}</code>  🔺 상단: <code>{high:,.0f}</code>
"""
                if reasoning:
                    message += f"💡 {escape(reasoning)}\n"
                message += "\n"

            # ═══════════════════ 시장 리스크 ═══════════════════
            market_risks = report.get('market_risks', [])
            if market_risks:
                message += "<b>⚠️ 시장 리스크</b>\n"
                for risk in market_risks[:5]:
                    message += f"• {escape(risk)}\n"
                message += "\n"

            # ═══════════════════ 섹터 분석 ═══════════════════
            sector_analysis = report.get('sector_analysis', {})
            bullish = sector_analysis.get('bullish', [])
            bearish = sector_analysis.get('bearish', [])

            if bullish or bearish:
                message += "<b>🏭 섹터 분석</b>\n"
                if bullish:
                    message += "📈 <b>유망 섹터</b>\n"
                    for item in bullish[:3]:
                        if isinstance(item, dict):
                            sector = item.get('sector', '')
                            reason = item.get('reason', '')
                            message += f"  • <b>{escape(sector)}</b>\n    └ {escape(reason)}\n"
                        else:
                            message += f"  • {escape(str(item))}\n"
                if bearish:
                    message += "📉 <b>주의 섹터</b>\n"
                    for item in bearish[:3]:
                        if isinstance(item, dict):
                            sector = item.get('sector', '')
                            reason = item.get('reason', '')
                            message += f"  • <b>{escape(sector)}</b>\n    └ {escape(reason)}\n"
                        else:
                            message += f"  • {escape(str(item))}\n"
                message += "\n"

            # ═══════════════════ 주목 종목 Top 10 ═══════════════════
            top_stocks = report.get('top_stocks', [])
            if top_stocks:
                message += """<b>🔥 오늘의 주목 종목 Top 10</b>

"""
                for stock in top_stocks[:10]:
                    rank = stock.get('rank', '-')
                    name = escape(stock.get('name', 'N/A'))
                    ticker = escape(stock.get('ticker', 'N/A'))
                    current_price = stock.get('current_price', 0)
                    score = stock.get('score', 0)
                    reason = escape(stock.get('reason', ''))
                    entry_strategy = stock.get('entry_strategy', {}) or {}

                    # 순위 이모지
                    rank_emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"<b>{rank}.</b>"

                    message += f"""
{rank_emoji} <b>{name}</b> ({ticker})
├ 💰 현재가: <code>{current_price:,}원</code>
├ ⭐ 점수: <code>{score:.1f}</code>
├ 📝 {reason}
"""
                    if entry_strategy:
                        target1 = entry_strategy.get('target_price_1', 0)
                        target2 = entry_strategy.get('target_price_2', 0)
                        stop = entry_strategy.get('stop_loss', 0)
                        timing = escape(entry_strategy.get('entry_timing', ''))
                        confidence = entry_strategy.get('confidence', 0)

                        if target1 and stop:
                            message += f"├ 🎯 목표1: <code>{target1:,}</code> / 목표2: <code>{target2:,}</code>\n"
                            message += f"├ 🛑 손절: <code>{stop:,}</code>\n"
                        if timing:
                            message += f"├ ⏰ {timing}\n"
                        if confidence:
                            conf_emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.7 else "🟠"
                            message += f"└ {conf_emoji} 신뢰도: <code>{confidence*100:.0f}%</code>\n"

            # ═══════════════════ 투자 전략 ═══════════════════
            strategy = report.get('investment_strategy', '')
            if strategy:
                message += f"""
<b>💡 오늘의 투자 전략</b>

{escape(strategy)}

"""
            # ═══════════════════ 일정 ═══════════════════
            daily_schedule = report.get('daily_schedule', {})
            if daily_schedule:
                message += "<b>📆 오늘의 매매 일정</b>\n"
                for time_slot, event in list(daily_schedule.items())[:4]:
                    time_display = time_slot.replace('_', ' ~ ')
                    message += f"⏰ <b>{escape(time_display)}</b>\n"
                    message += f"   {escape(event)}\n"
                message += "\n"

            # ═══════════════════ 푸터 ═══════════════════
            message += """
<i>🤖 MINT AI Report</i>
<i>⚠️ 투자 판단은 본인 책임입니다</i>
"""
            return await self.send_message(message)

        except Exception as e:
            logger.error(f"오전 리포트 전송 실패: {e}", exc_info=True)
            return False

    async def send_afternoon_report(self, report: Dict) -> bool:
        """
        오후 리포트 전송 (웹과 동일한 상세 정보)
        """
        try:
            date = report.get('date', datetime.now().strftime('%Y-%m-%d'))
            market_summary = report.get('market_summary', {})

            # ═══════════════════ 헤더 ═══════════════════
            message = f"""
<b>🌆 MINT 장 마감 리포트</b>

📅 <code>{date}</code>

"""
            # ═══════════════════ 지수 동향 ═══════════════════
            kospi_close = market_summary.get('kospi_close', 0)
            kospi_change = market_summary.get('kospi_change', 0)
            kospi_point = market_summary.get('kospi_point_change', 0)
            kosdaq_close = market_summary.get('kosdaq_close', 0)
            kosdaq_change = market_summary.get('kosdaq_change', 0)
            kosdaq_point = market_summary.get('kosdaq_point_change', 0)

            kospi_emoji = "📈" if kospi_change >= 0 else "📉"
            kosdaq_emoji = "📈" if kosdaq_change >= 0 else "📉"

            message += f"""<b>📊 지수 동향</b>
{kospi_emoji} <b>KOSPI</b>: <code>{kospi_close:,.2f}</code> ({kospi_change:+.2f}% / {kospi_point:+.2f}p)
{kosdaq_emoji} <b>KOSDAQ</b>: <code>{kosdaq_close:,.2f}</code> ({kosdaq_change:+.2f}% / {kosdaq_point:+.2f}p)

"""
            # ═══════════════════ 시장 폭 ═══════════════════
            advance = market_summary.get('advance_count', 0)
            decline = market_summary.get('decline_count', 0)
            unchanged = market_summary.get('unchanged_count', 0)
            market_breadth = report.get('market_breadth', {})

            if advance or decline:
                total = advance + decline + unchanged
                message += f"""<b>📊 시장 폭 (Market Breadth)</b>
🟢 상승: <code>{advance:,}</code>  🔴 하락: <code>{decline:,}</code>  ⚪ 보합: <code>{unchanged:,}</code>
"""
                if market_breadth:
                    sentiment = market_breadth.get('sentiment', '')
                    interpretation = market_breadth.get('interpretation', '')
                    message += f"📍 <b>{escape(sentiment)}</b>: {escape(interpretation)}\n"
                message += "\n"

            # ═══════════════════ 수급 동향 ═══════════════════
            foreign_kospi = market_summary.get('foreign_net_kospi', 0)
            institution_kospi = market_summary.get('institution_net_kospi', 0)
            individual_kospi = market_summary.get('individual_net_kospi', 0)
            foreign_kosdaq = market_summary.get('foreign_net_kosdaq', 0)
            institution_kosdaq = market_summary.get('institution_net_kosdaq', 0)
            individual_kosdaq = market_summary.get('individual_net_kosdaq', 0)

            def supply_emoji(val):
                return "🔵" if val >= 0 else "🔴"

            message += f"""<b>💰 수급 동향 (억원)</b>
<code>구분        KOSPI      KOSDAQ</code>
<code>외국인  {supply_emoji(foreign_kospi)}{foreign_kospi:>+8,}  {supply_emoji(foreign_kosdaq)}{foreign_kosdaq:>+8,}</code>
<code>기관    {supply_emoji(institution_kospi)}{institution_kospi:>+8,}  {supply_emoji(institution_kosdaq)}{institution_kosdaq:>+8,}</code>
<code>개인    {supply_emoji(individual_kospi)}{individual_kospi:>+8,}  {supply_emoji(individual_kosdaq)}{individual_kosdaq:>+8,}</code>

"""
            # ═══════════════════ 시장 요약 ═══════════════════
            summary_text = report.get('market_summary_text', '')
            if summary_text:
                message += f"""<b>📋 시장 요약</b>
{escape(summary_text)}

"""
            # ═══════════════════ 수급 분석 ═══════════════════
            supply_demand = report.get('supply_demand_analysis', '')
            if supply_demand:
                message += f"""<b>💹 수급 분석</b>
{escape(supply_demand)}

"""
            # ═══════════════════ 섹터 분석 ═══════════════════
            sector_analysis = report.get('sector_analysis', {})
            bullish = sector_analysis.get('bullish', [])
            bearish = sector_analysis.get('bearish', [])

            if bullish or bearish:
                message += "<b>🏭 섹터 분석</b>\n"
                if bullish:
                    message += "📈 <b>강세 섹터</b>\n"
                    for item in bullish[:3]:
                        if isinstance(item, dict):
                            sector = item.get('sector', '')
                            change = item.get('change', '')
                            reason = item.get('reason', '')
                            message += f"  • <b>{escape(sector)}</b> {escape(change)}\n    └ {escape(reason)}\n"
                        else:
                            message += f"  • {escape(str(item))}\n"
                if bearish:
                    message += "📉 <b>약세 섹터</b>\n"
                    for item in bearish[:3]:
                        if isinstance(item, dict):
                            sector = item.get('sector', '')
                            change = item.get('change', '')
                            reason = item.get('reason', '')
                            message += f"  • <b>{escape(sector)}</b> {escape(change)}\n    └ {escape(reason)}\n"
                        else:
                            message += f"  • {escape(str(item))}\n"
                message += "\n"

            # ═══════════════════ 오늘의 테마 ═══════════════════
            today_themes = report.get('today_themes', [])
            if today_themes:
                message += "<b>🏷️ 오늘의 테마</b>\n"
                for theme in today_themes[:4]:
                    if isinstance(theme, dict):
                        theme_name = theme.get('theme', '')
                        drivers = theme.get('drivers', '')
                        leading_stocks = theme.get('leading_stocks', [])
                        stocks_str = ', '.join(leading_stocks[:3]) if leading_stocks else ''
                        message += f"🔹 <b>{escape(theme_name)}</b>\n"
                        if drivers:
                            message += f"   {escape(drivers)}\n"
                        if stocks_str:
                            message += f"   📌 대장주: {escape(stocks_str)}\n"
                    else:
                        message += f"🔹 {escape(str(theme))}\n"
                message += "\n"

            # ═══════════════════ 급등주 분석 ═══════════════════
            surge_analysis = report.get('surge_analysis', [])
            if surge_analysis:
                message += """<b>🚀 오늘의 급등주 분석</b>

"""
                for i, stock in enumerate(surge_analysis[:5], 1):
                    name = escape(stock.get('name', 'N/A'))
                    ticker = escape(stock.get('ticker', 'N/A'))
                    category = escape(stock.get('category', ''))
                    reason = escape(stock.get('reason', ''))
                    outlook = escape(stock.get('outlook', ''))
                    change_rate = stock.get('change_rate', 0)

                    message += f"""
<b>{i}. {name}</b> ({ticker})
├ 🏷️ {category}
├ 📝 {reason}
"""
                    if outlook:
                        message += f"└ 🔮 {outlook}\n"

            # ═══════════════════ 체크포인트 ═══════════════════
            check_points = report.get('check_points', [])
            if check_points:
                message += "\n<b>✅ 내일 체크포인트</b>\n"
                for point in check_points[:5]:
                    message += f"• {escape(point)}\n"
                message += "\n"

            # ═══════════════════ 내일 전략 ═══════════════════
            tomorrow_strategy = report.get('tomorrow_strategy', '')
            if tomorrow_strategy:
                message += f"""<b>💡 내일 투자 전략</b>

{escape(tomorrow_strategy)}

"""
            # ═══════════════════ 푸터 ═══════════════════
            message += """
<i>🤖 MINT AI Report</i>
<i>⚠️ 투자 판단은 본인 책임입니다</i>
"""
            return await self.send_message(message)

        except Exception as e:
            logger.error(f"오후 리포트 전송 실패: {e}", exc_info=True)
            return False

    async def send_pre_surge_alert(self, signals: List[Dict]) -> bool:
        """급등 조짐 알림 전송"""
        if not signals:
            return True

        try:
            now = datetime.now().strftime('%H:%M')

            message = f"""
<b>🚨 급등 조짐 감지</b>

🕐 {now}

"""
            for i, signal in enumerate(signals[:5], 1):
                name = escape(signal.get('name', 'N/A'))
                ticker = escape(signal.get('ticker', 'N/A'))
                volume_ratio = signal.get('volume_ratio', 0)
                change_rate = signal.get('change_rate', 0)
                current_price = signal.get('current_price', 0)
                confidence = signal.get('confidence', 0)

                conf_emoji = "🔴" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🟢"

                message += f"""<b>{i}. {name}</b> ({ticker})
├ 💰 현재가: <code>{current_price:,}원</code>
├ 📊 등락률: <code>{change_rate:+.2f}%</code>
├ 📈 거래량: 평균 대비 <b>{volume_ratio:.1f}배</b>
└ {conf_emoji} 신뢰도: <code>{confidence*100:.0f}%</code>

"""
            message += """
<i>💡 거래량 급증 + 가격 미동 = 매집 신호</i>
<i>🤖 MINT Pre-Surge Detector</i>
"""
            return await self.send_message(message)

        except Exception as e:
            logger.error(f"조짐 알림 전송 실패: {e}")
            return False

    async def send_custom_alert(self, title: str, content: str) -> bool:
        """커스텀 알림 전송"""
        message = f"""
<b>🔔 {escape(title)}</b>


{escape(content)}

<i>🤖 MINT Alert</i>
"""
        return await self.send_message(message)


# 전역 인스턴스
notification_service = NotificationService()
