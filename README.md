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

## Running a fork of ethereum

### Running the fork locally

You will need:

1. `npm`/`yarn` & `node` & `npx`
2. `hardhat`

To install `hardhat` globally run:

```bash
npm install --save-dev hardhat
```

You can make a fork using hardhat + an archive node. The following uses [Alchemy](https://alchemyapi.io).

Go to the hardhat dir.

```bash
cd tests/helpers/hardhat
```

For Mainnet run:

```bash
make run-mainnet-fork
```

For Ropsten run:

```bash
make run-ropsten-fork
```

This will create a ledger api (HTTP and WebSocket JSON-RPC) on `http://127.0.0.1:8545` 

By default, this will make a fork using block `11844372`. If you want to fork from a given block number, you can do so by
setting `BLOCK_NUMBER` to your desired block. Ex.
```bash
BLOCK_NUMBER=123 make run-ropsten-fork
```

### Run with docker

To run the forks with docker:
Build the image:
```bash
make build-fork-image
```

To run the MainNet fork:
```bash
make run-mainnet-fork-docker
```

To run the Ropsten fork:
```bash
make run-ropsten-fork-docker
```

By default, the Ropsten container will be available on port `8545`, and MainNet should be available on port `8546`.
You can control what keys to use by setting MAINNET_KEY and ROPSTEN_KEY respectively. 
The docker ports (mappings) can be set using `ROPSTEN_DOCKER_PORT` and `MAINNET_DOCKER_PORT`.
`BLOCK_NUMBER` can be used to change the starting block number.

- Build the Hardhat projects:

      cd third_party/safe-contracts && yarn install
      cd ../..

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well
as `make hashes`. To run all tests use `make test`.
