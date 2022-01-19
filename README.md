# agent-academy-1

Valory's Agent Academy 1 - participant repo

- Clone the repository, and recursively clone the submodules:

      git clone --recursive git@github.com:valory-xyz/agent-academy-1.git

  Note: to update the Git submodules later:

      git submodule update --init --recursive

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

## Fuzzy Tests for ABCI Connection

To run the fuzzy tests with TCP as the communication channel, run:

```bash
make tcp-fuzzy-tests
```

For gRPC run:

To run the fuzzy tests with TCP as the communication channel, run:

```bash
make grpc-fuzzy-tests
```

To run both, use:
To run the fuzzy tests with TCP as the communication channel, run:

```bash
make fuzzy-tests
```
- Build the Hardhat projects:

      cd third_party/safe-contracts && yarn install
      cd ../..

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well
as `make hashes`. To run all tests use `make test`.
