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
Gemini SDK는 통합 의존성에 포함되어 있습니다. 현재 도트 렌더러는 Canvas를 사용합니다.

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
- `accounts/dependencies.py`가 B의 인증 연결점입니다. B는 이를 재사용합니다. 현재는 아이디 접속의 DB 세션 쿠키를 검증합니다.
- 임시 인증은 `APP_ENV=development`, `DEV_AUTH_ENABLED=true` 모두 필요합니다.
- 두 아이디의 실제 접속으로 기록·프로필·캐릭터 소유자 분리를 테스트합니다. B의 명시적 임시 인증 옵션도 유지합니다.

## 검증과 CI

`make check`는 Ruff lint/format과 pytest를 실행합니다.
테스트는 임시 파일 DB에 Alembic을 적용하고 기록 저장/소유권/입력 검증/운영 임시 인증 차단을 확인합니다.
GitHub Actions에서는 별도 DB로 migration upgrade/downgrade와 모델 일치도 확인합니다.
현재 프런트엔드는 기본 HTML/JS이며 브라우저 E2E 자동화는 아직 없습니다.

공식 참고:
[FastAPI 모듈 구성](https://fastapi.tiangolo.com/tutorial/bigger-applications/),
[FastAPI 테스트](https://fastapi.tiangolo.com/tutorial/testing/),
[Alembic 마이그레이션](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

## 아이디 접속·최초 설정·효과 지급

`.env.example`의 `DEV_AUTH_ENABLED=false`가 기본입니다. 기존 `.env`도 false로 바꾸면 접속 화면이 표시됩니다.
접속 아이디를 알면 누구나 같은 계정을 사용할 수 있으며 비밀번호/이메일 인증은 없습니다.
세션 토큰은 HttpOnly 쿠키에, 해시는 서버 DB에 저장됩니다.
`SESSION_MAX_AGE`는 초 단위로 기본 604800(7일), 허용 범위 60~2592000입니다.
개발 외 환경의 쿠키에는 Secure가 적용되므로 HTTPS가 필요합니다.
다른 Origin의 변경 요청은 차단하며 프록시 배포 시 서버가 인식하는 scheme/host를 외부 주소와 맞춥니다.

`0002`는 아이디/세션, `0003`은 최초 설정/캐릭터, `0004`는 효과/지급 내역을 추가합니다.
기존 사용자와 기록을 보존합니다. 기존 임시 사용자의 기록을 새 아이디로 자동 이전하지 않습니다.
닉네임은 2~12자로 별도 입력하고 임시 캐릭터 색상을 선택합니다.
설정 완료 상태와 캐릭터 생성을 하나의 트랜잭션으로 저장하며 계정당 캐릭터는 하나입니다.
캐릭터는 CSS 임시 도형입니다. 최종 이미지/Phaser는 B의 디자인 단계에서 교체합니다.

효과는 공부→책, 교류→하트, 운동→아령, 문화→팔레트, 일상→별입니다.
첫 획득은 1레벨이며 새 기록마다 해당 효과가 1레벨씩 오릅니다.
효과 호출 전에 B가 기록과 분석을 commit해야 합니다. A의 함수가 자체 세션으로 원자적으로 지급합니다.
기록/캐릭터 잠금과 기록별 지급 PK로 동시 처리·중복을 방지합니다. 검증 DB는 SQLite입니다.
B의 분석 완료 후 자동 호출은 아직 연결하지 않았습니다.
호출 순서와 실패 복구 예제는 [API 규약](api-contract.md)을 참고하세요.
쿠키 동작은 [Starlette 공식 문서](https://starlette.dev/responses/)를 참고했습니다.

## 단계 진행·Git 동기화

사용자가 다음 단계로 넘어가라고 명시적으로 요청할 때만 다음 단계의 구현을 시작합니다.
현재 단계 완료 후에는 검증된 변경을 로컬 커밋으로 보존하고 현재 기능 브랜치의 원격을 pull합니다.
공통 main의 변경도 필요 시 병합합니다. 충돌은 양쪽 기능을 보존하며 해결하고 변경이 생기면 다시 검증합니다.
원격 작업 브랜치가 없으면 origin/main을 pull하여 기반 변경만 반영합니다. push는 별도 요청 시 수행합니다.

### 캐릭터 초안과 로그인 진입점 병합

main의 `774b44d` 캐릭터 초안은 로그인 브랜치와 같은 `frontend/shared/main.js`를 교체했습니다.
초안의 내용을 `frontend/characters/phaser-draft.js`에 보존하고, 공통 진입점에는
로그인 → 최초 설정 → 캐릭터/기록 화면 연결을 유지했습니다.
현재 프런트는 번들러 없이 실행되므로 초안의 `import Phaser from 'phaser'`는 그대로 실행할 수 없습니다.
초안은 아직 로드하지 않으며, 디자인 단계에서 Phaser 의존성·배포 방식과 대상 컨테이너를 정한 뒤 연결합니다.
B 웹 앱의 자동 이동 라운지는 별도 시제품 폴더에서 기존 canvas 렌더러로 동작합니다.

## 한 주소에서 로컬 웹 흐름 검증

`LOCAL_WEB_PREVIEW_ENABLED=true`와 `APP_ENV=development`일 때만 개발 연결 라우터를 등록합니다.
`scripts/run_local_web.ps1`은 해당 옵션을 켜고 아이디 접속을 활성화한 뒤 8001 포트로 실행합니다.
필요 의존성은 `pip install -e '.[dev,preview]'` 또는 갱신된 requirements-dev.lock으로 설치합니다.

- `/`는 기존 로그인·최초 설정을 사용합니다. 완료하면 `/app`으로 이동합니다.
- `/api/preview-status`로 연결 모드 사용 여부를 확인합니다. 비활성화 시 기존 A 화면 흐름을 유지합니다.
- `/api/frontend-config.js`는 로그인한 사용자 ID·닉네임·색상과 예제 친구 모드만 전달합니다.
- `/api/me`, `/api/progress`, `/api/keywords`는 기존 HttpOnly 로그인 쿠키를 검증합니다.
- 게시 처리는 시제품 모듈을 별도 패키지명으로 불러와 재사용합니다. backend의 app 패키지를 가리지 않습니다.
- 스택 DB 경로는 서버가 인증된 UUID로 결정합니다. ContextVar로 요청/작업 스레드마다 격리합니다.
- 기존 web-preview 사용자별 SQLite 기록은 최초 연결 시 기준 스택으로 유지합니다. 최신 스택은 characters.stats에 저장합니다.
- 친구 초대의 예제 데이터도 사용자 ID를 붙인 localStorage 키로 분리합니다.
- 개발 응답은 no-store로 제공하고 초기 진입 모듈 버전을 붙여 병합 전 스크립트 캐시 영향을 줄입니다.
- 로그인 입력창은 기본 HTML에 표시하고 초기화 실패 시 다시 불러오기 버튼을 표시합니다.
- 로그인·설정 API는 12초 응답 제한을 두어 진행 안내만 무한히 남는 상황을 방지합니다.

실제 운영 연결에서는 B의 기록·네 분류 스택과 A의 효과 저장 규약을 합치고,
친구/초대/멤버십을 서버 API로 교체해야 합니다. 개발용 브리지는 운영에 노출하지 않습니다.

## INUstagram 피드

`b0001` 마이그레이션은 `0004` 다음에 게시물·친구 요청 테이블을 추가합니다. 계정과 캐릭터 테이블은 보존합니다.
서버 시작 전에 `alembic upgrade head`를 실행하세요. `scripts/run_local_web.ps1`에도 포함되어 있습니다.
다른 브랜치의 `0005` 통합 활동 마이그레이션과 병합하면 둘 다 보존하고 merge revision을 추가합니다.
공유된 revision 번호나 down_revision을 사후에 바꾸지 않습니다.

- 원본 사진은 DB BLOB으로 저장하며, 피드 조회는 사진 BLOB을 지연 로딩해 목록 전체를 메모리에 읽지 않습니다.
- 이미지를 직접 받는 API에도 세션 및 친구 관계 검사를 적용합니다.
- 게시 원문/원본을 분석 호출 전에 저장합니다. 재시도는 기존 게시 시각과 게시 ID를 유지합니다.
- 중복 요청은 사용자+request_id UNIQUE와 분석 처리권 조건부 UPDATE로 방지합니다.
- 두 게시 경로는 activity_records와 characters.stats를 공유합니다. 상태 반영과 피드 완료 갱신은 같은 트랜잭션입니다.
- 이전 분석 전용 시제품에는 원본 사진이 없었으므로 과거 사진을 자동 복원하지 않습니다.
- 실제 친구 등록은 피드 화면의 버튼을 사용합니다. 예제 라운지의 민지·준호와는 별개입니다.
- 두 계정은 일반/시크릿 브라우저에서 각각 로그인하거나 로그아웃 후 계정을 바꾸어 테스트합니다.

테스트는 게시물 페이지네이션, 실패 후 원본 유지, 동시 중복 처리, 실제 친구 수락 전후 피드/이미지 권한을 검증합니다.

## 최신 A·B·C 통합

`0005`의 활동 저장과 `b0001`의 피드/친구 저장은 `b0002` merge migration으로 연결합니다.
기존 DB에서 `alembic upgrade head`를 실행하면 양쪽 테이블을 보존하면서 단일 head로 갱신됩니다.
A의 `/api/records`는 비동기 분석·재시도, B의 `/api/keywords`는 기존 게시 UI 응답 형식을 유지합니다.
양쪽 모두 인증 계정의 activity_records에 분석을 저장하고 B의 계산 함수로 characters.stats에 반영합니다.
술→운동 감소는 그룹 합산으로 계산할 수 없으므로 현재 스택에 순차 반영하고 기록별 중복을 막습니다.
기존 사용자별 시제품 기록은 기준값으로 보존하며 다른 계정·이전 공용 DB를 가져오지 않습니다.
공통 원본 모듈은 `campus_records_prototype` 패키지 이름으로 불러오며 backend app과 충돌하지 않습니다.
main의 C 도트 캐릭터는 메인에 연결하고 독립 미리보기와 Phaser 초안도 보존합니다.
`GET /characters/me`의 stats와 `/api/progress`의 progress가 같은 최신 스택입니다.
