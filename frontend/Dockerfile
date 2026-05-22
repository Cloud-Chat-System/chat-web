FROM node:20-alpine

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

CMD ["sh", "-c", "npm run dev -- --host ${FRONTEND_HOST} --port ${FRONTEND_CONTAINER_PORT}"]
