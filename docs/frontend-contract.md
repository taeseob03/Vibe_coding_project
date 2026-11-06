# C의 게임 화면 연결 규약

최신 통합: 개발 연결 모드의 `/app`은 INUstagram 메인·피드·라운지입니다.
메인의 도트 캐릭터는 main의 `assets/character/pixel-character.js`를 사용하며 원래 독립 미리보기도 유지합니다.
캐릭터 표시 단계는 B의 1/5/10회 기준을 유지하도록 어댑터에서 변환합니다. 저장되지 않은 학년/학과는 이름표에 넣지 않습니다.
`/static/app.js` 등은 시제품 자산이며 `/static/accounts|shared|characters|records/`는 기존 A 화면의 호환 경로입니다.
두 기록 API와 `/characters/me`, `/api/progress`는 같은 계정 스택을 조회합니다.
`feature/post-titles`의 칭호도 실제 메인에 연결합니다. 소품의 표시 단계 변환과 별개로 칭호는 실제 count의 5/10/15/20 경계를 사용합니다.

A는 인증·저장·조회, B는 분석·스탯 계산, C는 게임 화면과 캐릭터 표현을 담당합니다.
현재 `frontend/`는 동작 확인용 임시 화면이며 자산 URL은 `/static/` 접두사를 사용합니다. API 경로와 인증 연결을 유지하며 교체할 수 있습니다.

## 진입 순서

1. `GET /auth/me`. 401이면 아이디 접속 화면을 표시합니다.
2. `POST /auth/login`에 username을 JSON으로 보내고 세션 쿠키를 받습니다.
3. `GET /profile/me`. onboarding_completed=false이면 닉네임/색상 설정을 표시합니다.
4. 설정 완료 후 `GET /characters/me`, `GET /api/records`로 메인 상태를 불러옵니다.

쿠키를 JavaScript나 localStorage에 복사하지 않습니다. 같은 origin fetch는 `credentials: 'same-origin'`을 사용합니다.
현재 서버는 프런트엔드를 같은 origin에서 제공하며 다른 Origin 변경 요청은 차단합니다.

## 사진/글 입력

```javascript
const data = new FormData();
data.append('request_id', crypto.randomUUID()); // 같은 입력 재전송에는 동일 UUID 재사용
if (text) data.append('text', text);
if (file) data.append('image', file);
const response = await fetch('/api/records', {
  method: 'POST', credentials: 'same-origin', body: data,
});
const record = await response.json();
```

FormData에 Content-Type을 직접 지정하지 않습니다.
저장 후 상세 GET을 약 1~2초 간격으로 조회하며 분석/상태 반영이 끝나거나 화면 이탈/숨김 시 중단합니다.
`analysis_error`와 `state_error`의 안전한 message를 각각 안내하고 실패 시 retry API를 사용합니다.
같은 입력의 통신 실패 재전송은 request_id를 유지하고, 새 입력은 새 request_id를 만듭니다.

## 캐릭터 표현용 데이터

```json
{
  "id":"20000000-0000-4000-8000-000000000001",
  "user_id":"00000000-0000-4000-8000-000000000001",
  "color":"blue",
  "stats":[
    {"category":"공부","id":"study_book","name":"책 소품","icon":"📚","slot":"hand","count":5,"level":2,"color":"#ec4899"}
  ],
  "effects":[]
}
```

stats의 각 항목은 B가 제공한 표시 정보입니다. 예시는 한 항목만 표시했습니다.

| 필드 | C의 사용 |
|---|---|
| 캐릭터 color | 최초 설정에서 선택한 기본 캐릭터 색상 |
| stats[].category | 활동 이름 |
| stats[].count | 현재 활동 수치 |
| stats[].level | B의 현재 표시 단계 |
| stats[].color | B가 제공한 상태 색상 |
| stats[].id/name/icon/slot | 해당 표현 자산을 연결할 ID·이름·임시 아이콘·위치 |

C는 B의 count/level/color를 이용해 자산을 연결합니다. 게임 규칙을 화면에서 다시 계산하지 않습니다.
현재 B 원본에는 표정/기분/동작 상태 코드가 없으므로 A가 임의의 코드를 만들어 전달하지 않았습니다.
이 값들이 B에서 추가되면 공통 규약에 정의한 후 C가 해당 표정/동작 자산을 연결합니다.
이전 `effects`는 호환용이며 새 통합 화면에서는 `stats`를 사용합니다.

분석 후 stat_status=applied이면 캐릭터를 다시 조회합니다.
skipped는 판단 보류이며 오류나 스탯 획득으로 표시하지 않습니다.
사용자가 입력한 글·닉네임·키워드는 textContent 등으로 표시해 HTML로 실행하지 않습니다.

## main의 Phaser 초안 병합

main의 `774b44d` 커밋이 공통 frontend/shared/main.js를 Phaser 초안으로 바꿨습니다.
A 통합 진입점과 충돌하여 C의 소스를 frontend/characters/phaser-draft.js에 원문 그대로 보존했습니다.
공통 진입점은 접속/최초 설정/통합 기록 API 흐름을 유지합니다.
초안의 `import Phaser from 'phaser'`에는 별도 Phaser 의존성/빌드 환경이 필요합니다.
현재 root 화면은 이 초안을 자동 실행하지 않습니다. C의 게임 화면 연결 단계에서 실행 환경과 mount 위치를 연결합니다.
이 초안의 고정 책 소품과 이동 연출을 실제 사용자 스탯으로 간주하지 않습니다.
