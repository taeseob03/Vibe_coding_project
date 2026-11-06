# 캠퍼스 캐릭터 앱

A의 계정·저장, B의 Gemini 사진/글 분석·스탯 규칙, C의 Phaser 캐릭터 초안을 하나의 실행 앱으로 통합했습니다.
아이디 접속 → 캐릭터 생성 → 게시 → 스탯·표정·소품 변화 → 칭호 → 친구와 공유 라운지까지 사용할 수 있습니다.
C의 원본 초안은 `frontend/characters/phaser-draft.js`에 보존하고 실행 화면은 `frontend/game/`에 연결했습니다.
사용자가 제공한 원문은 [campus-app-development-plan.md](campus-app-development-plan.md)에 보존했으며,
현재 역할과 규약은 아래 문서를 기준으로 합니다.

## 실행

Python 3.12 이상과 Git이 필요합니다. 게임 화면은 로컬 Phaser 라이브러리를 사용하며 실행에 Node.js 빌드가 필요하지 않습니다.
검증한 통합 구현은 main에 반영합니다. 개별 작업은 기능 브랜치에서 진행합니다.

```bash
git clone --branch main https://github.com/taeseob03/Vibe_coding_project.git
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

현재 B 코드의 스탯은 활동별 횟수와 그에 따른 표시 단계·색상입니다. 술은 운동 스탯을 1 줄이며 0 아래로 내려가지 않습니다. 최초 반영 순서를 저장해 미래 운동을 미리 차감하지 않습니다.
술·공부·연애·운동의 분류와 계산식은 B의 원본을 유지했습니다.
A가 이전에 만든 ‘새 기록마다 소품 레벨 +1’은 새 통합 흐름에서 사용하지 않습니다.
B의 character_state 함수가 현재 스탯의 표시 상태를 정하고, Phaser가 안경·눈·입·소품으로 표현합니다.
C의 화면은 [화면 연결 규약](docs/frontend-contract.md)의 스탯·표정 상태 필드를 사용합니다.

- **실제 분석:** `.env`에 Gemini 키를 설정하고 사진/글을 게시합니다.
- **샘플 체험:** 접속 화면의 체험 계정 또는 상단 샘플 체험 링크를 사용합니다. 화면과 기록에 샘플로 표시하며 AI 분석을 가장하지 않습니다.
- **칭호:** 첫 활동, 서로 다른 5일 공부, 서로 다른 활동 3종으로 획득하고 대표 칭호를 선택합니다.
- **친구/라운지:** 다른 계정의 닉네임 검색 → 초대 → 수신자 수락 → 참여. 좌표와 접속 상태는 인증된 WebSocket으로 공유됩니다.
- **두 계정 확인:** 일반 창과 시크릿 창 등 별도 브라우저 세션으로 각각 접속하세요. 같은 브라우저의 탭은 접속 쿠키를 공유합니다.

접속 아이디는 한글·영문·숫자·밑줄 2~20자, 닉네임은 2~12자입니다.
아이디만으로 접속하므로 해당 아이디를 아는 사람은 같은 계정을 사용할 수 있습니다.
세션은 기본 7일간 유지되며 현재 브라우저 로그아웃 시 폐기합니다.
사진은 JPG/PNG/WEBP 한 장, 최대 10MB·2,500만 픽셀입니다. 글은 최대 5,000자입니다.
현재 개발용 SQLite DB가 원본 사진도 보관하며 사진 조회에 소유권을 확인합니다.
기록 수정·삭제 및 재계산 정책, 고급 자산 교체, 여러 서버 운영은 선택 확장입니다. 현재는 단일 서버에서 동작합니다.

## 구조와 B 원본 활용

```text
backend/app/accounts/       A: 접속·최초 설정
backend/app/characters/     A: 캐릭터·스탯 조회 (이전 effects 구현은 호환용)
backend/app/integrations/   A: B 결과의 사용자별 저장·작업 상태·재시도·연결 API
backend/app/records/        초기 mock API, 호환용으로 보존
prototypes/records-analysis/app/
  analysis.py              B: Gemini 분석 원본
  effects.py               B: 활동별 표시 정보 원본
  progress.py              B: calculate_progress / eligible_category 공통 계산 함수
frontend/game/             통합 게임·Phaser·게시·칭호·친구/라운지
frontend/vendor/           고정 Phaser와 한글 글꼴·라이선스
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
브라우저 검사:

```bash
.venv/bin/python -m playwright install chromium
.venv/bin/python scripts/verify_game.py
# 실제 Gemini 사진 분석 1회를 포함하려면 --live-ai 추가
```

검증은 별도 임시 DB에서 실행하여 실제 사용자 기록을 변경하지 않습니다.
CI는 통합 앱·B Python/JS 원본·브라우저·마이그레이션을 검사합니다.

- [공통 API·저장 규약](docs/api-contract.md)
- [C의 화면 연결 규약](docs/frontend-contract.md)
- [설치·DB·환경 관리](docs/development.md)
- [Git 협업 절차](docs/collaboration.md)
- [진행 상황](docs/tasks.md)

현재 사용자 요청에 따라 통합 작업과 main 반영·서버 실행까지 자율 진행합니다. 이후 수정도 커밋·pull·필요한 병합/검증·push 절차로 관리합니다.

## 서버 운영과 범위

이 실행 구성은 Python 프로세스 1개와 로컬 SQLite DB를 사용하는 개발용 게임입니다.
중단된 분석은 원본으로 재시도하고, 라운지 WebSocket은 자동 재연결합니다.
호스팅 환경에서 여러 워커/서버를 사용할 때는 공유 큐·방 상태 저장을 별도로 확장합니다.
게임/게시 API 키를 브라우저에 전달하지 않습니다. `.env`와 DB 파일은 Git에서 제외합니다.

상세 실행·검증 결과는 [통합 게임 안내](docs/game-release.md)를 참고하세요.
