# INUstagram

메인에서 왼쪽으로 넘기면 나와 친구의 게시물 피드, 오른쪽으로 넘기면 라운지로 이동합니다.
사진과 직접 쓴 글은 게시 시점부터 서버 DB에 저장하며 최신 업로드순으로 표시합니다.
친구의 게시물은 피드의 `친구 등록`에서 실제 계정의 닉네임 검색 → 요청 → 상대 수락 후 볼 수 있습니다.
기존 라운지의 예제 초대는 이 친구 등록과 별개입니다.

A의 계정·캐릭터 저장 기능과 B의 사진/글 Gemini 분석·스탯 계산을 연결한 통합 개발 앱입니다.
C는 이 API를 사용해 게임 화면과 캐릭터 표현을 제작합니다.
main에서 가져온 C의 Phaser 초안은 `frontend/characters/phaser-draft.js`에 원문 그대로 보존했습니다.
현재 공통 진입점은 접속/최초 설정/기록 연결을 유지하며, Phaser 설치·실행 및 실제 게임 화면 연결은 C와의 후속 단계입니다.
사용자가 제공한 원문은 [campus-app-development-plan.md](campus-app-development-plan.md)에 보존했으며,
현재 역할과 규약은 아래 문서를 기준으로 합니다.

## 실행

Python 3.12 이상과 Git이 필요합니다. 임시 확인 화면은 HTML/CSS/JavaScript이며 Node.js가 필요하지 않습니다.
현재 통합 구현은 `feature/account-character` 브랜치에 있습니다.

```bash
git clone --branch feature/account-character https://github.com/taeseob03/Vibe_coding_project.git
cd Vibe_coding_project
make setup
make migrate
```

루트 `.env`에 본인의 `GEMINI_API_KEY`를 입력합니다. `GEMINI_MODEL`은 B가 설정한 모델명입니다.
기존 `.env`를 덮어쓰지 말고 빠진 항목만 `.env.example`을 참고해 추가하세요.
`DEV_AUTH_ENABLED=false`로 설정하면 아이디 접속 화면이 표시됩니다.

```bash
make dev
```

- 확인 화면: http://127.0.0.1:8000
- API 문서: http://127.0.0.1:8000/docs
- 상태 확인: http://127.0.0.1:8000/health
- 서버 종료: `Ctrl+C`

코드나 `.env` 변경 뒤 서버를 다시 시작합니다.
사진/글 분석은 Google Gemini에 입력을 전송합니다. 키가 없으면 원본 기록을 보존한 채 분석 실패로 안내합니다.
키를 설정하고 다시 시작한 뒤 해당 기록의 재시도 버튼으로 분석할 수 있습니다.

### make가 없는 환경

Windows PowerShell 예시입니다. macOS/Linux에서는 `python`을 `python3`,
`.venv/Scripts/python`을 `.venv/bin/python`으로 바꿉니다.

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.lock
.venv/Scripts/python scripts/init_env.py
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 역할과 현재 흐름

| 담당 | 역할 |
|---|---|
| A | 계정·인증·캐릭터, 사용자 소유권 검사, 분석 결과와 스탯의 저장·조회, 공통 연결 API |
| B | 사진/글 입력 검증, Gemini 키워드·활동 분석, 스탯 계산·상태 규칙 |
| C | 게임 화면·캐릭터·소품·표정·동작·애니메이션 표현 |

1. 아이디만으로 접속합니다. 처음 쓰는 아이디는 새 계정, 같은 아이디는 기존 계정입니다.
2. 별도 닉네임과 임시 캐릭터 색상을 선택합니다. 임시 저장 후 다시 이어갈 수 있습니다.
3. 사진 한 장 또는 글을 저장합니다. 원본은 인증된 사용자에게 연결됩니다.
4. B의 Gemini 분석을 실행하고 대기/진행/완료/실패를 표시합니다.
5. B가 계산한 스탯 결과를 A가 사용자 캐릭터에 저장하고 화면에 전달합니다.
6. 분석 실패는 원본으로 재시도하며, 스탯 저장 실패는 저장된 분석으로 재처리합니다.

현재 B 코드의 스탯은 활동별 횟수와 그에 따른 표시 단계·색상입니다.
술·공부·연애·운동의 분류와 계산식은 B의 원본을 유지했습니다.
A가 이전에 만든 ‘새 기록마다 소품 레벨 +1’은 새 통합 흐름에서 사용하지 않습니다.
구체적인 표정 전환 코드는 현재 B에 없으므로 A가 임의로 추가하지 않았습니다.
C는 [화면 연결 규약](docs/frontend-contract.md)의 스탯 필드를 사용할 수 있습니다.

접속 아이디는 한글·영문·숫자·밑줄 2~20자, 닉네임은 2~12자입니다.
아이디만으로 접속하므로 해당 아이디를 아는 사람은 같은 계정을 사용할 수 있습니다.
세션은 기본 7일간 유지되며 현재 브라우저 로그아웃 시 폐기합니다.
사진은 JPG/PNG/WEBP 한 장, 최대 10MB·2,500만 픽셀입니다. 글은 최대 5,000자입니다.
현재 개발용 SQLite DB가 원본 사진도 보관하며 사진 조회에 소유권을 확인합니다.
사진·글 삭제/수정과 보상 회수, 칭호, 라운지, 최종 디자인은 후속 단계입니다.

## 구조와 B 원본 활용

### 로그인부터 새 웹 앱까지 한 주소에서 로컬 테스트

현재 작업 브랜치에는 개발 전용 연결 모드가 있습니다.
로그인 → 닉네임·학년·학과 → 성별·머리 길이·머리 색 → 메인 캐릭터 → 게시·AI 분석 → 라운지를 같은 서버에서 시험합니다.

Windows PowerShell에서 저장소 루트 기준:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
# .env에 GEMINI_API_KEY와 GEMINI_MODEL을 설정한 뒤 실행
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_local_web.ps1
```

http://127.0.0.1:8001 을 엽니다. 기존 화면이 남으면 Ctrl+F5로 갱신합니다.
실행 스크립트는 로컬 프로세스에서만 개발 인증 우회는 끄고 LOCAL_WEB_PREVIEW_ENABLED를 켭니다.
일반 기본 실행에서 이 옵션은 false이며, 운영 환경에서는 연결 모드가 등록되지 않습니다.

캐릭터 설정 완료 후 `/app`으로 이동합니다. 새 메인에 선택한 닉네임과 색상이 표시됩니다.
게시의 스택은 로그인한 계정의 characters.stats에 저장되어 `/characters/me`에서도 동일하게 조회됩니다.
기존 사용자별 시제품 스택은 최초 연결 시 기준값으로 이어받으며 이전 공용 시제품 기록은 가져오지 않습니다.
라운지 초대는 브라우저에 계정별로 저장되는 예제이며 수락 테스트 창을 사용합니다.
피드의 친구 등록은 실제 계정과 서버 DB를 사용합니다. 나/친구/전체 필터와 이전 게시물 더 보기를 지원합니다.
라운지의 내 캐릭터는 실제 게시 스택, 예제 친구는 예제 스택을 표시합니다.
라운지 배경은 도트 캠퍼스 광장이며 캐릭터는 메인과 같은 픽셀 자산으로 자동 보행합니다.
내 성별·머리·학과 과잠은 저장된 프로필을 사용하고, 예제 친구는 각기 다른 외형을 사용합니다.
걷는 동안 팔다리·상하 움직임과 이동 방향을 반영하며 멈추면 기본 자세로 돌아옵니다.

이 모드는 A의 인증/프로필을 재사용하는 **로컬 검증용 연결**입니다.
두 게시 API(`/api/keywords`, `/api/records`) 모두 A의 activity_records와 characters.stats를 사용합니다.
기존 사용자별 SQLite는 이전 기록의 분석 캐시/기준값 호환용이며 화면의 최신 스택은 계정 DB가 기준입니다.
술은 운동 스택을 1 감소시키며 최솟값은 0입니다. 재시도는 스택을 중복 반영하지 않습니다.
키는 서버의 `.env`에서만 읽고 브라우저에는 보내지 않습니다.
게시 사진·원문·분석 상태와 친구 관계는 계정 DB의 web_posts/web_friend_requests에 저장합니다.
사진은 공개 정적 파일로 제공하지 않으며 본인 또는 수락한 친구만 인증 후 조회합니다.
기존 시제품에서 원본을 저장하지 않았던 과거 사진은 복구할 수 없습니다. 새로 게시한 사진부터 피드에 남습니다.

최신 main의 픽셀 캐릭터 렌더러가 메인에 연결되어 있습니다. C의 독립 미리보기는 `/preview/character.html`입니다.
표시 단계는 기존 1~4회/5~9회/10회 이상 규칙을 유지하고 C 렌더러에 맞춰 변환합니다.
실제 최초 설정에서도 성별·학년·학과·머리 길이·머리 색을 선택하며 도트 캐릭터 미리보기에 바로 반영합니다.
선택값은 계정 DB에 임시/완료 저장되고 다시 로그인해도 유지됩니다. 과잠은 선택한 학과에 맞게 자동 적용됩니다.
이미 만든 계정은 메인의 `캐릭터 설정`에서 외형·학년·학과를 저장할 수 있으며 활동 기록·스택은 그대로 유지됩니다.

```text
backend/app/accounts/       A: 접속·최초 설정
backend/app/characters/     A: 캐릭터·스탯 조회 (이전 effects 구현은 호환용)
backend/app/integrations/   A: B 결과의 사용자별 저장·작업 상태·재시도·연결 API
backend/app/records/        초기 mock API, 호환용으로 보존
prototypes/records-analysis/app/
  analysis.py              B: Gemini 분석 원본
  effects.py               B: 활동별 표시 정보 원본
  progress.py              B: calculate_progress / eligible_category 공통 계산 함수
frontend/                  C가 교체할 기능 확인용 화면
```

B 브랜치를 merge하여 원본과 Git 이력을 보존했습니다.
B의 Python 소스를 `campus_records_prototype` 패키지로 등록하여 공통 앱에서 직접 사용합니다.
기존 B의 독립 실행 방법은 [시제품 문서](prototypes/records-analysis/README.md)를 참고하세요.
B의 로컬 공용 DB를 A의 사용자별 DB로 자동 복사하지는 않습니다.

현재 작업 실행은 단일 프로세스 개발 서버의 BackgroundTasks를 사용합니다.
재시작 시 중단된 분석을 failed로 표시하며 사용자가 재시도합니다.
여러 서버/워커를 운영할 때의 작업 소유권·큐 확장은 별도 단계입니다.

## 검증과 협업

```bash
make check
# B 원본 테스트는 해당 폴더에서 별도로 실행합니다.
cd prototypes/records-analysis
../../.venv/bin/python -m pytest --disable-plugin-autoload -q
```

자동 테스트에서는 Gemini 응답을 대체하므로 API 키 없이 실행됩니다.
실제 모델의 응답 품질과 계정의 모델 접근 여부는 유효한 키를 설정해 별도로 확인합니다.
브라우저 E2E 자동화는 아직 없습니다. GitHub CI는 통합 앱과 B 원본 테스트·마이그레이션을 확인합니다.

- [공통 API·저장 규약](docs/api-contract.md)
- [C의 화면 연결 규약](docs/frontend-contract.md)
- [설치·DB·환경 관리](docs/development.md)
- [Git 협업 절차](docs/collaboration.md)
- [진행 상황](docs/tasks.md)

사용자가 다음 단계를 요청할 때만 다음 기능을 시작합니다.
단계 완료 후 커밋·pull·필요한 병합/검증·A 브랜치 push를 진행합니다.
