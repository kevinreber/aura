FROM node:20-alpine AS base
WORKDIR /app
COPY packages/ui/package.json packages/ui/package-lock.json ./
RUN npm ci
COPY packages/ui/ .

FROM base AS development
ENV NODE_ENV=development
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build
ENV NODE_ENV=production
RUN npm run build

FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/build ./build
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules
RUN addgroup -g 1001 -S appuser && adduser -S appuser -u 1001 -G appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=30s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1
CMD ["npm", "run", "start"]
