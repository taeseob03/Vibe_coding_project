# 캠퍼스 캐릭터 앱

A의 계정·캐릭터 저장 기능과 B의 사진/글 Gemini 분석·스탯 계산을 연결한 통합 개발 앱입니다.
C는 이 API를 사용해 게임 화면과 캐릭터 표현을 제작합니다.
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
