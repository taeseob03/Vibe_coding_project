"""Call the running local API without a browser."""

import argparse
import json
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser(description="로컬 키워드 추출 테스트")
    parser.add_argument("--text", default="", help="분석할 글")
    parser.add_argument("--image", type=Path, help="분석할 이미지 파일 경로")
    args = parser.parse_args()
    if not args.text.strip() and not args.image:
        args.text = "오늘 도서관에서 친구와 시험 공부를 하고 동아리 회의에 참석했다."
    try:
        with httpx.Client(timeout=90) as client:
            if args.image:
                with args.image.open("rb") as image:
                    response = client.post(
                        "http://127.0.0.1:8000/api/keywords",
                        data={"text": args.text},
                        files={"image": (args.image.name, image)},
                    )
            else:
                response = client.post(
                    "http://127.0.0.1:8000/api/keywords", data={"text": args.text}
                )
        print(f"HTTP {response.status_code}")
        print(json.dumps(response.json(), ensure_ascii=False, indent=2))
        return 0 if response.is_success else 1
    except (httpx.HTTPError, OSError) as error:
        print(f"테스트 실패: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
