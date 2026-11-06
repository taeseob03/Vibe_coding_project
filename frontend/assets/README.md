# 공통 이미지와 캐릭터 자산

현재는 빌드 도구 없이 브라우저 ES module을 사용합니다. Phaser는 아직 설치하지 않았습니다.
도입 시 버전을 고정하고 배포 가능한 라이브러리 파일 또는 프런트 빌드 구조를 함께 PR에 추가하세요.

## character/pixel-character.js (B)

개발 계획 7.2·7.4 기준의 임시 픽셀 캐릭터 렌더러입니다. 코드로 픽셀을 찍어 그립니다.

- `composeCharacter(appearance, major)`: 뒷머리 → 몸·과잠 → 얼굴 → 앞머리 레이어 합성
- `createStage(canvas, getState)`: 캐릭터·이름표·카테고리 소품(술병·책·덤벨·하트) 무대
- `tierOf / countOf / scaleOf`: 레벨 → 소품 단계·개수·크기

미리보기: 서버 실행 후 http://127.0.0.1:8000/preview/character.html
A가 메인 화면에 캐릭터를 붙일 때 `createStage`를 가져다 쓰면 됩니다.
최종 원본 이미지가 준비되면 `composeCharacter`와 `SPRITES`를 이미지 로딩으로 교체합니다.
