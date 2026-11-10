# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# Reuse the locally tested Keycloak version, with an isolated Postgres database.
FROM quay.io/keycloak/keycloak:26.8.0 AS builder
ENV KC_DB=postgres KC_HEALTH_ENABLED=true
RUN /opt/keycloak/bin/kc.sh build
FROM quay.io/keycloak/keycloak:26.8.0
COPY --from=builder /opt/keycloak/ /opt/keycloak/
ENV KC_DB=postgres KC_HEALTH_ENABLED=true KC_HTTP_ENABLED=true KC_PROXY_HEADERS=xforwarded KC_HOSTNAME_STRICT=true
ENTRYPOINT ["/opt/keycloak/bin/kc.sh"]
# No dev-mode database, realm import, test users or bootstrap password is embedded.
CMD ["start", "--optimized"]
