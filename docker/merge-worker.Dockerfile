FROM node:20-bookworm-slim AS deps

WORKDIR /srv/merge

COPY workers/node_merge/package.json ./package.json

RUN npm install --omit=dev

FROM node:20-bookworm-slim

WORKDIR /srv/merge

COPY --from=deps /srv/merge/node_modules ./node_modules
COPY workers/node_merge/package.json ./package.json
COPY workers/node_merge/merge_worker.js ./merge_worker.js
COPY workers/node_merge/server.js ./server.js

RUN mkdir -p /data/jobs && chown -R node:node /srv/merge /data/jobs

ENV NODE_ENV=production \
    JOB_STORAGE_ROOT=/data/jobs \
    PORT=3000

USER node

EXPOSE 3000

CMD ["npm", "start"]
