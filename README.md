
# agent-academy-1

[El Collectooorr](https://www.elcollectooorr.art/) is an autonomous service that watches for new Art Blocks drops and intelligently collects new works for you. This agent service has been created using the Autonolas stack as part of Valory's Agent Academy 1.

## Cloning

- Clone the repository, and recursively clone the submodules:

      git clone --recursive git@github.com:valory-xyz/agent-academy-1.git

  Note: to update the Git submodules later:

      git submodule update --init --recursive

## Requirements

- Python `>= 3.7`
- Yarn `>=1.22.xx`
- Node `>=v12.xx`
- [Tendermint](https://docs.tendermint.com/master/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==v0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Pipenv](https://pipenv.pypa.io/en/latest/install/) `>=2021.x.xx`
- [Go](https://go.dev/doc/install) `==1.14.2`
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Skaffold](https://skaffold.dev/docs/install/#standalone-binary) `>= 1.39.1`

Alternatively, you can fetch this docker image with the relevant requirments satisfied:

        docker pull valory/dev-template:latest
        docker container run -it valory/dev-template:latest

- Build the Hardhat projects:

      cd third_party/safe-contracts && yarn install
      cd ../contracts-elcol && yarn install
      cd ../..

## Running El Collectooorr as a service

Create a virtual environment with all development dependencies:

```bash
make new_env
```

Enter virtual environment:

``` bash
pipenv shell
```

First, ensure the service and its dependencies are pushed:
```
autonomy push-all
```

To run the build:
``` bash
./wrap.py deploy build deployment elcollectooorr/elcollectooorr:0.1.0:bafybeievsxqqih7wnrksuyrotjfvm7vgfsttej5a2fsah5576f7kna7ddu keys.json --force --local
```

(On MAC OS manually update permissions with `chmod 777 abci_build` and it's subfolders!)

Then substitue the safe address taken from onchain. In `abci_build/docker-compose.yaml`, replace
```
      - SKILL_ELCOLLECTOOORR_ABCI_MODELS_PARAMS_ARGS_SETUP_SAFE_CONTRACT_ADDRESS=[]
```
with
```
      - SKILL_ELCOLLECTOOORR_ABCI_MODELS_PARAMS_ARGS_SETUP_SAFE_CONTRACT_ADDRESS=["0xe64C856427C770DEa53E41a0f73C67eE37a16aB4"]
```
where `0xe64C856427C770DEa53E41a0f73C67eE37a16aB4` should match the correct address from the on-chain service deployment.

Then run the service:
``` bash
cd abci_build
docker-compose up --force-recreate
```

## Running a fork of ethereum

### Running the fork locally

You can make a fork using hardhat + an archive node. The following demo uses [Alchemy](https://alchemyapi.io).

You will need:

1. `npm`/`yarn` & `node` & `npx`
2. `hardhat`

To install `hardhat` globally run:

```bash
npm install --save-dev hardhat
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

By default, this will make a fork using block `11844372`. If you want to fork from a given block number, you can do so by setting `BLOCK_NUMBER` to your desired block. Ex.
```bash
BLOCK_NUMBER=123456 make run-ropsten-fork
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

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well
as `make hashes`. To run all tests use `make test`.
