# 피치노트 축구 카드뉴스

피치노트(@pitchnote_) 인스타그램에 올릴 축구 소식 게시물(이미지 한 장 + 상세 내용 텍스트)을 만드는 저장소입니다.

- `skills/pitchnote-card-news/` — Claude 스킬. 기사 수집, 사진 검색, 이미지 생성 스크립트와 작업 순서
- `skills/pitchnote-card-news.skill` — Claude 앱에 추가하는 스킬 설치 파일
- `docs/` — 스펙 문서 (`card-news-spec.md`, 읽기용 `피치노트-카드뉴스-스펙.html`)
- `posts/YYYY-MM-DD/` — 만든 게시물

Claude에게 "오늘 축구 카드뉴스 만들어줘"라고 요청하면 `posts/` 아래에 게시물이 만들어집니다. 규격과 기준은 스펙 문서에 있습니다.
