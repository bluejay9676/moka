# Moka

`Moka` is the project name for Mocha Jump's (https://mochajump.com/) backend.

## Settings

### Dev (Local)

Unlike production where google default authentication automatically picks up
all the necessary authentication information, we need to retrieve signed private keys
from the service accounts. Refer to `Setup` section below.

For setting up a private storage and accessing via CDN, look at https://medium.com/@reisfeld/google-cloud-cdn-best-practice-ed643558120e

### Production

- Firebase (Auth): `Mocha`
- GCP:
  - Cloud Run
  - SQL (PostGres)
  - Storage
  - Load Balancer
  - CDN
  - Scheduler
- Cloudflare:
  - Argo
  - Pages

Make sure to periodically remove built images from the image registry to avoid hogging memory.

As of now, we are able to track environment variables adhoc, but this is not scalable. In the long term we need to migrate to using terraform.

You will note that there are several code paths that run differently based on the environment. Refer to our V1 prod release post mortem on why this is the case (https://jayryu.notion.site/Mocha-Jump-V1-Production-Release-Post-mortem-6f0a948b4dac4a1b81b44023d2fbac6e). However this setup is not ideal. Dev env should reflect prod env as closely as possible.

For setting up a private storage and accessing via CDN in production, refer to https://medium.com/@reisfeld/google-cloud-cdn-best-practice-ed643558120e.

## Setup

### Dev

On firebase create an app,
go to `Project Settings` > `Service accounts` > Generate new private key
Save to the root of this project as `firebase-admin-creds.json`

Go to IAM, service accounts page.
Grab keys for the app.
Select `Add Key` and save to the root of this project as `gcp-creds.json`

These creds will be used for running a local server

### Load Balancer (404 on image loading)

Use `gc-ld-config` file to reconfig the load balancer on GCP. We need to rewrite the paths.
For instance, our path rule of `/images/*` will route `https://images.mochajump.com/images/asdf` to `gs://moka-prod-1/images/asdf`. However we are tryig to access `gs://moka-prod-1/asdf`. So we need to rewrute the url `/images/*` to `/`.
https://stackoverflow.com/questions/47113408/google-cdn-connection-to-cdn-create-nosuch-key-errors

## Workflow

See Makefile

```
# Inital build
make pull

# Run django app
make run

# Run shell on docker image
make shell

# Locally run collectstatic
make collectstatic

# Locally run migrations
make make-migration
make run-migrations

# Run test
make test

```

## Make migrations

```
# Run migration based on production db
make make-migrations-mockprod

# Apply migration in prod db (Dangerous!)
make run-migrates-mockprod
```

Note that migrations should be backward compatible and needs to be forward fixed only.

The best practice is to have a separate PR for just the migration.

## Build & Deploy

```
gcloud builds submit --config cloudbuild.yaml

gcloud run deploy --image gcr.io/cosmic-quarter-343904/moka
```

## Debugging

go to docker-compose.debug.yml and right click to docker compose up. Then attach python debugger to the port as defined in the compose yml and the launch.json.

## VSCode Interpreter: Activate virtualenv for non-docker dev

```
python3 -m venv ./.venv
source ./.venv/bin/activate
export $(cat .env.dev | xargs)
```

And set interpreter on VSCode as venv

## Installing Precommit hooks (Linters)

```
pip install pre-commit
pre-commit install
```

## Troubleshooting

### After running django makemigrations or startapp

You may not have the read/write access to the generated files. In such case, you need to run:

```
# After generating app through docker shell
sudo chown -R nunojay ./moka/generated-app/
```

### Why do I have to access 127.0.0.1:8000 (localhost:8000) instead of 0.0.0.0:8000?

in entrypoint.sh we run `exec python /code/moka/manage.py runserver 0.0.0.0:8000`
and finally, go to http://127.0.0.1:8000/ in your browser.

Why? Well, Python thinks you're exposing it on 127.0.0.1 when in reality you want the eth0 address, since that can change, and we don't want to hard code it, we use 0.0.0.0 which means "ALL" interfaces.

Remember docker 127.0.0.1 IS NOT your host 127.0.0.1, each docker container has its own loopback.

You must set a container’s main process to bind to the special 0.0.0.0 “all interfaces” address, or it will be unreachable from outside the container.

In Docker 127.0.0.1 almost always means “this container”, not “this machine”. If you make an outbound connection to 127.0.0.1 from a container it will return to the same container; if you bind a server to 127.0.0.1 it will not accept connections from outside.

## Clashing API paths

You will run into 405/422 status code when you have these two paths in the same router

```
## https://github.com/vitalik/django-ninja/issues/203
@router.get('/{int:id}')
@router.get('/something')
```

django-ninja won't be able to distinguish the two and will throw 422. To avoid this, create a different router or
make the second api path more descriptive `/something/this`.

## Accessing Local PostgresSQL directly

```
# Access Django test db
docker exec -it moka-backend-db-1 psql -U api_dev_user -d test_api_dev_db
```
