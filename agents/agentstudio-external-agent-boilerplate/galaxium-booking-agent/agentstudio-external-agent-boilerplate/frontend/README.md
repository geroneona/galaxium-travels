# About

This is a simple frontend speaking the A2A protocol which can be connected
to the provided `langgraph` or `crewai_a2a` backend.

## Local Development

Install the dependencies:

```bash
npm i
```

Run the application

```bash
npm run dev
```

Run e2e tests
```bash
npm run test:e2e
# run single test
npm run test:e2e -- e2e/send-hello.spec.ts
```

Build a podman image

```bash
npm run podman:build
```

Run a podman container

```bash
npm run podman:run
```

### Configuration

No configuration is needed to run the application locally without authentication. If you need some overrides, copy the `.env.example` file to `.env` and edit the values as needed.
