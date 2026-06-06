# wcp-docker-agent

An authenticated HTTP proxy that exposes a remote Docker socket over REST, secured
with a Bearer token. Designed to run on a NAS or remote host so the
[WCP Docker widget](https://hub.docker.com/r/penrithbeacon/wcp-widget-docker)
can manage containers on that host without opening the Docker socket directly.

**Specification:** [widgetcontextprotocol.com](https://widgetcontextprotocol.com)

## Quick Start

```bash
docker run -d \
  --name wcp-docker-agent \
  -p 3745:3745 \
  -v /var/run/docker.sock:/var/run/docker.sock:rw \
  -v agent_data:/app/data \
  -e CONTAINER_NAME=wcp-docker-agent \
  --restart unless-stopped \
  penrithbeacon/wcp-docker-agent:latest
```

On first start the agent generates a Bearer token and prints it to stdout:

```
[wcp-docker-agent] *** Bearer token (save this): <token> ***
```

Retrieve it at any time with:
```bash
docker logs wcp-docker-agent 2>&1 | grep "Bearer token" | head -1
```

Paste the token into the Docker widget's Settings instrument (`NAS Agent Token` field).

## Docker Compose

```yaml
services:
  wcp-docker-agent:
    image: penrithbeacon/wcp-docker-agent:latest
    container_name: wcp-docker-agent
    ports:
      - "3745:3745"
    environment:
      - CONTAINER_NAME=wcp-docker-agent
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - agent_data:/app/data
    restart: unless-stopped

volumes:
  agent_data:
```

## Authentication

Every endpoint (except `/health` and `/widget/health`) requires:

```
Authorization: Bearer <token>
```

The token is stored in the `agent_data` volume at `/app/data/token.txt` and
persists across container restarts. To rotate: delete the volume and recreate
the container.

## Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `GET /health` | None | Health check — same as `/widget/health` |
| `GET /widget/health` | None | WCP-standard health check |
| `GET /containers` | Bearer | List all containers |
| `GET /images` | Bearer | List all images |
| `POST /containers/<id>/start` | Bearer | Start a container |
| `POST /containers/<id>/stop` | Bearer | Stop a container |
| `POST /containers/<id>/restart` | Bearer | Restart a container |

## Health Response

```json
{"status": "ok", "name": "wcp-docker-agent", "version": "1.1.0", "container": "wcp-docker-agent"}
```

## Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release — multi-arch (`linux/amd64`, `linux/arm64`) |
| `1.1.0` | v1.1.0 — `/widget/health` alias, `container` + `version` fields in health response |
| `1.0.0` | v1.0.0 — initial release, Bearer-authenticated Docker proxy |

## Source

- Docker Hub: [penrithbeacon/wcp-docker-agent](https://hub.docker.com/r/penrithbeacon/wcp-docker-agent)
- GitHub: [penrithbeacon/wcp-docker-agent](https://github.com/penrithbeacon/wcp-docker-agent)
- WCP Specification: [widgetcontextprotocol.com](https://widgetcontextprotocol.com)
