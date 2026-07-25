# Startup Commands

## Start all services (with rebuild)
```bash
docker-compose up --build
```

## Start all services (no rebuild)
```bash
docker-compose up
```

## Start all services in background
```bash
docker-compose up -d
```

## Stop all services
```bash
docker-compose down
```

## Rebuild and restart a single service
```bash
docker-compose up --build -d <service-name>
```
Available service names: `gateway`, `user-service`, `topic-service`, `ai-service`, `frontend`, `mongodb`

## Check status
```bash
docker-compose ps
```

## View logs
```bash
docker-compose logs -f                    # all services
docker-compose logs -f <service-name>     # single service
```
