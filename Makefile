.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr pip-wheel-metadata
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -fr {} +
	rm -fr Pipfile.lock

.PHONY: clean-docs
clean-docs:
	rm -fr site/

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
	black packages/valory tests scripts
	isort packages/valory tests scripts
	flake8 packages tests scripts
	darglint packages/valory/agents packages/valory/connections packages/valory/contracts packages/valory/skills tests

.PHONY: pylint
pylint:
	pylint -j4 packages

.PHONY: hashes
hashes:
	python scripts/generate_ipfs_hashes.py --vendor valory

.PHONY: static
static:
	mypy packages tests --disallow-untyped-defs

.PHONY: test
test:
	pytest -rfE tests/ --cov-report=html --cov=packages/valory/skills/simple_abci --cov-report=xml --cov-report=term --cov-report=term-missing --cov-config=.coveragerc
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
	if [ ! -z "$(which svn)" ];\
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
