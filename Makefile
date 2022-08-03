BLOCK_NUMBER ?= 11844372
MAINNET_KEY ?= gP4Np3Qs4ABcu-LCQNDETRklUaW7ouUq
ROPSTEN_KEY ?= WIedVERFqJW1Rlc5Yg6hshrLSCGqzXru
ROPSTEN_DOCKER_PORT ?= 8545
MAINNET_DOCKER_PORT ?= 8546

.PHONY: clean
clean: clean-build clean-pyc clean-test

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr pip-wheel-metadata
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	rm -fr Pipfile.lock

.PHONY: clean-pyc
clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +
	find . -name '.DS_Store' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	rm -fr .tox/
	rm -f .coverage
	find . -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	rm -fr .hypothesis/
	find . -name 'log.txt' -exec rm -fr {} +
	find . -name 'log.*.txt' -exec rm -fr {} +

.PHONY: lint
lint:
	black packages tests scripts
	isort packages tests scripts
	flake8 packages tests scripts
	darglint packages tests

.PHONY: pylint
pylint:
	pylint -j4 packages

.PHONY: hashes
hashes:
	./scripts/hash_patch.py
	#autonomy hash all

.PHONY: static
static:
	mypy packages tests --disallow-untyped-defs

.PHONY: test
test:
	pytest -rfE tests/ --cov-report=html --cov=packages --cov-report=xml --cov-report=term --cov-report=term-missing --cov-config=.coveragerc
	find . -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;

.PHONY: grpc-fuzzy-tests
grpc-fuzzy-tests:
	pytest tests/test_packages/test_connections/fuzzy_tests/fuzzy.py::GrpcFuzzyTests

.PHONY: tcp-fuzzy-tests
tcp-fuzzy-tests:
	pytest tests/test_packages/test_connections/fuzzy_tests/fuzzy.py::TcpFuzzyTests

.PHONY: fuzzy-tests
fuzzy-tests: grpc-fuzzy-tests tcp-fuzzy-tests
	@echo " Running fuzzy tests"

v := $(shell pip -V | grep virtualenvs)

.PHONY: new_env
new_env: clean
	which svn;\
	if [ $$? -ne 0 ];\
	then\
		echo "The development setup requires SVN, exit";\
		exit 1;\
	fi;\
	if [ -z "$v" ];\
	then\
		pipenv --rm;\
		pipenv --python 3.8;\
		pipenv install --dev --skip-lock --clear;\
		echo "Enter virtual environment with all development dependencies now: 'pipenv shell'.";\
	else\
		echo "In a virtual environment! Exit first: 'exit'.";\
	fi
	which pipenv;\
	if [ $$? -ne 0 ];\
	then\
		echo "The development setup requires Pipenv, exit";\
		exit 1;\
	fi;\

.PHONY: run-mainnet-fork
run-mainnet-fork:
	@cd tests/helpers/hardhat;\
  	echo "Forking MainNet on block $(BLOCK_NUMBER)";\
	npx hardhat node --fork https://eth-mainnet.alchemyapi.io/v2/$(MAINNET_KEY) --fork-block-number $(BLOCK_NUMBER)

.PHONY: run-ropsten-fork
run-ropsten-fork:
	@cd tests/helpers/hardhat;\
  	echo "Forking Ropsten on block $(BLOCK_NUMBER)";\
	npx hardhat node --fork https://eth-ropsten.alchemyapi.io/v2/$(ROPSTEN_KEY) --fork-block-number $(BLOCK_NUMBER)

.PHONY: build-fork-image
build-fork-image:
	@echo "Building docker image for hardhat";\
	cd tests/helpers/hardhat;\
	docker build . -t hardhat:latest

.PHONY: run-ropsten-fork-docker
run-ropsten-fork-docker:
	@echo Running ropsten fork as a docker container;\
	docker run -d -e KEY=$(ROPSTEN_KEY) --name ropsten-fork -e NETWORK=ropsten -e BLOCK_NUMBER=$(BLOCK_NUMBER) -p $(ROPSTEN_DOCKER_PORT):8545 hardhat:latest

.PHONY: run-mainnet-fork-docker
run-mainnet-fork-docker:
	@echo Running mainnet fork as a docker container;\
	docker run -d -e KEY=$(MAINNET_KEY) --name mainnet-fork -e NETWORK=mainnet -e BLOCK_NUMBER=$(BLOCK_NUMBER) -p $(MAINNET_DOCKER_PORT):8545 hardhat:latest

.PHONY: copyright
copyright:
	tox -e check-copyright

.PHONY: check_abci_specs
check_abci_specs:
	autonomy analyse abci generate-app-specs packages.valory.skills.elcollectooorr_abci.rounds.ElcollectooorrBaseAbciApp packages/valory/skills/elcollectooorr_abci/fsm_specification.yaml || (echo "Failed to check elcollectooorr abci consistency" && exit 1)
	autonomy analyse abci generate-app-specs packages.valory.skills.elcollectooorr_abci.rounds.ElcollectooorrAbciApp packages/valory/skills/elcollectooorr_abci/fsm_composition_specification.yaml || (echo "Failed to check chained abci consistency" && exit 1)
	echo "Successfully validated abcis!"
