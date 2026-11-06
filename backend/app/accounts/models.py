from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    # A: 이메일/비밀번호 해시/설정 완료 여부는 마이그레이션과 함께 추가합니다.
