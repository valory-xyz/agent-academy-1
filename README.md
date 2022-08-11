
# agent-academy-1

[El Collectooorr](https://www.elcollectooorr.art/) is an autonomous service that watches for new Art Blocks drops and intelligently collects new works for you. This agent service has been created using the Autonolas stack as part of Valory's Agent Academy 1.
This repository holds the code for the [FSM apps](https://docs.autonolas.network/fsm_app_introduction) used in the El Collectooorr.

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
- [Go](https://go.dev/doc/install) `==1.17.7`
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

Populate the test data used in the tests:
```bash
make test-data
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

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make lint`, `make static` and `make pylint`, as well
as `make hashes`. To run all tests use `make test`.

### Running a fork of Ethereum
You can run a fork of Ethereum Mainnet via [ganache](https://github.com/trufflesuite/ganache) in the following way:
```
ganache --fork.network mainnet
```
