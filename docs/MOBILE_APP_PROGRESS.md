# IAmSurfer Mobile — Estado da Implementação (handoff)

> **Para a próxima sessão.** Leia este arquivo primeiro. Ele resume o que estamos
> construindo, o que já está pronto e funcionando, as decisões/armadilhas do
> ambiente, e o próximo passo concreto.
>
> Última atualização: **2026-06-29**.

---

## 1. O que estamos construindo

App mobile **nativo iOS + Android** do IAmSurfer (rede social de surf), com
**paridade com a web**. Plano-mestre detalhado (prompts A0–A13 backend, B0–B13
app): [`MOBILE_APP_IMPLEMENTATION.md`](./MOBILE_APP_IMPLEMENTATION.md).

**Arquitetura:** o backend Flask existente (site Jinja) ganha uma **API REST
`/api/v1`** (blueprint novo, JWT) que **reaproveita os mesmos models/DB/
Cloudinary** sem alterar o site. O app **Expo/React Native** (repo separado
`iamsurfer-app/`) consome essa API.

```
iamsurfer/        ← backend Flask (site Jinja + API REST /api/v1)  [git repo]
iamsurfer-app/    ← app Expo/React Native (TypeScript)             [git repo]
```

---

## 2. O que JÁ está pronto e verificado ✅

### Backend — Prompt A0 (fundação da API) + A1 (auth)
Pasta nova: **`iamsurfer/routes/api/`**
- `__init__.py` — blueprint `/api/v1`, init de JWT/CORS/rate-limit, `register_api(app)`, `GET /api/v1/ping`.
- `errors.py` — formato de erro único `{"error":{"code","message","fields"}}` + handlers (401/403/404/422/429/500) e classe `ApiError`.
- `pagination.py` — paginação **cursor-based** (`?cursor=&limit=`) → `{items, next_cursor}`.
- `serializers.py` — `user_full(viewer)`, `me_full`, `user_brief` (contrato da seção 2 do plano: `patente`, `counts`, `viewer_state`, URLs de mídia absolutas).
- `deps.py` — `current_api_user()`, `issue_tokens()`, `revoke_token()`, `body()`, `require_fields()`.
- `auth.py` — `POST /auth/register`, `/auth/login` (email **ou** username, case-insensitive), `/auth/refresh` (rotativo), `/auth/logout`, `GET /auth/me`, `POST /auth/push-token`.

Outras mudanças no backend:
- `models.py` — **+`TokenBlocklist`** (refresh revogados) e **+`DeviceToken`** (Expo push token por device).
- `migrations/versions/e3f4a5b6c7d8_*.py` — migration das 2 tabelas (down_revision = `d2b3c4e5f6a7`, que é o head).
- `app.py` — chama `register_api(app)` após registrar os blueprints do site.
- `requirements.txt` — `Flask-JWT-Extended==4.5.3`, `Flask-Cors==3.0.10`, `Flask-Limiter==2.8.1`.
- `.env.example` — `JWT_SECRET_KEY`, `API_CORS_ORIGINS`.
- `tests/conftest.py` + `tests/test_api_auth.py` — **8 testes passando** (ping, 401 padrão, fluxo register→login→refresh→me→logout, rotação/revogação, validação, push-token upsert).

**Como rodar os testes do backend:**
```bash
cd iamsurfer
python -m pytest tests/test_api_auth.py -q
```
Smoke: `python app.py` sobe site + API juntos (109 rotas; `/api/v1/ping` responde `{"ok":true,"version":"1"}`).

### App — Prompt B0 (scaffold + design system) + B1 (cliente/auth) + B2 (telas auth)
Pasta nova: **`iamsurfer-app/`** (Expo SDK 56, expo-router, React 19, RN 0.85).
- `src/theme/index.ts` — design system da marca (indigo `#3730a3`, spacing, tipografia).
- `src/components/` — `Button`, `Input`, `Avatar`, `Placeholder`.
- `src/api/client.ts` — fetch + `Authorization: Bearer` + **interceptor de refresh** (401 → refresh single-flight → retry → senão `onSessionExpired`); mapeia erro padrão p/ `ApiError`. `types.ts`, `auth.ts`.
- `src/lib/storage.ts` — tokens no **SecureStore**. `queryClient.ts` (React Query). `push.ts` (Expo push token).
- `src/context/AuthContext.tsx` — `signIn/register/signOut/refreshMe`, restaura sessão no boot, liga o `onSessionExpired`.
- `app/_layout.tsx` — provedores globais + **gate de autenticação** (logado→tabs, deslogado→login).
- `app/(auth)/login.tsx`, `signup.tsx` — telas com validação e erros da API.
- `app/(tabs)/_layout.tsx` + telas — bottom tabs **Início · Explorar · Criar · Reels · Perfil** (espelha o navbar web). `index` (feed placeholder + status da API), `profile` (perfil real do usuário logado + logout), demais placeholders.

**Verificado:** `npx tsc --noEmit` limpo **e** `npx expo export --platform android` gera o bundle Hermes com sucesso (rotas, imports e auth compilam para alvo nativo).

**Como rodar o app:**
```bash
cd iamsurfer-app
# copie .env.example -> .env e ajuste EXPO_PUBLIC_API_URL
npm install
npm start            # Expo Go / emulador
npm run typecheck    # tsc --noEmit
```
Detalhes no [`iamsurfer-app/README.md`](../../iamsurfer-app/README.md).

---

## 3. Armadilhas do ambiente (IMPORTANTE) ⚠️

- **NÃO subir o Flask para 3.x.** O site usa `from flask import Markup` e
  `from werkzeug.urls import url_parse`, removidos no Flask 2.3+/3. Manter
  **Flask 2.0.1 / Werkzeug 2.0.1**. (O `pip install` das libs novas chega a
  puxar Flask 3 — se acontecer, reinstale: `pip install "Flask==2.0.1"
  "Werkzeug==2.0.1" "itsdangerous==2.0.1"`.)
- O ambiente Python desta máquina não tinha as deps do projeto instaladas; foram
  instaladas Flask-SQLAlchemy 2.5.1, Flask-Login 0.5.0, Flask-Migrate 3.1.0,
  SQLAlchemy 1.4.46, etc. (compatíveis com Flask 2.0.1).
- **Disco:** C: vive quase cheio. Caches/temp já redirecionados para D: e
  **Docker movido para `D:\DockerData`** (junction). Ver memória `disk-constraint`.
  Builds pesados (EAS) → manter saída em D:.
- App em **Expo SDK 56 / React 19 / RN 0.85** (bleeding edge). `babel-preset-expo`
  já injeta o plugin do Reanimated/Worklets — **não** adicionar manualmente no
  `babel.config.js`. Instalações usaram `--legacy-peer-deps` quando deu ERESOLVE.

---

## 4. Próximo passo (caminho recomendado)

O caminho crítico (`A0→A1→B0→B1→B2`, login real) **está fechado**. Agora cada par
`An/Bn` de feature é independente. Sugestão de ordem (do plano, seção 6):

1. **A11 (upload Cloudinary assinado)** — desbloqueia mídia de posts/stories/reels.
2. **A2 + B6 (perfil/follow)** — bom primeiro par "vertical" ponta a ponta.
3. **A3 + B3 (feed/posts)** — núcleo do app.
4. Depois: A4/B4 (stories), A5/B5 (reels), A7/B8 (mapa/previsão), A6+A12/B7 (msgs+push), A8/B9 (caronas), A9/B10 (fotos+pagamento), A10/B11 (ranking).
5. Fechamento: A13 (OpenAPI/contrato), B12 (deep links), B13 (EAS build + lojas).

**Padrões obrigatórios** (Definition of Done, seção 4 do plano): formato de erro,
paginação e serializers da fundação; `@jwt_required()` + respeitar
`is_public`/privacidade; não quebrar o pytest do site; reusar lógica existente
(gamificação, badges, forecast Open-Meteo, Cloudinary); nada de segredo hardcoded.

### Sugestão para começar amanhã
> "Implemente o Prompt A11 (upload assinado pro Cloudinary) e, em seguida, o par
> A2/B6 (perfil + follow), seguindo os contratos já estabelecidos em
> `routes/api/` e o cliente do app. Rode os testes do backend e o typecheck do
> app ao final."
