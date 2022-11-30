# Blow everything away and rebuild from scratch -- no caching of
# already-built stages. Use this mostly when you want to pull a fresh
# copy of the upstream base Python container.
pull:
	docker-compose -f ./docker-compose.yml down
	docker-compose -f ./docker-compose.yml build --pull --no-cache mokabackend

pull-debug:
	docker-compose -f ./docker-compose.debug.yml down
	docker-compose -f ./docker-compose.debug.yml build --pull --no-cache mokabackend

run:
	docker-compose -f ./docker-compose.yml up

run-debug:
	docker-compose -f ./docker-compose.debug.yml up

run-mockprod:
	docker-compose -f ./docker-compose.mockprod.yml up

shell:
	docker-compose -f ./docker-compose.yml run mokabackend bash

shell-debug:
	docker-compose -f ./docker-compose.debug.yml run mokabackend bash


# Rebuild both containers, but using cache. Use this when you've made
# changes to the Dockerfile or dependencies, and just need to rebuild
# what's changed.
build:
	docker-compose -f ./docker-compose.yml build mokabackend

build-debug:
	docker-compose -f ./docker-compose.debug.yml build mokabackend

build-mockprod:
	docker-compose -f ./docker-compose.mockprod.yml build mokabackend

collectstatic:
	docker-compose -f ./docker-compose.yml run mokabackend python /code/moka/manage.py collectstatic --no-input

# Generate Django ORM migrations, if any need to be generated.
make-migrations:
	docker-compose -f ./docker-compose.yml run mokabackend python /code/moka/manage.py makemigrations

make-migrations-debug:
	docker-compose -f ./docker-compose.debug.yml run mokabackend python /app/moka/manage.py makemigrations

make-migrations-mockprod:
	docker-compose -f ./docker-compose.mockprod.yml run mokabackend python /code/moka/manage.py makemigrations

run-migrations:
	docker-compose -f ./docker-compose.yml run mokabackend python /code/moka/manage.py migrate

run-migrations-debug:
	docker-compose -f ./docker-compose.debug.yml run mokabackend python /app/moka/manage.py migrate

run-migrations-mockprod:
	docker-compose -f ./docker-compose.mockprod.yml run mokabackend python /code/moka/manage.py migrate

# Run tests.
# make test arg=animals.tests
# # Run all the tests in the animals.tests module
# $ ./manage.py test animals.tests

# # Run all the tests found within the 'animals' package
# $ ./manage.py test animals

# # Run just one test case
# $ ./manage.py test animals.tests.AnimalTestCase

# # Run just one test method
# $ ./manage.py test animals.tests.AnimalTestCase.test_animals_can_speak
test:
	docker-compose -f ./docker-compose.yml run mokabackend python /code/moka/manage.py test $(arg)

test-parallel:
	docker-compose -f ./docker-compose.yml run mokabackend python /code/moka/manage.py test $(arg) --parallel

deploy:
	gcloud builds submit --config cloudbuild.yaml; gcloud run deploy --image gcr.io/cosmic-quarter-343904/moka