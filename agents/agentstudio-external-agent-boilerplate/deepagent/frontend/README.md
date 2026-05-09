# Recruitment Assistant Frontend

React frontend for the Recruitment Assistant agent. Allows users to manage CVs and job descriptions, then ask the agent free-form questions about them.

## Features

- Manage a list of CVs (name + foldable content)
- Manage a list of job descriptions (title + foldable description)
- Free-form question input sent to the A2A backend agent
- Q&A history with the most recent answer at the top
- Optional Keycloak authentication

## Local Development

Install dependencies:

```bash
npm install
```

Run the development server:

```bash
npm run dev
```

The app connects to `http://localhost:8000` by default (the sibling `backend` service).

## Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable | Description | Default |
|---|---|---|
| `VITE_BACKEND_URL` | URL of the A2A backend agent | `http://localhost:8000` |
| `VITE_KEYCLOAK_ISSUER_URL` | Keycloak issuer URL (optional) | — |
| `VITE_KEYCLOAK_CLIENT_ID` | Keycloak client ID (optional) | — |

Keycloak is only enabled when both `VITE_KEYCLOAK_ISSUER_URL` and `VITE_KEYCLOAK_CLIENT_ID` are set.

## Build

```bash
npm run build
```

Output is placed in `dist/`.
