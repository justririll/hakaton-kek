# Culture Insights frontend

Vue 3 frontend for the culture analytics FastAPI service. It uses TypeScript,
Vite, Vue Router, Pinia, Vitest, ESLint, and Prettier.

## Recommended IDE Setup

[VS Code](https://code.visualstudio.com/) + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar) (and disable Vetur).

## Project Setup

```sh
npm install
```

Start FastAPI from the repository root:

```sh
uv run fastapi dev
```

Then start the frontend in another terminal:

```sh
npm run dev
```

Vite serves the app at `http://localhost:5173` and proxies `/api` requests to
FastAPI at `http://127.0.0.1:8000`.

### Type-Check, Compile and Minify for Production

```sh
npm run build
```

### Run Unit Tests with [Vitest](https://vitest.dev/)

```sh
npm run test:unit
```

### Lint with [ESLint](https://eslint.org/)

```sh
npm run lint
```

### Format source files

```sh
npm run format
```
