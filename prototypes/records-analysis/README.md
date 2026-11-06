# 캠퍼스 앱 · 캐릭터와 라운지

메인 캐릭터 → 게시(글·사진) → 키워드·활동 분석 → 캐릭터 성장, 라운지 → 닉네임 검색 → 초대·수락 흐름을 제공하는 웹앱 시제품입니다.
게시 분석은 실제 Gemini와 로컬 누적 DB를 사용합니다. 친구·초대는 가상 사용자와 브라우저 저장을 사용하는 예제 모드입니다.
로그인·최초 캐릭터 생성 완료 후의 화면을 가정합니다. 최종 캐릭터와 배경은 나중에 디자인 자산으로 교체합니다.

서버 담당에게 전달할 경로·응답 형식·권한·통합 순서는 [앱 서버 연결 안내](docs/app-server-integration.md)에 정리했습니다.

공동 저장소의 `scripts/run_local_web.ps1`을 사용하면 A의 로그인·캐릭터 설정 후 이 화면으로 연결됩니다.
그 모드에서는 실제 계정 ID·닉네임·색상을 사용하고 스택 DB와 예제 초대 저장도 계정별로 분리합니다.
아래의 단독 실행 방법은 기존 로그인 없는 시제품 실행입니다. 한 주소 연결 안내는 [공동 개발 안내](../../docs/development.md)를 참고하세요.

## 실행 (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

.env 파일의 GEMINI_API_KEY= 뒤에 본인의 키를 입력하고 저장하세요.
이미 .env가 있다면 복사하지 말고 기존 파일을 수정하세요. 키를 채팅이나 Git에 올리지 마세요.
GEMINI_MODEL 기본값은 gemini-3.5-flash-lite이며 이미지 입력과 구조화 출력을 지원하는 접근 가능한 모델로 변경할 수 있습니다.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 http://127.0.0.1:8000 을 엽니다.
.env 변경 후 서버를 재시작하세요. 서버 터미널에서 Ctrl+C로 종료합니다.
분석 요청은 실제 Gemini API를 호출합니다. 무료 티어도 요청 한도가 있으며, 유료 프로젝트는 요금이 발생할 수 있습니다.

## 입력과 출력

- 글: 최대 5,000자
- 이미지: JPG/PNG/WEBP 정지 이미지 한 장, 최대 10MB·2,500만 픽셀
- 둘 중 하나 이상 필요합니다. 원본 글·사진은 저장하지 않으며, 분석 결과(요약 포함)·기록 ID·입력 해시를 data/progress.sqlite3에 저장합니다.
- 전송된 내용은 Google Gemini에서 처리하며 무료/유료 티어에 따라 Google의 데이터 처리 정책이 적용됩니다.

POST /api/keywords (multipart/form-data)
- text: 선택 문자열
- image: 선택 파일
- record_id: 선택 UUID. 같은 기록 재시도에는 같은 ID를 전달하세요. 생략하면 새 기록으로 처리합니다.

응답 예시:
```json
{
  "keywords": ["도서관", "시험 공부", "친구"],
  "summary": "친구와 도서관에서 시험을 준비했어요.",
  "category": "공부",
  "category_keywords": ["도서관", "시험 공부"],
  "category_reason": "시험 준비가 주된 활동입니다.",
  "needs_review": false,
  "character_effect": {"id": "study_book", "name": "책 소품", "icon": "📚", "slot": "hand"},
  "record_id": "서버가 반환하는 UUID",
  "awarded": true,
  "progress": [{"category":"공부","id":"study_book","name":"책 소품","icon":"📚","slot":"hand","count":1,"level":1,"color":"#f9a8d4"}]
}
```

입력에서 근거를 찾지 못하면 keywords는 빈 배열일 수 있습니다.
분류는 추출된 키워드에 근거한 술·공부·연애·운동 중 하나이며 관련 키워드가 없으면 null입니다. AI 호출 한 번으로 키워드·요약·분류·분류 근거 키워드·이유를 받습니다.
app/effects.py에서 서버가 분류를 소품 ID에 연결합니다. AI가 소품이나 지급 규칙을 결정하지 않습니다.
술 → drink_mug, 공부 → study_book, 연애 → love_hearts, 운동 → exercise_dumbbell.
근거가 부족하면 category=null과 needs_review=true를 반환하고 누적하지 않습니다.
여러 활동이 동등하게 강조되어 판단이 애매한 경우에도 needs_review=true입니다.
needs_review=true인 기록도 누적하지 않습니다. 확실한 분류는 기록 1건당 1회만 누적하며 키워드 개수는 누적량에 영향을 주지 않습니다.
1~4회 Lv.1, 5~9회 Lv.2, 10회 이상 Lv.3입니다. 하트 색상은 연분홍 → 진분홍 → 빨강으로 바뀝니다.
확정된 술 기록은 술 +1과 운동 스택 -1을 함께 적용합니다. 운동은 0 아래로 내려가지 않습니다.
운동이 0일 때 마신 술은 이후 운동에 영향을 주지 않습니다. 기록 최초 반영 순서대로 계산합니다.
운동 5 → 술 기록 → 운동 4가 되면 운동 효과도 Lv.2 → Lv.1로 내려갑니다. 0이면 운동 소품이 사라집니다.
기존 로컬 기록도 같은 순서 규칙으로 재계산하며 원본 기록은 삭제하지 않습니다.
응답의 stack_changes는 이번에 실제 적용한 변화(예: {"술":1,"운동":-1})입니다. 재시도 응답은 {}이며 추가 차감하지 않습니다.
GET /api/progress는 네 활동의 현재 횟수·레벨·표시 정보를 반환합니다. 위 응답 예시는 progress 중 한 항목만 표시했습니다.
동일 record_id는 재요청 시 AI를 재호출하지 않으며, 동시 요청에도 1회만 누적합니다. ID를 바꿔 제출하면 별도 기록입니다.
실제 분류 테스트: .\\.venv\\Scripts\\python.exe -X utf8 check_categories.py (API 호출 7회, 임시 DB로 실제 사용자 누적과 분리).
API 문서: http://127.0.0.1:8000/docs

## A의 앱에 통합

- app/analysis.py: 독립 분석 함수 extract_keywords(text, image_bytes, mime)
- app/routes.py: 입력 검증·오류 처리와 /api/keywords 라우터
- app/main.py: 로컬 실행 진입점
- app/progress.py: 로컬 SQLite 누적 저장. PROGRESS_DB로 테스트 DB 경로 변경 가능
- static/: 기능 확인용 화면

A의 FastAPI 앱에서 router를 include_router로 등록하거나 B의 기록 처리 서비스에서
extract_keywords를 호출하면 됩니다. 기존 .env 설정과 인증 체계는 A의 앱에 맞추세요.
현재 엔드포인트는 인증이 없는 로컬 시제품입니다. 배포 전에 A의 인증·요청 제한을 연결하세요.
통합 시 로컬 공용 캐릭터 대신 인증된 사용자 ID를 기록과 연결하고, A의 캐릭터 저장·효과 지급 함수로 교체하세요.

## 테스트

### 라운지 시제품

서버 실행 후 http://127.0.0.1:8000 의 메인 화면 아래 `게시` 버튼을 사용합니다.
메인에서 오른쪽으로 스와이프하거나 상단 `라운지` 탭을 누릅니다. 반대 방향은 메인으로 돌아옵니다.
내 라운지에는 처음 나만 표시됩니다. `친구 초대`에서 민지·준호·서연을 검색하고 초대를 보냅니다.
창을 닫고 `초대 수락 테스트 → 친구의 수신함 열기`에서 수락하면 그 친구가 나타납니다.
민지와 준호가 수락하면 3명의 캐릭터가 자동으로 움직입니다. 이동 조작 버튼은 없습니다.
받은 초대에는 민지가 보낸 예제 초대 1건이 있어 다른 라운지 참여도 테스트할 수 있습니다.
내 캐릭터는 실제 분석 누적을 표시하고, 친구는 예제 활동 횟수를 사용합니다.
초대·멤버십은 같은 브라우저에 저장됩니다. 다른 기기의 실제 친구와 위치를 공유하는 기능은 서버 연결 후 구현합니다.

이동 엔진 테스트 (Node.js 18 이상):
```powershell
node --test tests/lounge-engine.test.mjs
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

화면 흐름·친구 초대 상태 전이 테스트 (Node.js 18 이상, 실제 AI 호출 없음):

```powershell
npm ci
npm test
```

jsdom으로 스와이프 이벤트, 검색·초대·수락·멤버 반영, 게시 실패/재시도·사진 입력과 캐릭터 갱신을 검증합니다.
실제 브라우저의 레이아웃·터치 조작은 별도로 확인해야 합니다.

테스트는 AI 응답을 대체하여 세 가지 입력, 입력 제한, API 오류, 요청 형식을 확인합니다.
실제 모델의 추출 품질·계정 접근 여부는 유효한 키를 설정하고 세 입력 방식으로 직접 확인해야 합니다.

## 참고한 공식 문서

- [Google Gen AI SDK](https://googleapis.github.io/python-genai/)
- [Gemini API 요금 및 무료 티어](https://ai.google.dev/gemini-api/docs/pricing)

