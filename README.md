# card_news

주제별 인스타그램 계정에 올릴 카드뉴스 게시물(이미지 + 상세 내용 텍스트)을 만드는 저장소입니다. 주제마다 Claude 스킬이 하나씩 있습니다.

| 주제 | 스킬 | 계정 |
|---|---|---|
| 축구 | `skills/football-card-news/` | @pitchnote_ |

- `skills/` — 주제별 스킬 폴더와 Claude 앱 설치 파일(`.skill`)
- `docs/` — 스펙 문서. 공통 규칙은 `00-overview.md`, 주제별 규칙은 `01-<주제>.md`, 읽기용 `카드뉴스-스펙.html`
- `posts/<주제>/YYYY-MM-DD/` — 만든 게시물 (git에 올리지 않음)

Claude에게 "오늘 축구 카드뉴스 만들어줘"처럼 요청하면 해당 주제의 `posts/` 아래에 게시물이 만들어집니다. 새 주제를 추가하는 방법은 `docs/00-overview.md`에 있습니다.
