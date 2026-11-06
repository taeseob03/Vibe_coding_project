# 캠퍼스 캐릭터 앱

대학생활 기록을 분석해 캐릭터 효과를 모으는 웹앱의 공동 개발 환경입니다.
개발 계획 원문은 [campus-app-development-plan.md](campus-app-development-plan.md)에 보존했습니다.

## 빠른 시작

Python 3.12 이상과 Git이 필요합니다. 현재 프런트엔드는 빌드 없는 HTML/CSS/JavaScript이므로 Node.js가 필요하지 않습니다.
모든 명령은 저장소 루트에서 실행합니다.

```bash
git clone https://github.com/taeseob03/Vibe_coding_project.git
cd Vibe_coding_project
make setup
make migrate
make dev
```

- 화면: http://127.0.0.1:8000
- API 문서: http://127.0.0.1:8000/docs
- 상태 확인: http://127.0.0.1:8000/health
- 검증: `make check`
- 서버 종료: `Ctrl+C`

`make setup`은 `.venv`를 만들고 고정 버전 의존성을 설치하며, 기존 `.env`가 없을 때만 `.env.example`을 복사합니다.
새 환경 설치에는 인터넷이 필요합니다. 각 개발자는 별도 `.env`와 SQLite DB를 사용합니다.

### Windows PowerShell 또는 make가 없는 환경

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements-dev.lock
.venv/Scripts/python scripts/init_env.py
.venv/Scripts/python -m alembic upgrade head
.venv/Scripts/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# 별도 터미널에서 검증
.venv/Scripts/python -m ruff check .
.venv/Scripts/python -m ruff format --check .
.venv/Scripts/python -m pytest -q
```

macOS/Linux에서 make 없이 실행할 때는 위의 `python`을 `python3`로, `.venv/Scripts/python`을 `.venv/bin/python`으로 바꿉니다.

## 역할별 구조

```text
backend/
  app/
    accounts/       A: 로그인·사용자·최초 설정·공통 인증 의존성
    characters/     A: 캐릭터·효과 지급 함수
    records/        B: 기록 모델·API·분석 상태
    analysis/       B: 분석 스키마·임시/실제 AI 어댑터
    core/           공동: 환경 설정·DB·오류 응답
    main.py         공동: 라우터 등록·정적 화면 제공
  migrations/       공동: Alembic 스키마 이력
  tests/            API·권한·환경 검증
frontend/
  accounts/         A: 로그인·최초 설정 화면
  characters/       A: 기본 캐릭터 연결, 이후 B가 시각 표현 정리
  records/          B: 기록 작성·목록·결과 화면
  shared/           공동: API 호출·화면 진입점·공통 스타일
  assets/           B: 후속 Phaser·캐릭터 이미지 자산
scripts/            개발 설정 초기화
.github/            CI·PR 템플릿
```

## 현재 구현 범위

A의 첫 단계로 **아이디만 입력하는 접속**을 구현했습니다.
첫 입력은 계정 생성, 같은 아이디의 다음 입력은 기존 계정으로 접속합니다.
비밀번호·이메일 인증은 사용하지 않습니다. 아이디를 아는 사람은 같은 계정으로 들어갈 수 있습니다.
아이디는 한글·영문·숫자·밑줄 2~20자이며, 앞뒤 공백을 제거하고 영문 소문자로 통일합니다.

1. `make migrate` 후 `make dev`를 실행합니다.
2. 화면에서 아이디를 입력하고 시작하기를 누릅니다.
3. 닉네임(2~12자)을 저장하고 캐릭터 색상을 선택해 최초 설정을 완료합니다.
4. 기록을 작성하고 새로고침하거나 로그아웃 후 같은 아이디로 접속해 저장 상태를 확인합니다.
5. 다른 아이디로 접속하면 별도 계정의 기록 목록이 표시됩니다.

접속은 7일간 유지되며, 로그아웃하면 현재 브라우저의 서버 세션이 폐기됩니다.
브라우저에는 HttpOnly 쿠키를, DB에는 세션 토큰의 해시를 저장합니다.
개발 외 환경의 쿠키는 HTTPS 전용입니다.

기존 개발 환경에서 `.env`에 `DEV_AUTH_ENABLED=true`가 있으면 `false`로 바꾸세요.
B가 독립 개발 시 명시적으로 임시 인증을 켜는 기능은 유지합니다.
`DEV_AUTH_ENABLED=true`는 `APP_ENV=development`에서만 허용됩니다.
`.env`, DB, 업로드 파일은 Git에서 제외됩니다.

최초 설정은 별도 닉네임과 임시 캐릭터 색상(초록/파랑/노랑/분홍/보라)을 저장합니다.
입력란에서 벗어나거나 다음 단계로 이동할 때 임시 저장하고, 색상을 바꾸면 해당 선택도 저장합니다.
화면의 `임시 저장됨` 표시를 확인하면 다음 접속에서 저장된 단계부터 이어갈 수 있습니다.
설정 완료와 캐릭터 생성은 함께 저장되며, 반복/동시 완료 요청에도 계정당 캐릭터는 하나입니다.
완료 후 닉네임/색상 변경 화면은 후속 단계입니다.
A의 효과 지급 서버 함수는 공부→책, 교류→하트, 운동→아령, 문화→팔레트, 일상→별을 처리합니다.
새 기록마다 해당 효과 레벨이 1씩 증가하고, 같은 기록의 중복/동시 처리는 한 번만 지급합니다.
효과 목록은 캐릭터 조회와 기본 화면에서 표시합니다.
**B의 기록 분석 후 자동 호출은 아직 연결하지 않았으므로, 현재 글 저장만으로는 효과가 지급되지 않습니다.**
B의 연결 예제와 지급 실패 복구 방법은 [API 규약](docs/api-contract.md)에 있습니다.
다섯 효과를 함께 소유할 수 있으며 강화·중복 방지·실패 복구 규칙은 동일합니다.
현재 기록 분석은 입력과 무관한 고정 mock 응답입니다. 실제 AI·비동기 처리·분석 재시도는 B의 구현 대상입니다.
사진·칭호·라운지·Phaser도 후속 단계입니다. API 키 없이 실행됩니다.

## 협업 문서

- [Git 브랜치·pull/push·PR 절차](docs/collaboration.md)
- [공통 API·데이터·효과 연결 규약](docs/api-contract.md)
- [DB 마이그레이션·환경 관리](docs/development.md)
- [단계별 작업 목록](docs/tasks.md)

FastAPI 모듈 분리·테스트와 Alembic 구성은 공식 문서를 참고했습니다:
[FastAPI](https://fastapi.tiangolo.com/tutorial/bigger-applications/),
[테스트](https://fastapi.tiangolo.com/tutorial/testing/),
[Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

## B? ????? ???

[?? ?? ???](prototypes/records-analysis/README.md)?? Gemini ?? ???? ??? ??, ??? ?? ?? ??, ?? ??? ?????? ??? ? ????. ?? ??? ??? ? ??? ?? ?? ??? ?????. ?? ?? ?? ???DB?? ?? ???? ?????.
