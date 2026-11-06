# 개발 환경과 DB 변경

## 설치와 의존성

Python 3.12를 기준으로 검증합니다. `make setup` 뒤 `make migrate`, `make dev`를 실행합니다.
프로젝트는 editable 설치되어 `backend/app`의 수정이 바로 반영됩니다.
프런트도 같은 FastAPI 서버에서 제공하므로 별도 서버나 CORS 설정이 필요하지 않습니다.

`pyproject.toml`은 직접 의존성과 도구 설정, `requirements-dev.lock`은 검증한 전체 버전 목록입니다.
lock 끝의 `-e .`는 프로젝트를 editable로 설치합니다.
직접 의존성을 바꿀 때 공통 파일 변경을 공유한 뒤 다음 순서로 갱신합니다.

```bash
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python scripts/lock_dependencies.py
make check
```

Windows는 `.venv/bin/python`을 `.venv/Scripts/python`으로 바꿉니다.
lock은 버전 고정 목록이며 플랫폼별 wheel이나 해시까지 고정하지는 않습니다.
Phaser·OpenAI SDK는 해당 구현 단계에서 추가하여 의존성을 최소화합니다.

## 로컬 DB

`backend/data/campus.db`는 각 개발자의 SQLite DB입니다. DB 파일 대신 마이그레이션을 공유합니다.
서버가 자동으로 테이블을 만드는 방식은 사용하지 않습니다.

```bash
make migrate
.venv/bin/python -m alembic current
# 모델 수정 후 새 스키마 변경 파일 생성
.venv/bin/python -m alembic revision --autogenerate -m "add character profile"
# 생성된 코드를 검토하고 적용
make migrate
.venv/bin/python -m alembic check
```

`migrations/env.py`에 새 모델 모듈을 import해야 autogenerate가 해당 테이블을 인식합니다.
마이그레이션 파일을 PR에 포함합니다. 이미 공유된 버전 파일을 수정하지 않고 새 버전을 만듭니다.
두 브랜치에서 head가 갈라지면 상대 변경을 merge한 뒤 `alembic heads`로 확인하고
`alembic merge heads -m "merge schema heads"`로 병합 revision을 추가합니다.
모델 코드 충돌도 함께 해결한 뒤 `upgrade head`와 `alembic check`를 실행합니다.
`downgrade`는 데이터가 지워질 수 있으므로 테스트 DB에서 먼저 검증합니다.

기본 DB는 로컬 개발용입니다. 공용 운영 DB와 작업 큐는 배포/실제 AI 단계에서 정합니다.
동기 mock 환경은 백그라운드 작업·동시 분석·복구를 구현하지 않습니다.

## 설정과 인증 교체

- `.env`는 로컬 비밀 설정이며 Git에 올리지 않습니다.
- `.env.example`만 공유합니다. API 키는 서버 환경에서만 읽습니다.
- `accounts/dependencies.py`가 B의 인증 연결점입니다. B는 이를 재사용합니다.
- 임시 인증은 `APP_ENV=development`, `DEV_AUTH_ENABLED=true` 모두 필요합니다.
- 실제 계정 2개 검증은 실제 인증 구현 후 수행합니다. 현재는 테스트에서 dependency override로 소유자 분리를 검증합니다.

## 검증과 CI

`make check`는 Ruff lint/format과 pytest를 실행합니다.
테스트는 임시 파일 DB에 Alembic을 적용하고 기록 저장/소유권/입력 검증/운영 임시 인증 차단을 확인합니다.
GitHub Actions에서는 별도 DB로 migration upgrade/downgrade와 모델 일치도 확인합니다.
현재 프런트엔드는 기본 HTML/JS이며 브라우저 E2E 자동화는 아직 없습니다.

공식 참고:
[FastAPI 모듈 구성](https://fastapi.tiangolo.com/tutorial/bigger-applications/),
[FastAPI 테스트](https://fastapi.tiangolo.com/tutorial/testing/),
[Alembic 마이그레이션](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
