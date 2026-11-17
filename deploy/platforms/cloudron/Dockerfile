# Cloudron runs the image read-only except /app/data (the localstorage
# addon), /tmp and /run - so Soloblog keeps its data folder there
FROM ghcr.io/soloblog/soloblog:1.0.0-beta

ENV DATA_DIR=/app/data \
    HOSTED_ON=Cloudron

COPY start.sh /app/pkg/start.sh

CMD ["/app/pkg/start.sh"]
