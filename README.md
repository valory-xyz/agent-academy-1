# agent-academy-1
Valory's Agent Academy 1 - participant repo

## System requirements

- Python `>=3.7`
- [Tendermint](https://docs.tendermint.com/master/introduction/install.html) `==0.34.11`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`

Alternatively, you can fetch this docker image with the relevant requirments satisfied:

        docker pull valory/dev-template:latest
        docker container run -it valory/dev-template:latest

## Simple ABCI example

Create a virtual environment with all development dependencies: 

```bash
make new_env
```

Enter virtual environment:

``` bash
pipenv shell
```

To run the test:

``` bash
pytest tests/test_packages/test_agents/test_simple_abci.py::TestSimpleABCISingleAgent
```

or

``` bash
pytest tests/test_packages/test_agents/test_simple_abci.py::TestSimpleABCITwoAgents
```

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well as `make hashes`. To run all tests use `make test`.
