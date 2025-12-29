"""
LLM 서비스 공통 유틸리티

RateLimiter, CostTracker, 예외 클래스 등 LLM 서비스에서 공통으로 사용하는 컴포넌트
"""

import logging
import asyncio
from datetime import datetime, timedelta
from collections import deque

logger = logging.getLogger(__name__)


# ============= 예외 클래스 =============

class LLMAPIError(Exception):
    """LLM API 호출 중 일반 에러"""
    pass


class LLMRateLimitError(Exception):
    """LLM API Rate Limit 에러"""
    pass


# ============= Rate Limiter =============

class RateLimiter:
    """
    Rate Limiting 관리 클래스

    Gemini API 호출 제한을 관리하여 과도한 요청 방지
    """

    def __init__(self, max_requests: int, time_window: int):
        """
        Args:
            max_requests: 최대 요청 수
            time_window: 시간 윈도우 (초)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Rate limit 체크 및 대기"""
        async with self.lock:
            now = datetime.now()

            # 오래된 요청 제거
            while self.requests:
                if (now - self.requests[0]) > timedelta(seconds=self.time_window):
                    self.requests.popleft()
                else:
                    break

            # Rate limit 체크
            if len(self.requests) >= self.max_requests:
                # 대기 시간 계산
                oldest_request = self.requests[0]
                wait_until = oldest_request + timedelta(seconds=self.time_window)
                wait_seconds = (wait_until - now).total_seconds()

                if wait_seconds > 0:
                    logger.warning(f"Rate limit reached, waiting {wait_seconds:.1f}s")
                    await asyncio.sleep(wait_seconds)

            # 요청 기록
            self.requests.append(now)


# ============= Cost Tracker =============

class CostTracker:
    """
    LLM 비용 추적 클래스

    토큰 사용량 및 예상 비용을 모니터링
    """

    # Gemini 2.5 Pro 가격 (2025년 기준)
    # 출처: https://ai.google.dev/pricing
    # Input: $0.075 / 1M tokens = $0.000075 / 1K tokens
    # Output: $0.30 / 1M tokens = $0.0003 / 1K tokens
    INPUT_COST_PER_1K = 0.000075  # $0.075 / 1M tokens
    OUTPUT_COST_PER_1K = 0.0003  # $0.30 / 1M tokens

    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0

    def record_usage(self, input_tokens: int, output_tokens: int):
        """토큰 사용량 기록"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens

    def get_total_cost(self) -> float:
        """총 비용 계산 (USD)"""
        input_cost = (self.total_input_tokens / 1000) * self.INPUT_COST_PER_1K
        output_cost = (self.total_output_tokens / 1000) * self.OUTPUT_COST_PER_1K
        return input_cost + output_cost

    def get_daily_report(self) -> dict:
        """일일 사용량 리포트"""
        return {
            "date": datetime.now().date().isoformat(),
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "total_cost_usd": self.get_total_cost(),
            "total_cost_krw": self.get_total_cost() * 1320  # 환율 적용
        }


# ============= Sentence Transformer (지연 로딩) =============

_sentence_model = None

def get_sentence_model():
    """Sentence Transformer 모델 로드 (싱글톤)"""
    global _sentence_model
    if _sentence_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading ko-sbert-sts model...")
            _sentence_model = SentenceTransformer('jhgan/ko-sbert-sts')
            logger.info("ko-sbert-sts model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer: {e}")
            _sentence_model = None
    return _sentence_model


# ============= 뉴스 중복 제거 =============

def deduplicate_news(news_list: list[dict], threshold: float = 0.66) -> list[dict]:
    """
    중복 뉴스 제거 (ko-sbert-sts 기반 의미적 유사도)

    Args:
        news_list: 뉴스 목록
        threshold: 유사도 임계값 (기본값: 0.66 = 66%, 코사인 유사도)

    Returns:
        중복 제거된 뉴스 목록

    Example:
        >>> news = [
        ...     {'title': '삼성전자, 신규 반도체 공장 착공'},
        ...     {'title': '삼성전자 반도체 공장 착공 발표'},  # 중복
        ...     {'title': 'SK하이닉스, AI 칩 수주'}
        ... ]
        >>> deduplicated = deduplicate_news(news, threshold=0.66)
        >>> len(deduplicated)
        2
    """
    if not news_list:
        return []

    # Sentence Transformer 모델 로드
    model = get_sentence_model()

    if model is None:
        logger.warning("STS 모델 로드 실패, 중복 제거 스킵")
        return news_list

    try:
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError:
        logger.error("scikit-learn not installed, 중복 제거 스킵")
        return news_list

    # 제목만 추출
    titles = [news.get('title', '') for news in news_list]
    titles = [t for t in titles if t]  # 빈 제목 제거

    if len(titles) == 0:
        return []

    logger.info(f"STS 모델로 {len(titles)}개 뉴스 임베딩 생성 중...")

    # 제목들을 임베딩으로 변환
    embeddings = model.encode(titles, convert_to_numpy=True, show_progress_bar=False)

    # 중복 제거 로직
    deduplicated = []
    deduplicated_indices = []

    for i in range(len(titles)):
        is_duplicate = False

        # 이미 선택된 뉴스들과 유사도 비교
        for j in deduplicated_indices:
            # 코사인 유사도 계산
            similarity = cosine_similarity(
                embeddings[i].reshape(1, -1),
                embeddings[j].reshape(1, -1)
            )[0][0]

            if similarity >= threshold:
                is_duplicate = True
                logger.debug(f"중복 뉴스 제거: '{titles[i][:50]}...' (유사도: {similarity:.2%})")
                break

        if not is_duplicate:
            deduplicated.append(news_list[i])
            deduplicated_indices.append(i)

    logger.info(f"중복 제거: {len(news_list)}개 → {len(deduplicated)}개 (제거: {len(news_list) - len(deduplicated)}개)")
    return deduplicated
