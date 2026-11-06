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

환경 확인용 `/auth/me`, 기록 작성·목록·상세, 고정 mock 분석과 SQLite 저장이 실행됩니다.
임시 사용자는 `.env`의 고정 UUID로 결정하며 사용자 입력으로 바꾸지 않습니다.
목록·상세·재시도 진입점에 소유권 검사를 적용했습니다.

실제 회원가입·로그인·최초 설정·캐릭터·효과 지급은 A의 구현 대상입니다.
캐릭터 조회와 분석 재시도는 명시적인 `501 NOT_IMPLEMENTED`를 반환합니다.
현재 분석은 저장 요청 안에서 고정 결과를 반환합니다. 실제 글 분류, 비동기 상태 전이,
실패·재시도·서버 재시작 복구는 B가 구현해야 합니다. 따라서 계획의 첫 독립 마일스톤 전체가 완료된 상태는 아닙니다.
사진·칭호·라운지·Phaser도 후속 단계입니다. OpenAI SDK/호출은 아직 추가하지 않았으며 API 키 없이 실행됩니다.

`DEV_AUTH_ENABLED=true`는 `APP_ENV=development`에서만 허용됩니다.
실제 인증을 연결하기 전에는 개발 서버를 로컬에서 사용합니다. `.env`, DB, 업로드 파일은 Git에서 제외됩니다.

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
