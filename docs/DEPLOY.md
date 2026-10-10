# GitStories 배포 가이드 (Stage 1)

수업용 배포. 백엔드는 Render(항상 켜짐), 프론트엔드는 Cloudflare Pages 또는 Vercel(무료).
접근 제한은 없다 — 링크를 아는 사람은 누구나 쓸 수 있으므로, 예산 방어선은 Anthropic
선불 크레딧(자동 충전 OFF) 하나뿐이다.

토론에 등장하는 실제 개발자는 스토리마다 가명으로 치환된다(`Maintainer A`,
`Contributor B`). 공개 데이터이긴 하지만 그 사람들이 교재에 실리는 데 동의한 적은
없으므로, 앱 화면과 논문 어디에도 식별 정보가 남지 않는 것이 요구사항이다.
구현은 `backend/app/privacy.py`, 검증은 `backend/scripts/check_privacy.py`.

---

## 0. 배포 전에 (한 번만)

- [ ] **Anthropic 콘솔 → 월 spend limit + 알림 설정.** 이것이 실제 예산 방어선이다.
- [ ] **GitHub 토큰 만료일 확인** (classic PAT 기본 만료 시 앱 전체 정지). 최소 배포 기간 + 여유.
- [ ] **교사용 토큰 생성** → Render `TEACHER_TOKEN`에 넣기. 학생 답변 열람에 필요하다:
      `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`
      값이 비면 `GET /stories/{id}/answers`는 403으로 **닫힌다** (fail-closed). 열리는
      쪽이 기본값이 아니므로, 깜빡해도 반 전체 답변이 공개되는 일은 없다.
- [ ] **비식별화 검증** (seed 캐시를 손봤다면 필수):
      `cd backend && ./venv/bin/python scripts/check_privacy.py --dir seed_cache`

---

## 1. 백엔드 — Render Web Service

1. Render 대시보드 → **New → Web Service** → 이 GitHub repo 연결.
2. 설정:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Starter ($7/월, 항상 켜짐 — cold start 없음)
   - **Health Check Path**: `/health`
3. **Environment** 탭에서 아래 변수 추가:
   | Key | Value |
   |---|---|
   | `GITHUB_TOKEN` | GitHub PAT |
   | `ANTHROPIC_API_KEY` | Anthropic 키 |
   | `TEACHER_TOKEN` | 답변 열람용 (아래 0단계에서 생성) |
   | `CORS_ORIGINS` | (2단계 후 채움 — 프론트 URL) |
   | `DB_PATH` | `/data/gitstory.db` |
   | `CACHE_DIR` | `/data/.cache` |
4. **Disks** → Add Disk: Name 아무거나, **Mount Path `/data`**, Size 1GB.
   (마이닝 캐시가 재배포에도 보존돼 재배포 후 첫 사용자가 안 느려짐.)
5. Deploy. 배포되면 URL 확보 (예: `https://gitstories-api.onrender.com`).

---

## 2. 프론트엔드 — Cloudflare Pages 또는 Vercel

- **Root Directory**: `frontend`
- **Build Command**: `npm install && npm run build`
- **Output Directory**: `dist`
- **환경변수** `VITE_API_BASE_URL` = 1단계에서 얻은 백엔드 URL
- SPA 라우팅 rewrite는 이미 repo에 포함됨 (`frontend/public/_redirects`, `frontend/vercel.json`)
  — 별도 설정 불필요.

배포되면 프론트 URL 확보 (예: `https://gitstories.pages.dev`).

---

## 3. 마무리 (CORS 연결)

- [ ] Render 백엔드의 `CORS_ORIGINS`에 프론트 URL 입력 (여러 개면 콤마로) → **재배포**.
      예: `CORS_ORIGINS=https://gitstories.pages.dev`

---

## 4. 확인

- [ ] discover → 스토리 1개 열기까지 정상 동작.
- [ ] 스토리 화면의 발언자가 `Maintainer A` 같은 가명인지 (실명/GitHub 아이디면 중단).
- [ ] `curl $API/stories/<owner>/<repo>%23<n>` → **404** (원본 번들은 공개되지 않는다).
- [ ] `curl $API/stories/<owner>/<repo>%23<n>/answers` → **403**, 토큰 헤더를 붙이면 200:
      `curl -H "X-Teacher-Token: $TEACHER_TOKEN" ...`
- [ ] `/workspace`에서 새로고침해도 404 안 뜨는지 (SPA rewrite).

---

## 운영 노트

- **중간 수정 반영**: main에 push하면 Render/Pages가 자동 재배포 (Auto-Deploy 켜둘 것).
- **캐시 주의**: `.cache`가 디스크에 보존되므로 워크스페이스 프롬프트를 바꾸면 기존 캐시가
  그대로 서빙됨 → 새로 생성하려면 해당 요청을 `force=true`로 부르거나 디스크 캐시 삭제.
- **로컬 실행**: `backend/.env`에 `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`가 있어야 서버가 뜬다.
  `TEACHER_TOKEN`은 없어도 뜨지만 답변 열람만 막힌다.
- **학생 답변 내려받기**: `curl -H "X-Teacher-Token: $TEACHER_TOKEN" $API/stories/<id>/answers`
- **프롬프트나 파이프라인을 건드린 뒤**: `scripts/check_privacy.py`를 돌릴 것. 실명이 다시
  새는 경로(새 beat 필드, 프롬프트의 실명 지시)는 아무것도 깨뜨리지 않고 조용히 통과한다.
- **배포 디스크 캐시 정리**: 비식별화 이전에 생성된 워크스페이스가 `/data/.cache`에 남아
  있으면 실명이 그대로 서빙된다. 한 번만:
  `./venv/bin/python scripts/pseudonymize_cached_workspaces.py --dir /data/.cache`
