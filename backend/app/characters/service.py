from uuid import UUID

from app.analysis.schemas import AnalysisResult


def apply_analysis_effects(*, user_id: UUID, record_id: UUID, analysis: AnalysisResult):
    """A가 구현할 연결 지점. B는 캐릭터 DB를 직접 수정하지 않습니다.

    소유권 확인과 record_id UNIQUE 제약을 포함한 하나의 트랜잭션으로 처리합니다.
    반환 규약은 docs/api-contract.md를 참고하세요.
    """
    raise NotImplementedError("A: 효과 지급/중복 방지 구현 필요")
