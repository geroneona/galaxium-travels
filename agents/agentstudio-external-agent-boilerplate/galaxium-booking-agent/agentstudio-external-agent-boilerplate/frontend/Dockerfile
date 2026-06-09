### Multi-stage Dockerfile: build with Node, serve static site with nginx

FROM node:20-bookworm AS builder
ARG VITE_BACKEND_URL
ARG VITE_A2A_BEARER_TOKEN
ARG VITE_KEYCLOAK_ISSUER_URL
ARG VITE_KEYCLOAK_CLIENT_ID
WORKDIR /app

COPY package.json package-lock.json* pnpm-lock.yaml* ./
RUN npm ci --silent --include=optional

COPY . .
RUN if [ -n "$VITE_BACKEND_URL" ] || [ -n "$VITE_A2A_BEARER_TOKEN" ] || [ -n "$VITE_KEYCLOAK_ISSUER_URL" ] || [ -n "$VITE_KEYCLOAK_CLIENT_ID" ]; then \
      env \
        ${VITE_BACKEND_URL:+VITE_BACKEND_URL=$VITE_BACKEND_URL} \
        ${VITE_A2A_BEARER_TOKEN:+VITE_A2A_BEARER_TOKEN=$VITE_A2A_BEARER_TOKEN} \
        ${VITE_KEYCLOAK_ISSUER_URL:+VITE_KEYCLOAK_ISSUER_URL=$VITE_KEYCLOAK_ISSUER_URL} \
        ${VITE_KEYCLOAK_CLIENT_ID:+VITE_KEYCLOAK_CLIENT_ID=$VITE_KEYCLOAK_CLIENT_ID} \
        npm run build; \
    else \
      npm run build; \
    fi


FROM nginxinc/nginx-unprivileged:stable-bookworm AS runner

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Copy static assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy configs
COPY nginx-main.conf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
