FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY docker-entrypoint-companion.sh /docker-entrypoint-companion.sh
COPY index.html app.js style.css /usr/share/nginx/html/

RUN chmod +x /docker-entrypoint-companion.sh

ENTRYPOINT ["/docker-entrypoint-companion.sh"]
