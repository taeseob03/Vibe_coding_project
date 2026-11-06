# A·B Git 협업 절차

## 저장소 준비

원격: `https://github.com/taeseob03/Vibe_coding_project.git`

저장소 관리자는 GitHub Settings → Collaborators에서 A와 B를 초대하고 각자 초대를 수락합니다.
각자는 자기 GitHub 계정으로 인증합니다. HTTPS 사용 시 GitHub CLI/자격 증명 관리자/PAT를 사용하며,
토큰을 저장소 주소·소스 파일에 쓰지 않습니다. SSH는 각자의 SSH 키를 등록한 뒤 사용합니다.
이 개발 환경 구성은 GitHub 초대·인증·보호 규칙을 자동으로 변경하지 않습니다.

초기 환경 파일을 GitHub main에 반영한 뒤 각자 clone합니다. 이 작업 공간에서 초기 구성을 게시할 때:

```bash
git status
# 의도한 환경 파일인지 검토 후 커밋
git add .
git commit -m "chore: set up campus app development environment"
git push -u origin main
```

이미 커밋되어 있다면 `git push -u origin main`만 실행합니다. 원격에 새 커밋이 있으면 먼저 fetch/merge하고 검증합니다.
main 직접 push가 보호된 저장소라면 작업 브랜치로 push한 뒤 PR을 만듭니다.

## A와 B의 첫 작업

A:

```bash
git clone https://github.com/taeseob03/Vibe_coding_project.git
cd Vibe_coding_project
make setup
make migrate
git switch -c feature/account-character
```

B는 같은 과정을 실행하되 마지막 명령을 다음으로 바꿉니다.

```bash
git switch -c feature/records-analysis
```

각자 별도 clone 폴더와 DB를 사용합니다. 같은 폴더에서 두 사람이 브랜치를 전환하지 않습니다.
`git config user.name`과 `git config user.email`은 각자의 값으로 설정합니다.

## 매 작업 시작과 종료

작업 시작 시 현재 브랜치를 확인하고 원격의 같은 브랜치를 가져옵니다.
`git pull`은 main이 아니라 **현재 브랜치의 upstream**을 가져옵니다.

```bash
git status
git branch --show-current
# 최초 push 이후 사용
git pull --ff-only
# 통합된 main 변경을 현재 기능 브랜치에 반영
git fetch origin
git merge origin/main
make migrate
make check
```

작업 후에는 본인 담당 변경과 필요한 연결 변경을 검토하여 커밋합니다.

```bash
git diff
# 예: B 담당. A는 본인 담당 경로를 지정
git add backend/app/records backend/app/analysis frontend/records backend/tests
# 모델 변경 시 검토한 migrations/versions의 새 파일도 추가
git commit -m "feat: implement record analysis retry"
git push -u origin feature/records-analysis
```

이후 같은 브랜치는 `git push`로 올립니다. GitHub에서 base=`main`인 PR을 만들고 상대 담당자가 검토합니다.
PR에는 변경 동작, 규약 영향, 마이그레이션, 검증 결과를 기록합니다.
통합 후에는 각 기능 브랜치에서 다시 `git fetch origin`, `git merge origin/main`을 실행합니다.

## 공통 파일과 충돌

`core/`, `main.py`, `frontend/index.html`, `frontend/shared/`, 의존성 파일, 마이그레이션,
API 규약은 변경 전에 상대에게 범위를 공유합니다. 다른 담당 모듈의 내부 DB 저장을 우회 호출하지 않습니다.

충돌 시 `git status`로 파일을 확인하고 충돌 표시를 편집하여 두 기능을 보존합니다.
해결한 파일만 `git add`한 뒤 `git merge --continue`하고 `make migrate`, `make check`를 실행합니다.
판단이 어려우면 `git merge --abort`로 merge를 취소하고 담당자와 해결합니다.
공유 브랜치에 force push하거나 상대 변경을 통째로 덮어쓰지 않습니다.

## 통합 기준과 GitHub 설정

- 1차: 두 계정의 실제 인증·소유자별 기록 조회·재시도 권한 검증
- 2차: 실제 AI 분석·효과 반영·중복 지급 방지·실패 복구 검증
- 관리자 권장 설정: main PR 필수, 상대 1명 승인, CI의 `backend` 체크 통과 필수
- 관리자 권장 설정: main 강제 push·삭제 차단

로컬에서 CI 파일을 추가하는 것만으로 GitHub의 브랜치 보호가 활성화되지는 않습니다.
