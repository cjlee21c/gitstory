# GitStories 배포 가이드 (Stage 1)

수업용 배포. 백엔드는 Render(항상 켜짐), 프론트엔드는 Cloudflare Pages 또는 Vercel(무료).
접근 제한은 없다 — 링크를 아는 사람은 누구나 쓸 수 있으므로, 예산 방어선은 Anthropic
선불 크레딧(자동 충전 OFF) 하나뿐이다.

---

## 0. 배포 전에 (한 번만)

- [ ] **Anthropic 콘솔 → 월 spend limit + 알림 설정.** 이것이 실제 예산 방어선이다.
- [ ] **GitHub 토큰 만료일 확인** (classic PAT 기본 만료 시 앱 전체 정지). 최소 배포 기간 + 여유.

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

- [ ] 프론트 URL 접속 → 접근 코드 입력 화면이 뜨는지.
- [ ] 틀린 코드 → 막히고, 맞는 코드 → 통과.
- [ ] discover → 스토리 1개 열기까지 정상 동작.
- [ ] `/workspace`에서 새로고침해도 404 안 뜨는지 (SPA rewrite).

---

## 운영 노트

- **중간 수정 반영**: main에 push하면 Render/Pages가 자동 재배포 (Auto-Deploy 켜둘 것).
- **캐시 주의**: `.cache`가 디스크에 보존되므로 워크스페이스 프롬프트를 바꾸면 기존 캐시가
  그대로 서빙됨 → 새로 생성하려면 해당 요청을 `force=true`로 부르거나 디스크 캐시 삭제.
- **로컬 실행**: `backend/.env`에 `GITHUB_TOKEN`, `ANTHROPIC_API_KEY`가 있어야 서버가 뜬다.
