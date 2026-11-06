from app.analysis.schemas import AnalysisResult, Category


def analyze_mock(text: str) -> AnalysisResult:
    """B의 독립 개발용 고정 응답. 실제 AI 호출은 이 모듈에서 교체합니다."""
    return AnalysisResult(
        category=Category.study,
        keywords=["도서관", "시험 공부"],
        summary="도서관에서 시험을 준비했어요.",
    )
