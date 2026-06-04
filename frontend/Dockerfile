FROM node:20-alpine

WORKDIR /app

RUN chown node:node /app

COPY --chmod=440 --chown=root:node package*.json ./

USER node

RUN npm ci

COPY --chmod=440 --chown=root:node index.html vite.config.js ./
COPY --chmod=550 --chown=root:node public ./public
COPY --chmod=550 --chown=root:node src ./src

CMD ["sh", "-c", "npm run dev -- --host ${FRONTEND_HOST} --port ${FRONTEND_CONTAINER_PORT}"]
