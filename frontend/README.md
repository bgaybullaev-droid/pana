# ucharmarket-frontend

Frontend for PANA — a real estate marketplace web application.

Built with React, TypeScript and Vite, using Mantine for the UI and Effector
for state management.

## Tech stack

- **Framework:** React 18 + TypeScript
- **Build tool:** Vite 5
- **UI:** Mantine 7 (`@mantine/core`, `form`, `hooks`, `notifications`)
- **State management:** Effector
- **Routing:** React Router DOM 6
- **HTTP client:** Axios
- **i18n:** i18next / react-i18next
- **Maps:** Leaflet / react-leaflet
- **Testing:** Vitest + Testing Library (unit), Playwright (e2e)

## Requirements

- Node.js 18+ and npm

## Getting started

```bash
# install dependencies
npm install

# start the dev server
npm run dev
```

The dev server runs on http://localhost:7878 and proxies `/api` and `/uploads`
requests to the backend at http://localhost:7879.

## Available scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start the Vite dev server |
| `npm run build` | Type-check and build for production |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run ESLint |
| `npm run lint:fix` | Run ESLint with autofix |
| `npm run type-check` | Run the TypeScript compiler without emitting |
| `npm run test` | Run unit tests (Vitest) |
| `npm run test:coverage` | Run unit tests with coverage |

## Path aliases

Configured in `vite.config.ts`:

| Alias | Path |
|-------|------|
| `@` | `./src` |
| `@app` | `./src/app` |
| `@modules` | `./src/modules` |
| `@shared` | `./src/shared` |

## Project structure

```
frontend/
├── src/          # application source
├── public/       # static assets
├── e2e/          # Playwright end-to-end tests
├── index.html    # app entry point
└── vite.config.ts
```
