from pathlib import Path
from shutil import copyfile

root = Path(__file__).resolve().parents[1]
if not (root / ".env").exists():
    copyfile(root / ".env.example", root / ".env")
(root / "backend/data").mkdir(parents=True, exist_ok=True)
print("개발 설정 준비 완료. 프로젝트 루트에서 마이그레이션을 실행하세요.")
