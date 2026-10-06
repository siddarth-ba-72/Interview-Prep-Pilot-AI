# Frontend for the load-test stack. Same as frontend/Dockerfile, except:
# - VITE_API_BASE_URL is empty, so the app calls /api/v1 on its own origin and nginx proxies it to
#   the gateway, the way Vercel rewrites do in production;
# - the ignore file next to this one keeps local node_modules, dist and .env out of the build.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV VITE_API_BASE_URL=""
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
