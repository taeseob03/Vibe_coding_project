# 공통 연결 규약 v0.1

이 문서는 독립 개발을 위한 초기 규약입니다. 변경 시 A·B가 문서/예제/관련 테스트를 함께 수정합니다.
자동 생성된 실제 스키마는 실행 후 `/docs`와 `/openapi.json`에서 확인합니다.

## 공통

- 경로는 계획 원문의 `/auth`, `/characters`, `/records`를 사용합니다.
- 사용자·캐릭터·기록 ID: UUID 문자열. 예제의 `user_001` 형태 대신 실제 UUID를 사용합니다.
- 시간: UTC ISO 8601 (`Z`). SQLite에서 offset이 생략된 값도 응답 시 UTC로 직렬화합니다.
- JSON 요청은 정의된 필드만 받습니다. 기록의 `user_id`를 보내면 422입니다.
- 기록 소유자는 `accounts.dependencies.get_current_user`의 반환값으로 결정합니다.
- 인증 실패 401, 잘못된 입력 422, 없는 기록 또는 다른 사람의 기록 404, 미구현 501.
- 오류: `{"error":{"code":"UNAUTHENTICATED","message":"로그인이 필요합니다."}}`.
- 개발 인증: `.env`의 `DEV_USER_ID`. 헤더나 요청 본문에서 ID를 받지 않습니다.
- 실제 인증 예정: `Authorization: Bearer <token>`을 공통 의존성에서 검증. A 구현 시 확정합니다.

## 현재 API

| API | 담당 | 현재 동작 |
|---|---|---|
| GET /health | 공동 | 상태 확인, 인증 불필요 |
| GET /auth/me | A | 개발 사용자 ID 반환; 실제 인증 교체 지점 |
| GET /characters/me | A | 인증 후 501 |
| POST /records | B | 글 저장·고정 임시 분석, 201 |
| GET /records?limit=50 | B | 내 기록 최신순, limit 1~100 |
| GET /records/{id} | B | 내 기록 상세 |
| POST /records/{id}/retry | B | 소유권 확인 후 501 |

가입/로그인/최초 설정 경로는 A가 PR로 요청/응답을 문서화하고 추가합니다.
기록 삭제·분류 수정 API는 초기 단계에서 추가하지 않습니다.

### 기록 작성

```json
{"text":"도서관에서 시험 공부를 했다."}
```

개발 환경 응답 예시는 [examples/record.json](examples/record.json)을 참고합니다.
현재 분석은 입력과 무관한 고정 응답이며 `status=completed`, `effect_status=not_requested`를 반환합니다.
효과를 지급한 것으로 표시하면 안 됩니다.

## B가 구현할 비동기 상태 규약

- 분석 상태: `pending → processing → completed | failed`.
- 분석 전 `analysis=null`, 실패 시 안전한 오류 코드와 사용자 안내 필드 추가.
- 저장 후 ID와 `pending`을 반환하고, 상세 조회로 상태를 확인합니다.
- 프런트 폴링은 완료/실패/화면 이탈 시 중단합니다.
- 작업의 원자적 상태 변경/잠금으로 중복 실행을 막고 재시작 복구를 구현합니다.
- 재시도는 실패한 소유자 기록에만 허용합니다. 분석 성공·효과 실패를 재분석하지 않습니다.

분석 스키마는 `analysis/schemas.py`에서 검증합니다. 분류는
`drink`(술), `study`(공부), `exercise`(운동), `love`(연애), `none`(해당 없음)입니다.
(개발 계획 7.3. 코드의 기존 `study`, `social`, `exercise`, `culture`, `daily`는 B가 교체 예정)
분류/키워드/요약만 AI에서 받고 보상 결정은 A의 서버 규칙이 수행합니다.
키워드는 1~5개, 요약은 1~300자입니다. 사진/실제 AI 지원 시 제한을 재검토합니다.

## A의 효과 처리 함수 연결점

```python
apply_analysis_effects(user_id=UUID(...), record_id=UUID(...), analysis=AnalysisResult(...))
```

위치는 `backend/app/characters/service.py`이며 아직 `NotImplementedError`인 명시적 stub입니다.
B의 임시 분석 흐름에서는 호출하지 않습니다.

구현 시 반환 형식 초안:

```json
{
  "record_id": "10000000-0000-4000-8000-000000000001",
  "effect_status": "applied",
  "already_applied": false,
  "effects": [{"effect_id": "book", "level": 1, "visible": true}]
}
```

레벨 규칙 (개발 계획 7.4): 분석 완료 기록 하나가 해당 카테고리 레벨을 +1 합니다. `none`은 오르지 않습니다.
소품 단계 `tier = floor(level / 5)`이며 술→술병, 공부→책, 운동→덤벨, 연애→하트입니다.
반환 형식도 `effects` 대신 `levels: [{"category","level","tier"}]`로 바꾸는 것을 제안합니다. A 구현 시 확정합니다.
현재 캐릭터/효과 테이블은 만들지 않았으므로 A가 마이그레이션과 함께 추가합니다.
함수는 기록 소유권과 저장된 분석 결과를 확인하고,
기록별 지급 내역의 DB UNIQUE 제약 및 하나의 트랜잭션으로 보상과 지급 내역을 함께 저장해야 합니다.
같은 기록을 재처리하면 기존 결과를 반환합니다. B는 캐릭터 DB를 직접 변경하지 않습니다.
효과 상태는 `not_requested`, `pending`, `applied`, `failed`로 분석 상태와 별도로 저장합니다.
효과 실패 시 저장된 분석으로 재지급하고 AI를 다시 호출하지 않습니다.
