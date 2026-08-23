FROM oven/bun:1 AS builder
WORKDIR /app
COPY package.json bun.lock* ./
RUN bun install --frozen-lockfile
COPY . .
ARG API_BASE_URL
ARG API_KEY
ENV VITE_API_BASE_URL=$API_BASE_URL
ENV VITE_API_KEY=$API_KEY
RUN bun run build

FROM oven/bun:1-slim
WORKDIR /app
COPY --from=builder /app/.output ./.output
ENV HOST=0.0.0.0
ENV PORT=8080
EXPOSE 8080
CMD ["bun", ".output/server/index.mjs"]
