# 공통 연결 규약 v0.6

캐릭터 설정 연결: `GET /profile/me`, `/characters/me`, `/api/me`에 `grade`, `major`, `appearance`를 추가합니다.
`grade`는 1~4 또는 기존 계정의 null, `major`는 embedded/computer/ict 또는 기존 계정의 null입니다.
`appearance`는 `{base:male|female,hair_length:short|medium|long,hair_color:black|brown|blonde|red|blue|pink|silver}`입니다.
프로필 draft/complete는 동일 필드를 받으며 계정 DB users.character_setup에 저장합니다(마이그레이션 b0003).
기존 nickname/color 호출은 유지합니다. 기존 계정은 null 학년/학과와 기본 외형으로 조회됩니다.
`PUT /profile/me/appearance`는 완료 계정의 위 세 필드만 갱신합니다. 세션 인증이 필요하며 닉네임·캐릭터 ID·스택은 변경하지 않습니다.
실제 UI는 학과 선택을 요구하며 학과에 따른 과잠·성별·머리 모양을 C 픽셀 렌더러에 반영합니다.

현재 통합 기록 규약은 아래 `통합 기록 API` 절을 기준으로 합니다. 이전 `/records`·effects 규약은 호환용입니다.
INUstagram의 `/api/keywords`도 같은 activity_records/characters.stats에 반영합니다.
기존 사용자별 로컬 기록은 기준 스택으로 이어받습니다. 술 +1 시 현재 운동 -1(최소 0), 미래 운동에 차감 부채는 없습니다.
두 업로드 경로의 완료 게시물은 같은 web_posts 피드에서 수락된 친구에게 공개됩니다.
기록 하나의 스택 반영은 한 번뿐이며 API를 바꿔 재전송해도 중복 반영하지 않습니다.
C의 도트 소품에는 B의 표시 단계(0/1/2/3)를 렌더러 입력(0/5/10/15)으로 변환해 전달합니다.
AI 요약은 저장용이며 게시 결과/피드 화면에는 표시하지 않습니다.

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
- 현재 접속: 서버 세션 + `campus_session` HttpOnly 쿠키. Bearer 토큰은 사용하지 않습니다.
- 비밀번호 없는 아이디 접속으로, 동일 아이디를 아는 사람은 동일 계정을 사용할 수 있습니다.

## 현재 API

| API | 담당 | 현재 동작 |
|---|---|---|
| GET /health | 공동 | 상태 확인, 인증 불필요 |
| POST /auth/login | A | 아이디로 계정 생성 또는 재접속, 200 + 세션 쿠키 |
| GET /auth/me | A | 현재 UUID·아이디·접속 방식 반환 |
| POST /auth/logout | A | 현재 세션 폐기 + 쿠키 삭제, 204 |
| GET /profile/me | A | 내 최초 설정 진행 상태 조회 |
| PUT /profile/me/draft | A | 최초 설정 임시 저장 |
| POST /profile/me/complete | A | 최초 설정 완료 + 계정당 캐릭터 1개 생성 |
| GET /characters/me | A | 내 캐릭터 조회, 설정 전 404 |
| POST /records | B | 글 저장·고정 임시 분석, 201 |
| GET /records?limit=50 | B | 내 기록 최신순, limit 1~100 |
| GET /records/{id} | B | 내 기록 상세 |
| POST /records/{id}/retry | B | 소유권 확인 후 501 |
| POST /character-preview/analyze | B | 개발 환경 전용. multipart `text`·`image`를 Gemini로 분류만 하고 저장하지 않음 |

### 게시물 분류 (미리보기)

`POST /character-preview/analyze` (multipart/form-data): `text` 0~5,000자, `image` JPG·PNG·WEBP 10MB 이하, 둘 중 하나 필수.

```json
{"category":"study","category_label":"공부","keywords":["도서관","시험"],
 "summary":"도서관에서 시험 공부를 했어요.","reason":"공부 관련 키워드","needs_review":false}
```

`category`는 `drink`·`study`·`exercise`·`love` 또는 `null`(분류 근거 없음).
오류: 400 `EMPTY_POST`·`TEXT_TOO_LONG`·`IMAGE_*`, 503 `GEMINI_NOT_CONFIGURED`, 502 `ANALYSIS_FAILED`.
서버 `.env`에 `GEMINI_API_KEY`가 있어야 하며 키는 브라우저에 보내지 않습니다.

### 아이디 접속

```json
{"username":"campus_a"}
```

`POST /auth/login`은 위 요청으로 계정을 생성하거나 기존 계정에 접속합니다.
아이디는 한글·영문·숫자·밑줄 2~20자, 앞뒤 공백 제거/NFC 정규화/영문 소문자 변환을 적용합니다.
서버 내부 UUID는 로그인 아이디와 별개이며 B는 계속 UUID를 기록 소유자로 사용합니다.

로그인 및 `/auth/me` 응답:

```json
{"id":"00000000-0000-4000-8000-000000000001","username":"campus_a","auth_mode":"id-only"}
```

임시 인증 응답은 `username=null`, `auth_mode=local-development`입니다.
유효하지 않거나 만료된 쿠키는 `401 SESSION_EXPIRED`, 쿠키 없는 미접속은 `401 UNAUTHENTICATED`입니다.
세션은 DB에 저장되어 서버 재시작 후에도 유지되고 기본 7일 뒤 만료됩니다.
로그아웃은 현재 세션만 폐기합니다. 같은 아이디의 다른 브라우저 세션은 유지됩니다.
브라우저는 같은 origin의 쿠키를 자동 전달하므로 B가 별도 토큰 저장 로직을 만들 필요가 없습니다.
기존 B의 `get_current_user` 의존성 및 기록 API 호출 경로는 유지됩니다.
변경 요청의 다른 Origin 또는 cross-site 요청은 `403 CROSS_ORIGIN_DENIED`입니다.
### 최초 설정과 캐릭터

선택한 정책: 접속 아이디와 별도의 닉네임, 임시 캐릭터의 색상 선택.
닉네임은 앞뒤 공백을 제거한 2~12자이고 계정 사이의 중복은 허용합니다.
색상 ID는 `green`, `blue`, `yellow`, `pink`, `purple`입니다.

`GET /profile/me` 응답:

```json
{
  "user_id":"00000000-0000-4000-8000-000000000001",
  "nickname":null,
  "color":null,
  "step":"nickname",
  "onboarding_completed":false
}
```

`PUT /profile/me/draft` 요청 예시:

```json
{"nickname":"새내기","color":"blue","step":"color"}
```

`step`은 `nickname` 또는 `color`입니다. 닉네임 단계에서는 미완성 이름(0~12자)을 저장할 수 있고,
색상 단계로 진행할 때는 닉네임이 2자 이상이어야 합니다. `color=null`로 색상 미선택 상태를 저장할 수 있습니다.
이 API는 전체 임시 설정을 저장하며 사용자 ID와 완료 여부는 입력받지 않습니다.
완료 후 임시 저장은 `409 SETUP_ALREADY_COMPLETED`입니다.

`POST /profile/me/complete` 요청:

```json
{"nickname":"새내기","color":"blue"}
```

응답은 `{"profile":{...},"character":{...}}`입니다.
프로필 완료와 캐릭터 생성은 하나의 DB 트랜잭션으로 저장합니다.
반복/동시 요청은 처음 완료한 프로필·캐릭터를 반환하며 완료 후 이름/색상 변경 API로 사용하지 않습니다.
`characters.user_id`의 UNIQUE 제약으로 계정당 하나만 생성됩니다.

`GET /characters/me` 응답 예시:

```json
{
  "id":"20000000-0000-4000-8000-000000000001",
  "user_id":"00000000-0000-4000-8000-000000000001",
  "color":"blue",
  "effects":[]
}
```

설정 전 캐릭터 조회는 `404 CHARACTER_NOT_FOUND`입니다.
지급 전에는 `effects=[]`, 지급 후에는 소유한 효과의 `effect_id`, `level`, `visible`을 반환합니다.
화면 표시 여부와 소유 정보는 별개이며, 숨긴 효과도 다음 획득 시 레벨이 증가합니다.
화면은 `/profile/me`의 완료 여부에 따라 설정 또는 메인 화면을 표시합니다.
B의 기록 API에는 아직 최초 설정 완료 검사를 추가하지 않았으며, 독립 개발용 호출은 계속 가능합니다.
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

분석 스키마는 `analysis/schemas.py`에서 검증합니다. 초기 분류는
`study`, `social`, `exercise`, `culture`, `daily`입니다.
분류/키워드/요약만 AI에서 받고 보상 결정은 A의 서버 규칙이 수행합니다.
키워드는 1~5개, 요약은 1~300자입니다. 사진/실제 AI 지원 시 제한을 재검토합니다.

## A의 효과 처리 함수

위치: `backend/app/characters/service.py`.
A가 서버 함수와 DB 저장/조회, 기본 효과 목록 표시를 구현했습니다.
B의 기록/분석 작업에서 자동으로 호출하는 부분은 아직 연결하지 않았습니다.
브라우저가 임의의 활동 분류나 지급 레벨을 지정하는 보상 API는 제공하지 않습니다.

### B의 호출 순서

1. 기록 소유자를 서버에서 확인합니다.
2. 검증된 분석 결과와 `status=completed`를 기록에 저장하고 commit합니다.
3. 기존 쓰기 트랜잭션을 끝낸 뒤 A의 함수를 호출합니다. 함수는 자체 DB 세션/트랜잭션을 소유합니다.
4. 성공/실패를 표시하고 `GET /characters/me`로 최신 캐릭터를 갱신합니다.

```python
from uuid import UUID

from app.characters.service import EffectApplicationError, apply_analysis_effects

try:
    result = apply_analysis_effects(
        user_id=UUID(owner_id),  # 인증/서버 작업으로 확인한 소유자
        record_id=UUID(record_id),
        analysis=validated_analysis,  # AnalysisResult 인스턴스
    )
except EffectApplicationError as exc:
    # 화면에 전달 가능한 정보만 사용합니다. 원본 내부 예외를 노출하지 않습니다.
    effect_error = {"code": exc.code, "message": exc.message, "retryable": exc.retryable}
else:
    payload = result.model_dump(mode="json")
```

### 확정한 규칙

- `study → book`(책), `social → heart`(하트), `exercise → dumbbell`(아령),
  `culture → palette`(팔레트), `daily → star`(별).
- 첫 획득은 1레벨, 같은 효과에 대응하는 **새 기록마다 +1레벨**입니다. 현재 최대 레벨 제한은 없습니다.
- 서로 다른 종류의 효과는 유지되므로 책과 하트를 동시에 소유할 수 있습니다.
- 같은 기록은 한 번만 지급합니다. `effect_grants.record_id`가 PK입니다.
- 같은 기록의 재시도와 같은 캐릭터의 동시 강화를 잠금/트랜잭션으로 직렬화합니다.
- 실제 보상은 DB에 저장된 분석을 다시 검증하여 결정합니다. 전달받은 분석이 다르면 거부합니다.
- 소유 정보와 `visible`을 분리하며, 강화는 기존 표시 여부를 바꾸지 않습니다. 표시 토글 화면/API는 후속입니다.
- 다섯 활동 분류 모두 같은 강화·중복 지급 방지·복구 규칙을 적용합니다.
- 이전에 운동·문화·일상 기록이 규칙 미정으로 failed였더라도,
  저장된 분석으로 같은 함수를 다시 호출하면 해당 효과를 지급할 수 있습니다.

### 성공 결과

```json
{
  "record_id": "10000000-0000-4000-8000-000000000001",
  "effect_status": "applied",
  "already_applied": false,
  "effects": [{"effect_id": "book", "level": 1, "visible": true}]
}
```

`effects`는 **그 기록의 최초 지급 당시 소유 효과 목록**입니다. 같은 기록의 재호출은
`already_applied=true`와 저장된 동일 목록을 반환합니다. 이후 다른 기록으로 레벨이 올라갔더라도
기존 기록 응답을 바꾸지 않으며, 최신 목록은 캐릭터 조회를 사용합니다.

### 실패와 복구

| 함수 오류 코드 | 의미 | 자동 재시도 |
|---|---|---|
| RECORD_NOT_FOUND | 없거나 다른 계정의 기록 | 금지 |
| ANALYSIS_NOT_COMPLETED | 분석 전/진행/실패 또는 분석 없음 | 분석 완료 후 호출 |
| ANALYSIS_MISMATCH | 전달한 결과와 저장된 결과가 다름 | B 연결 확인 필요 |
| INVALID_SAVED_ANALYSIS | 저장된 분석 스키마가 잘못됨 | B의 분석 검증 수정 필요 |
| EFFECT_RULE_NOT_CONFIGURED | 향후 분류 추가 시 지급 규칙 누락 방어 | 규칙 추가 후 호출 |
| CHARACTER_NOT_FOUND | 최초 설정/캐릭터 없음 | 설정 완료 후 가능 |
| EFFECT_APPLICATION_FAILED | DB 오류 등 지급 실패 | 가능 |

효과 레벨·지급 내역·`effect_status=applied`를 하나의 트랜잭션으로 저장합니다.
실패 시 이 변경들을 되돌리고 소유자 기록의 `effect_status=failed`만 별도 저장합니다.
다른 요청에서 이미 지급했다면 failed로 덮어쓰지 않습니다.
분석의 `status=completed`와 원본 분석 결과는 유지됩니다.
소유권/미완료 분석/호출 결과 불일치 오류는 효과 상태를 변경하지 않습니다.
DB 자체가 중단된 경우 failed 저장도 불가능할 수 있어, 복구 시
completed 분석 중 효과 미반영(not_requested/pending/failed) 기록을 확인합니다.

복구 호출은 분석을 생략하면 저장된 결과를 사용합니다. AI를 다시 호출하지 않습니다.

```python
result = apply_analysis_effects(user_id=UUID(owner_id), record_id=UUID(record_id))
```

B가 복구 작업과 화면 재시도 흐름에서 이 함수를 재사용합니다.
분석 재시도 API(`/records/{id}/retry`)의 실제 구현은 B 단계에 남아 있습니다.

## B 웹 시제품의 최신 규칙과 통합 전 차이

`prototypes/records-analysis`는 웹 메인·게시·라운지·예제 초대 흐름과 실제 Gemini 분석을 제공한다.
분류는 술·공부·연애·운동이며, 근거 키워드가 없거나 불확실하면 누적을 보류한다.
술 기록을 처음 반영할 때 술 +1과 운동 스택 -1을 적용한다. 운동은 최소 0이며
0에서의 차감은 미래의 운동에 이월하지 않는다. 동일 기록 재처리는 추가 차감하지 않는다.
효과 디자인은 현재 스택 1~4/5~9/10 이상에 따라 1/2/3단계로 표시한다.
운동이 감소하면 단계도 내려가고, 0이면 운동 소품을 표시하지 않는다.

이 규칙은 현재 시제품의 공용 로컬 SQLite에 적용되어 있다. 위 A 서버의 다섯 분류·
기록당 효과 레벨 +1 규약과는 아직 연결하지 않았다. 자동 변환으로 임의 연결하지 않으며,
통합 시 분석 스키마·분류/효과 ID·원자적 증감·사용자 격리 규약과 테스트를 함께 맞춘다.
상세 화면/API 제안은 [B의 앱 연결 안내](../prototypes/records-analysis/docs/app-server-integration.md)를 참고한다.

### 개발 전용 로컬 연결 모드

현재는 LOCAL_WEB_PREVIEW_ENABLED=true인 개발 서버에서 A의 실제 로그인·프로필을 거쳐
`/app`의 B 화면으로 이동하는 연결을 추가했다. `GET /api/me`, `GET /api/progress`,
`POST /api/keywords`는 기존 로그인 쿠키로 인증한다. 사용자 ID는 요청으로 받지 않는다.
계정별 시제품 스택 DB를 따로 선택하며, A의 다섯 분류 EffectGrant 저장은 변경하지 않는다.
즉 로그인/설정과 새 웹 화면을 한 주소에서 검증할 수 있지만 최종 저장 구조 통합과는 구분한다.
개발 모드 판별용 `GET /api/preview-status`와 인증된 브라우저 설정용
`GET /api/frontend-config.js`에는 API 키가 포함되지 않는다.

### INUstagram 게시물 피드와 실제 친구 등록

- 개발 연결 모드의 `POST /api/keywords`는 먼저 원문·사진을 저장하고, 같은 record_id로 재시도하면 기존 게시물을 사용한다.
- 응답에 `post_id`가 추가된다. 원본 사진은 MIME·크기를 검증하고 DB BLOB으로 보관한다.
- 분석 실패 시에도 게시물은 유지된다. 120초 이상 멈춘 processing 기록은 재시도로 처리권을 얻을 수 있다.
- 성공한 게시물 재요청은 저장된 분석을 반환하고 추가 AI 호출·스택 지급·운동 차감을 하지 않는다.
- `GET /api/feed?scope=all|mine|friends&limit=12&before=커서`는 `{posts,next_cursor}`를 반환한다.
- 최신 created_at → 같은 시각이면 id 내림차순이다. 재분석 시 게시 시각을 변경하지 않는다.
- 각 게시물은 `{id,author:{id,nickname,emoji},text,image_url,keywords,analysis_status,created_at}`이다.
- AI 요약/이미지 설명은 피드에 반환하거나 표시하지 않는다. text는 사용자가 직접 쓴 글이다.
- `GET /api/posts/{id}/image`는 로그인한 본인/수락된 친구에게만 이미지를 반환한다. 그 외는 404, 미접속은 401이다.
- `GET /api/people?nickname=검색어`는 최초 설정을 마친 본인 외 사용자를 최대 20명 반환한다.
- `GET /api/friends`는 `{friends,incoming,outgoing}`를 반환한다. 대기 요청은 게시물 접근 권한이 없다.
- `POST /api/friend-requests` 요청은 `{recipient_id:UUID}`이다. 자기 자신·미설정 계정·중복 대기/기존 친구는 거부한다.
- `POST /api/friend-requests/{id}/response` 요청은 `{accept:bool}`이다. 요청 수신자만 응답할 수 있다.
- 수락된 쌍방 친구 관계만 피드와 사진 권한에 사용한다. localStorage의 라운지 예제 초대나 클라이언트가 전달하는 친구 ID 목록은 신뢰하지 않는다.


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
- progress.calculate_progress: 활동별 횟수 → 표시 단계/색상/소품 정보
- A의 integrations/state_store: 인증된 사용자에 대한 중복 방지·계산 결과 검증·트랜잭션 저장

B의 현재 분류는 술/공부/연애/운동입니다. A가 새 분류나 변경량을 추가하지 않습니다.
현재 B 계산은 1~4회 표시 단계 1, 5~9회 2, 10회 이상 3이며 원본과 동일합니다.
이는 B가 반환하는 표현용 정보입니다. A의 이전 ‘기록마다 강화 레벨 +1’과 연결하지 않습니다.
B가 향후 스탯이나 상태 규칙을 변경하면 B 함수와 공통 응답 규약을 함께 갱신합니다.

## 캐릭터 조회와 C 전달

`GET /characters/me`의 `stats`가 최신 상태입니다. 예시의 count/level/color는 B가 계산한 값을 저장한 것입니다.
`stats_snapshot`은 해당 기록 반영 당시 목록이며 이후 기록이 쌓이면 최신 상태와 다를 수 있습니다.
C는 최신 캐릭터를 다시 조회하여 화면을 갱신합니다.
현재 원본에 표정·기분·동작 전환 코드가 없으므로 해당 필드는 새로 추측해 만들지 않았습니다.
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
