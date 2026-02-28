## 🚀 해커톤 기획서: 9-Cut Teaser Studio (가칭)

### 1. 서비스 개요

* **목표:** 웹소설/대본 1화 분량의 텍스트를 분석하여, 스포일러 없는 9컷의 인스타그램/릴스용 티저 이미지를 자동 생성합니다.
* **핵심 기술:** * **Gemini 3.1 Pro:** 텍스트 이해, 반전 요소 필터링, 9컷 씬 분할, 카피라이팅 및 프롬프트 설계.
* **Nano Banana:** 캐릭터 일관성 유지, 선택된 화풍 적용, 이미지 내 완벽한 카피라이팅 텍스트 렌더링.



### 2. 사용자 플로우 (UI/UX)

1. **텍스트 입력:** 사용자가 웹소설 1화 텍스트를 붙여넣습니다.
2. **레퍼런스 선택:** 작품에 맞는 '캐릭터 및 화풍 레퍼런스 템플릿'을 선택합니다. (아래 템플릿 목록 참조)
3. **자동 생성 대기:** Gemini가 씬을 쪼개고 나노 바나나가 이미지를 굽는 로딩 화면.
4. **결과 확인 및 다운로드:** 텍스트가 박힌 9컷의 고퀄리티 티저 이미지가 인스타 피드 형태로 출력됩니다.

---

### 2. 미술 장르 (Art Style) 템플릿

나노 바나나(Nano Banana)의 프롬프트 뒷부분에 고정으로 삽입되어, 9컷 내내 동일한 질감과 톤을 유지하게 만드는 '스타일 프롬프트'입니다.

* **Option A: 깔끔한 만화/웹툰형 (Webtoon / Cel Animation)**
* **시각적 특징:** 뚜렷한 외곽선, 단색 위주의 깔끔한 채색, 높은 명도 대비.
* **나노 바나나 프롬프트 키워드:** `2D cel shading, crisp line art, korean webtoon style, flat colors, clear lighting, high contrast.`


* **Option B: 깊이 있는 반실사형 (Semi-Realistic / Cinematic)**
* **시각적 특징:** 실사에 가까운 피부 질감과 빛 표현, 영화 같은 구도와 심도(아웃포커싱).
* **나노 바나나 프롬프트 키워드:** `Semi-realistic, intricate details, cinematic lighting, dramatic shadows, 8k resolution, photorealistic textures, depth of field.`


* **Option C: 감성적인 수채화형 (Watercolor / Traditional Media)**
* **시각적 특징:** 물감이 번진 듯한 부드러운 경계, 파스텔톤의 따뜻하고 몽환적인 분위기.
* **나노 바나나 프롬프트 키워드:** `Watercolor painting, soft pastel colors, traditional media, fluid brush strokes, dreamy and ethereal atmosphere, paper texture.`


* **Option D: 밀도 높은 일러스트형 (Digital Illustration)**
* **시각적 특징:** 붓 터치가 살아있는 두터운 채색, 화려하고 풍부한 색감, 게임 원화 같은 완성도.
* **나노 바나나 프롬프트 키워드:** `High-quality digital painting, conceptual art, thick impasto strokes, rich and vibrant colors, masterpiece, highly detailed.`


