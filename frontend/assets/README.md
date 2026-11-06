# 공통 이미지와 캐릭터 자산

빌드 도구 없이 브라우저 ES module을 사용합니다. 통합 게임은 로컬 `frontend/vendor/phaser-3.90.0.min.js`를 사용합니다.
라이브러리·폰트의 라이선스와 출처는 `frontend/vendor/README.md`에 있습니다.

## character/pixel-character.js

개발 계획 7.2·7.4 기준의 임시 픽셀 캐릭터 렌더러입니다. 코드로 픽셀을 찍어 그립니다.

- `composeCharacter(appearance, major)`: 뒷머리 → 몸·과잠 → 얼굴 → 앞머리 레이어 합성
- `createStage(canvas, getState)`: 캐릭터·이름표·카테고리 소품(술병·책·덤벨·하트) 무대
- `tierOf / countOf / scaleOf`: 레벨 → 소품 단계·개수·크기

미리보기: 서버 실행 후 http://127.0.0.1:8000/static/preview/character.html
통합 화면의 `game/avatar.mjs`가 `composeCharacter`로 본체·학과 과잠을 그립니다.
소품·표정은 B가 반환하는 stats/state를 표시합니다. 이 파일의 tierOf 등은 별도 미리보기용 초안입니다.
최종 원본 이미지가 준비되면 `composeCharacter`와 `SPRITES`를 이미지 로딩으로 교체합니다.
