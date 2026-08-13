# 智慧医疗前端镜像（多阶段：node 构建 → nginx 静态托管）
# 构建上下文必须为 frontend/（避免根目录 .npmrc 的 Windows 缓存路径进镜像）
# 基础镜像钉到国内快的 daocloud 镜像源（绕过 Docker Hub 慢源）
FROM docker.m.daocloud.io/library/node:22-alpine AS build
WORKDIR /app
# 国内 npm 镜像源（避免直连 registry.npmjs.org 超时）
RUN npm config set registry https://registry.npmmirror.com
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM docker.m.daocloud.io/library/nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# history 路由回退 + /api、/static 反代后端
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
