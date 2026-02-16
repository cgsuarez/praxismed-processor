# Ejecute alembic

- Create the Schema

```
create schema praxismd
```

- Execute alembic upgrade

```
alembic upgrade head
```

# Run the agent

```
python3 -m uvicorn main:app --reload
```

# Clear the cache

- Go into the Redis container

```
docker container exec -it 594ec7fae865 /bin/bash
redis-cli
FLUSHDB
```

- To list the sessions

```
KEYS "*"
```

- Get the session

```
GET session:593988776655
```