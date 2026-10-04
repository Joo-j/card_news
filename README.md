# 해외축구 카드뉴스 봇

해외축구 RSS를 모아 Claude가 기사 하나를 고르고 한국어 카드뉴스(표지 + 본문 3~5장)를 만든 뒤 인스타그램 캐러셀로 게시합니다.
GitHub Actions에서 하루 3번(KST 08:00, 13:00, 20:00) 실행되고, 한 번에 1건을 올립니다.

## 흐름

1. `python -m bot prepare`
   - RSS 수집: BBC Sport, The Guardian, Sky Sports, ESPN (최근 24시간)
   - 이미 올린 기사는 빼고, Claude가 화제성 기준으로 1건 선택 (이미 다룬 주제와 겹치면 제외)
   - 기사 본문을 가져와 Claude가 카드 문구, 캡션, 해시태그 작성
   - `posts/<날짜-시각>/01.jpg …` 로 1080×1350 이미지 렌더링, `posts/pending.json` 기록
2. 워크플로가 이미지를 저장소에 커밋·푸시
3. `python -m bot publish`
   - `raw.githubusercontent.com/<저장소>/<커밋>/posts/...` 주소로 인스타그램 Graph API에 캐러셀 게시
   - 성공하면 `data/state.json` 에 기록하고 `pending.json` 삭제
   - 실패하면 다음 실행 때 같은 카드로 다시 시도, 3번 실패하면 그 기사는 건너뜀

## 설정

### 1. GitHub 저장소

- 이 폴더를 **public** 저장소로 올립니다. 인스타그램이 raw URL로 이미지를 가져가야 해서 private이면 게시가 안 됩니다.
- Settings → Actions → General → Workflow permissions 를 **Read and write** 로 둡니다.

### 2. 인스타그램 토큰

인스타그램 계정이 **비즈니스 또는 크리에이터 계정**이어야 합니다.

1. [Meta for Developers](https://developers.facebook.com/)에서 앱 생성 → 제품에 **Instagram** 추가 → "API setup with Instagram login"
2. 게시할 인스타그램 계정을 연결하고 권한 `instagram_business_basic`, `instagram_business_content_publish` 부여
3. 액세스 토큰 생성 → 장기 토큰(60일)으로 교환
4. 계정의 user id 확인: `https://graph.instagram.com/v23.0/me?fields=user_id,username&access_token=<토큰>`

페이스북 페이지에 연결된 방식(Facebook Login)으로 토큰을 받았다면 저장소 Variables에 `IG_GRAPH_HOST=graph.facebook.com` 을 넣습니다.

### 3. Secrets / Variables

Settings → Secrets and variables → Actions

| 종류 | 이름 | 값 |
|---|---|---|
| Secret | `ANTHROPIC_API_KEY` | Claude API 키 |
| Secret | `IG_USER_ID` | 인스타그램 user id |
| Secret | `IG_ACCESS_TOKEN` | 인스타그램 장기 토큰 |
| Variable (선택) | `BRAND_NAME` | 카드 상단에 들어갈 이름 (기본값 `해외축구 브리핑`) |
| Variable (선택) | `IG_GRAPH_HOST` | 위 설명 참고 (기본값 `graph.instagram.com`) |

설정 후 Actions 탭 → card-news → **Run workflow** 로 한 번 실행해 확인합니다.

## 로컬에서 카드만 만들어 보기

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
ANTHROPIC_API_KEY=... .venv/bin/python -m bot prepare
```

`posts/` 에 이미지가 생깁니다. 로컬에서 게시까지 하려면 이미지가 공개 URL에 있어야 하므로 `RAW_BASE_URL` 을 지정해야 합니다.
로컬에서 만든 `posts/pending.json` 은 지우지 않으면 다음 실행 때 그대로 게시되니, 확인만 했다면 지웁니다.

## 바꿀 만한 곳

- RSS 목록, 수집 기간: `bot/config.py`
- 기사 선택 기준, 카드 문구 규칙: `bot/writer.py`
- 카드 디자인(색, 글꼴 크기, 배치): `bot/render.py`
- 실행 시각: `.github/workflows/card-news.yml` 의 `cron` (UTC 기준)

## 주의

- 장기 토큰은 60일 뒤 만료됩니다. 만료 전에 `https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<토큰>` 으로 갱신해 Secret을 바꿔 넣어야 합니다.
- 기사 사진은 저작권 문제로 쓰지 않고 글자 카드만 만듭니다. 캡션에 출처와 원문 링크를 붙입니다.
- 글꼴: [Pretendard](https://github.com/orioncactus/pretendard) (SIL OFL, `fonts/LICENSE.txt`)
