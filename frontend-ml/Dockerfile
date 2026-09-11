# Сборка витрины идёт внутри образа: каталог dist/ под gitignore, и полагаться
# на то, что его кто-то собрал руками перед деплоем, — источник несвежих сборок.
FROM node:20-alpine AS build

WORKDIR /build

# Слой с зависимостями кэшируется отдельно от исходников.
COPY frontend-ml/package.json frontend-ml/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend-ml/ ./
RUN npm run build


FROM nginx:alpine

COPY frontend-ml/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /build/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
