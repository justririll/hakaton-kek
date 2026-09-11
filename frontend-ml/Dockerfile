FROM nginx:alpine

COPY frontend-ml/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend-ml/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
