FROM node:20-alpine

WORKDIR /app

RUN chown node:node /app

COPY --chown=node:node package*.json ./

USER node

RUN npm ci

COPY --chown=node:node index.html vite.config.js ./
COPY --chown=node:node public ./public
COPY --chown=node:node src ./src

CMD ["sh", "-c", "npm run dev -- --host ${FRONTEND_HOST} --port ${FRONTEND_CONTAINER_PORT}"]
