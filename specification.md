# Docker Agent — Specification

## Overview
Authenticated Docker proxy for NAS deployment. Exposes local Docker socket over HTTP, protected by a Bearer token. Used by the Docker widget's NAS view to manage containers remotely.

- **Port:** 3745
- **Container:** `wcp-docker-agent`
- **Image:** `docker.io/penrithbeacon/wcp-docker-agent`

## Version
- **Widget:** 1.2.0
- **WCP:** 2.1.0 (pending — discovery endpoints not yet implemented)
- **Docker tag:** `1.1.0`

## Controls (HTML Templates)

| Template | Route | Purpose | Default Size |
|----------|-------|---------|--------------|
| (none) | — | No user-facing HTML templates | — |

**Note:** Docker Agent is a headless API proxy — it has no HTML templates. The `/widget/index` page will list the API endpoints instead.

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/health` | Health check (legacy path) |
| GET | `/widget/health` | Health check (WCP path) |
| GET | `/containers` | List Docker containers (auth required) |
| GET | `/images` | List Docker images (auth required) |
| POST | `/containers/<cid>/<action>` | Container actions: start/stop/restart (auth required) |

### Missing Endpoints (to be added)
| Method | Route | Purpose |
|--------|-------|---------|
| GET | `/wcp` | Container directory |
| GET | `/widget/wcp` | Widget manifest |
| OPTIONS | `/wcp` | CORS preflight |
| GET | `/widget/index` | Widget index page |

## Authentication
- Bearer token authentication on all `/containers` and `/images` routes
- Token auto-generated on first run, stored in `/app/data/token.txt`
- Token printed to stdout on container startup

## Features
- Docker socket proxy over HTTP
- Bearer token authentication
- Container listing with status, ports, image info
- Image listing with size, tags, creation date
- Container lifecycle management (start/stop/restart)
- Human-readable size formatting

## Configuration
- No user configuration — token is auto-generated

## Data Persistence
- Token file: `/app/data/token.txt` (auto-generated)

## Dependencies
- Python: `flask`, `docker` (Docker SDK)
- Local: Docker socket (`/var/run/docker.sock`)
- No external API dependencies

## Known Compliance Gaps
- Missing `WCP_MANIFEST` definition
- Missing `GET /wcp` (container directory)
- Missing `GET /widget/wcp` (widget manifest)
- Missing `OPTIONS /wcp` (CORS preflight)
- Missing `GET /widget/index` (widget index)
- Missing `GET /widget/icon.svg`
- Missing `GET /widget/api/guids`
- No HTML templates (headless proxy)
- Docker tag format doesn't include WCP version
