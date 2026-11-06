# 통합 연결 규약 v0.7

이 문서가 현재 통합 앱의 기준입니다. 사용자 요청에 따라 **스탯 계산은 B**, **계정별 저장·조회는 A**가 담당합니다.
C는 이 API로 화면·캐릭터를 표현합니다. 원래 개발 계획은 원문으로 보존합니다.

## 공통

- ID: UUID 문자열. 소유자는 세션에서 결정하며 본문의 user_id를 신뢰하지 않습니다.
- 접속: `campus_session` HttpOnly 쿠키, 기본 7일. 같은 origin의 브라우저 요청에 자동 전달합니다.
- 아이디만으로 접속하므로 아이디를 아는 사람은 같은 계정을 사용할 수 있습니다.
- 오류: `{"error":{"code":"RECORD_NOT_FOUND","message":"기록을 찾을 수 없습니다."}}`.
- 인증 401, 다른 사용자/없는 기록 404, 입력 형식 400/422, 업로드 초과 413, 상태 충돌 409.
- 다른 Origin 또는 cross-site 변경 요청은 403입니다.
- 시간은 UTC ISO 8601 `Z`입니다. 비밀 키·내부 예외는 응답하지 않습니다.

## 접속과 최초 설정

| API | 동작 |
|---|---|
| POST /auth/login | `{"username":"student_a"}`로 계정 생성/재접속, 200 + 쿠키 |
| GET /auth/me | 현재 UUID·아이디·접속 방식 |
| POST /auth/logout | 현재 세션 폐기, 204 |
| GET /profile/me | 닉네임·색상·단계·완료 여부 |
| PUT /profile/me/draft | `{"nickname":"새내기","color":"blue","step":"color"}` 임시 저장 |
| POST /profile/me/complete | `{"nickname":"새내기","color":"blue"}` 완료 + 캐릭터 원자적 생성 |
| GET /characters/me | 내 캐릭터와 현재 `stats` |

아이디는 한글·영문·숫자·밑줄 2~20자, 앞뒤 공백 제거/NFC 정규화/영문 소문자 변환입니다.
닉네임은 별도 2~12자이며 중복을 허용합니다. 색상은 green/blue/yellow/pink/purple입니다.
임시 저장의 step은 nickname 또는 color입니다. 닉네임 단계에서는 0~12자 미완성 입력을 저장할 수 있습니다.
색상 단계와 완료 시 닉네임이 2자 이상이어야 합니다. 완료에는 색상이 필요합니다.
완료 후 draft 저장은 409입니다. 반복·동시 완료에도 캐릭터는 하나이고 기존 설정을 유지합니다.

## 통합 기록 API

| API | 동작 |
|---|---|
| POST /api/records | multipart 글/사진 저장, 새 기록 201 + pending |
| GET /api/records?limit=50 | 내 기록 최신순, 1~100개 |
| GET /api/records/{id} | 내 기록의 분석·스탯 반영 상태 |
| GET /api/records/{id}/image | 내 원본 사진, 없으면 404 |
| POST /api/records/{id}/retry | 실패 분석 또는 스탯 저장 재처리, 202 |

POST는 `text`(선택), `image`(선택), `request_id`(선택 UUID)를 받습니다.
글 또는 사진 하나 이상이 필요합니다. 최대 5,000자, 정지 JPG/PNG/WEBP 한 장 10MB·2,500만 픽셀입니다.
파일 내용은 B의 이미지 검증 함수로 검사합니다. 최초 설정을 완료한 계정만 저장할 수 있습니다.
`request_id`를 같은 입력 재전송에 재사용하면 동일 기록을 200으로 반환하고 AI/스탯을 중복 실행하지 않습니다.
같은 ID에 다른 입력은 409입니다. request_id는 계정별로 분리되며 내부 기록 ID는 서버가 생성합니다.

기록 응답 예시:

```json
{
  "id":"10000000-0000-4000-8000-000000000001",
  "user_id":"00000000-0000-4000-8000-000000000001",
  "request_id":"30000000-0000-4000-8000-000000000001",
  "text":"도서관에서 공부했다",
  "has_image":true,
  "status":"completed",
  "analysis":{
    "keywords":["도서관","시험 공부"],
    "summary":"도서관에서 시험을 준비했어요.",
    "category":"공부",
    "category_keywords":["시험 공부"],
    "category_reason":"학습 활동을 기록했어요.",
    "needs_review":false
  },
  "analysis_error":null,
  "stat_status":"applied",
  "state_error":null,
  "stats_snapshot":[
    {"category":"공부","id":"study_book","name":"책 소품","icon":"📚","slot":"hand","count":1,"level":1,"color":"#f9a8d4"}
  ],
  "created_at":"2026-11-06T10:00:00Z"
}
```

예시는 stats_snapshot 중 한 항목만 표시했으며 실제 목록은 B의 네 활동 항목입니다.
분석 전 analysis=null입니다. 사진 바이트와 지문 해시는 JSON에 노출하지 않습니다.
사진 API는 쿠키와 소유권을 확인하고 `Cache-Control: private, no-store`를 반환합니다.

### 상태와 복구

- 분석: pending → processing → completed 또는 failed.
- 스탯 저장: pending → applied, skipped 또는 failed.
- B의 category=null 또는 needs_review=true이면 분석은 completed, 스탯은 skipped입니다.
- 분석 실패 시 글·사진을 보존합니다. retry는 원본으로 Gemini를 다시 호출합니다.
- 분석 완료 후 스탯 저장만 실패하면 retry는 저장된 분석만 재사용하며 Gemini를 다시 호출하지 않습니다.
- 이미 완료/반영한 기록이나 처리 중인 기록의 불필요한 retry는 409입니다.
- 재시도/동시 요청에도 기록 하나가 스탯 횟수에 두 번 포함되지 않습니다.
- 서버 재시작 시 pending/processing을 ANALYSIS_INTERRUPTED 실패로 바꾸며 명시적 재시도를 기다립니다.
- 오래된 분석 시도의 응답이 새 시도의 결과를 덮어쓰지 않도록 attempt 조건으로 저장합니다.

안전한 오류 코드: ANALYSIS_UNAVAILABLE, ANALYSIS_TIMEOUT, ANALYSIS_RATE_LIMITED,
ANALYSIS_CONFIGURATION_ERROR, INVALID_ANALYSIS_RESPONSE, ANALYSIS_FAILED, ANALYSIS_INTERRUPTED,
STATE_SAVE_FAILED. 분석 오류와 상태 저장 오류는 서로 다른 필드입니다.

## B 결과와 A의 저장 경계

원본은 merge한 `prototypes/records-analysis/app/`입니다.

- analysis.extract_keywords: Gemini 호출·KeywordResult 검증
- progress.eligible_category: 스탯 반영 여부
- progress.calculate_snapshot: 최초 반영 순서의 이벤트 → 현재 스탯/변화량
- effects.character_state: 현재 스탯 → 표정 코드
- A의 integrations/state_store: 인증된 사용자에 대한 중복 방지·계산 결과 검증·트랜잭션 저장

B의 현재 분류는 술/공부/연애/운동입니다. A가 새 분류나 변경량을 추가하지 않습니다.
현재 B 계산은 1~4회 표시 단계 1, 5~9회 2, 10회 이상 3이며 원본과 동일합니다.
이는 B가 반환하는 표현용 정보입니다. A의 이전 ‘기록마다 강화 레벨 +1’과 연결하지 않습니다.
B가 향후 스탯이나 상태 규칙을 변경하면 B 함수와 공통 응답 규약을 함께 갱신합니다.

## 캐릭터 조회와 C 전달

`GET /characters/me`의 `stats`가 최신 상태입니다. 예시의 count/level/color는 B가 계산한 값을 저장한 것입니다.
`stats_snapshot`은 해당 기록 반영 당시 목록이며 이후 기록이 쌓이면 최신 상태와 다를 수 있습니다.
C는 최신 캐릭터를 다시 조회하여 화면을 갱신합니다.
state.expression은 B 함수가 정한 neutral/focused/energetic/heart_eyes/relaxed 중 하나이며 Phaser가 표현합니다. intensity는 B 표시 단계, dominant_activity는 현재 우세 활동입니다.
구체적인 표시 연결은 [frontend-contract.md](frontend-contract.md)를 참고하세요.

## 이전 호환 API

기존 `/records`는 초기 고정 mock 실험용이며 OpenAPI에서 deprecated입니다.
이전 `effects` 필드/테이블과 소품 강화 함수는 기존 데이터 호환용입니다.
새 확인 화면과 통합 API는 이를 사용하지 않습니다. 새 코드는 `/api/records`와 `characters.me.stats`를 사용합니다.
자동 데이터 변환이나 기존 데이터 삭제는 하지 않았습니다.
과거 규약은 [legacy-effects-contract.md](legacy-effects-contract.md)에 남겼습니다.

## 구현 참고

분석 실행은 [FastAPI BackgroundTasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)로 응답 뒤 진행합니다.
현재는 단일 프로세스 개발 서버를 대상으로 하며 여러 서버의 작업 소유권/외부 큐는 후속입니다.
Gemini 호출은 B의 [Google Gen AI SDK](https://googleapis.github.io/python-genai/) 구현을 재사용합니다.

## 완성 게임 API 추가

- `GET /api/runtime`: gemini_available/demo_available. 비밀 값은 반환하지 않습니다.
- `GET /api/me`: 현재 사용자·닉네임·기본 색상·대표 칭호·stats·state.
- `GET /api/progress`: `{progress:[...],state:{expression,intensity,dominant_activity}}`.
- `POST /api/records/demo`: development 전용 multipart category/text/image/request_id.
  샘플임을 source=demo와 요약에 명시합니다. 실제 Gemini 호출을 하지 않습니다.
- 통합 기록 응답에 source, stack_changes를 추가했습니다. JSON의 stack_changes는 해당 기록의 최초 반영 이력입니다.
  중복 게시의 화면 어댑터는 추가 변화량을 비워 표시합니다.

### 순서 있는 스탯

B의 새 규칙은 술 +1일 때 현재 운동이 양수면 운동 -1, 아니면 0 유지입니다.
A는 캐릭터 잠금 아래 applied_order를 부여해 최초 반영 순서를 보존하고 B 함수로 재생합니다.
분석 완료 순서가 적용 순서입니다. 동일 기록은 order를 다시 받지 않습니다.
이전 저장 기록은 마이그레이션에서 created_at/id 순으로 안정적 순서를 부여하고 시작 시 B 규칙으로 다시 계산합니다.
A의 독자적인 소품 +1 규칙은 계속 호환 경로에만 남습니다.

### 칭호

`GET /api/titles`는 id/name/description/earned/selected 목록입니다.
`PUT /api/titles/selected {title_id}`는 획득한 칭호만 선택하며 null로 해제할 수 있습니다.
first_step: 첫 확정 활동. steady_challenger: 서로 다른 한국 날짜 5일의 공부 기록.
campus_explorer: 서로 다른 활동 3종을 확정 기록. 스탯 차감으로 이미 획득한 칭호를 회수하지 않습니다.
칭호 판정은 applied인 기록만 사용하며 기록·스탯 저장 트랜잭션에서 중복 없이 지급합니다.

### 실제 친구·라운지

| API | 동작 |
|---|---|
| GET /api/lounges | 내 방을 보장하고 참여 중인 방 목록 반환 |
| GET /api/lounges/{id}/members | 멤버만 조회 가능. id/nickname/emoji/color/counts/stats/state/title |
| GET /api/users?nickname=... | 본인 제외, 설정 완료 사용자, 최대 20명 |
| POST /api/lounges/{id}/invitations | `{recipient_id}`. 방 주인만 초대 |
| GET /api/lounge-invitations | 내가 보낸/받은 초대 |
| POST /api/lounge-invitations/{id}/response | `{accept:bool}`. 수신자만 수락/거절 |
| WS /api/lounges/{id}/live | 동일 Origin·유효한 쿠키·방 멤버만 연결 |

자기 초대·이미 참여·대기 중복 초대는 409, 다른 발신자/수신자 접근은 403/404입니다.
수락과 멤버 추가를 같은 트랜잭션에 저장합니다. 같은 수락/거절 반복은 기존 결과를 반환하고 반대 응답은 409입니다.
거절 후 방 주인이 다시 초대할 수 있습니다. 예제 친구를 실제 회원으로 자동 생성하지 않습니다.
WebSocket snapshot에는 room_id/tick/people과 서버 좌표 x/y·접속 online·스탯·표정이 포함됩니다.
클라이언트는 이동 좌표를 지정하지 않고 서버가 자동 이동을 계산합니다. 두 브라우저가 같은 tick을 받으면 같은 위치를 표현합니다.
세션 만료/로그아웃/권한 만료 시 1008로 종료합니다. 정상 연결 장애는 화면에서 자동 재연결합니다.
현재 방 위치는 단일 서버의 메모리에 보관합니다. 회원·초대·캐릭터·스탯·칭호는 DB에서 복원합니다.
