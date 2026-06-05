# wcp-docker-agent

A lightweight authenticated Docker proxy for remote deployment — designed to be deployed
on a NAS or any remote host where you want to expose Docker container and image management
to a [Penrith Beacon WCP](https://penrithbeacon.com) dashboard running on another machine.

**Part of the** [Penrith Beacon WCP](https://penrithbeacon.com) widget suite.  
**Used by:** [wcp-widget-docker](https://github.com/penrithbeacon/wcp-widget-docker)

---

## What it does

`wcp-docker-agent` sits between the `wcp-widget-docker` container (running on your Mac or
server) and the Docker socket on your NAS. It exposes a simple HTTP API protected by a
**Bearer token** that is generated automatically on first start. The widget calls the agent;
the agent calls the local Docker socket; Docker never needs to expose its raw TCP port.

```
Penrith Beacon dashboard
        │
        ▼
wcp-widget-docker (port 3744)
        │  HTTP + Bearer token
        ▼
wcp-docker-agent (port 3745, on NAS)
        │  Unix socket
        ▼
/var/run/docker.sock
```

---

## Security

- **Bearer token** generated with `secrets.token_urlsafe(32)` on first start
- Token written to `/app/data/token.txt` inside the container volume (persists across restarts)
- Token printed **once** to the container log on first start — read it with `docker logs wcp-docker-agent`
- All requests without a valid `Authorization: Bearer <token>` header return `401 Unauthorized`
- No default password — the token is unique to each deployment

---

## Quick Start

```bash
docker run -d \
  --name wcp-docker-agent \
  -p 3745:3745 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v agent_data:/app/data \
  --restart unless-stopped \
  penrithbeacon/wcp-docker-agent:latest
```

**Get your Bearer token (one-time):**

```bash
docker logs wcp-docker-agent
# [wcp-docker-agent] *** Bearer token (save this): <token> ***
```

Paste the URL (`http://<nas-ip>:3745`) and token into the **Docker Settings** instrument
on your Penrith Beacon dashboard.

---

## Docker Compose

```yaml
services:
  wcp-docker-agent:
    image: penrithbeacon/wcp-docker-agent:latest
    container_name: wcp-docker-agent
    ports:
      - "3745:3745"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:rw
      - agent_data:/app/data
    restart: unless-stopped

volumes:
  agent_data:
```

> Place this `docker-compose.yml` on your NAS and run `docker compose up -d`.

---

## Endpoints

All endpoints except `/health` require `Authorization: Bearer <token>`.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /health` | GET | `{"status":"ok","name":"wcp-docker-agent"}` — no auth required |
| `GET /containers` | GET | List all containers (including stopped) |
| `GET /images` | GET | List all images, sorted by creation date descending |
| `POST /containers/<id>/start` | POST | Start a container |
| `POST /containers/<id>/stop` | POST | Stop a container |
| `POST /containers/<id>/restart` | POST | Restart a container |

---

## Response Format

**Containers:**
```json
{
  "success": true,
  "data": {
    "containers": [
      {
        "id": "abc123def456",
        "name": "wcp-widget-radio",
        "image": "penrithbeacon/wcp-widget-radio:latest",
        "state": "running",
        "status": "running",
        "ports": "3741→3741"
      }
    ]
  }
}
```

**Images:**
```json
{
  "success": true,
  "data": {
    "images": [
      {
        "repo": "penrithbeacon/wcp-widget-radio",
        "tag": "latest",
        "id": "abc123def456",
        "size": "124.5 MB",
        "created": "2026-06-05T10:00:00Z"
      }
    ]
  }
}
```

**Errors** (including auth failure):
```json
{ "success": false, "error": "error message" }
```

---

## Example Usage

```bash
TOKEN="your-bearer-token-here"
NAS_URL="http://nas.local:3745"

# List containers
curl -H "Authorization: Bearer $TOKEN" $NAS_URL/containers

# Stop a container
curl -X POST -H "Authorization: Bearer $TOKEN" $NAS_URL/containers/abc123/stop

# Health check (no auth)
curl $NAS_URL/health
```

---

## Technical Details

- **Base image:** `python:3.12-slim`
- **Port:** `3745`
- **Framework:** Flask
- **Dependencies:** Flask, docker (Python SDK)
- **Docker socket:** mounted at `/var/run/docker.sock:rw`
- **Persistent storage:** Named Docker volume for token persistence

---

## NAS Compatibility

Tested on:
- Synology DSM (Docker package or Container Manager)
- QNAP QTS (Container Station)
- Any Linux host with Docker installed

The agent connects to the Docker socket at `unix:///var/run/docker.sock` — the standard
location on all supported platforms.

---

## Links

- [Penrith Beacon](https://penrithbeacon.com)
- [Widget Context Protocol specification](https://widgetcontextprotocol.com)
- [wcp-widget-docker](https://github.com/penrithbeacon/wcp-widget-docker) — the dashboard widget that uses this agent
- [Docker Hub — penrithbeacon/wcp-docker-agent](https://hub.docker.com/r/penrithbeacon/wcp-docker-agent)
