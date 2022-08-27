
# agent-academy-1

[El Collectooorr](https://www.elcollectooorr.art/) is an autonomous service that watches for new Art Blocks drops and intelligently collects new works for you. This agent service has been created using the Autonolas stack as part of Valory's Agent Academy 1.

This repository holds the code for the [FSM apps](https://docs.autonolas.network/fsm_app_introduction) used in the El Collectooorr.

## Cloning

- Clone the repository, and recursively clone the submodules:

      ```bash
      git clone --recursive git@github.com:valory-xyz/agent-academy-1.git
      ```

- Note: to update the Git submodules later:

      ```bash
      git submodule update --init --recursive
      ```

## Requirements & Setup

- Refer to requirements for [open-autonomy](https://github.com/valory-xyz/open-autonomy) in the requirements section of the README.

- Build the Hardhat projects:

      ```bash
      cd third_party/safe-contracts && yarn install
      cd ../contracts-elcol && yarn install
      cd ../..
      ```

- Create a virtual environment with all development dependencies:

      ```bash
      make new_env
      ```

- Enter virtual environment:

      ```bash
      pipenv shell
      ```

- Optionally: run all checks 

      ```bash
      tox
      ```

## Running El Collectooorr as a service

These steps only work for operators registered on-chain!

1. Ensure the service and its dependencies are pushed:
      ```bash
      autonomy init --reset --remote --ipfs
      autonomy push-all
      ```

2. Prepare a JSON file `keys.json` containing the addresses and keys of the agents. Below you have some sample keys for testing. Use these keys for testing purposes only. **Never use these keys in a production environment or for personal use.**. Also, make sure that the addresses have some funds or transactions will fail.

      ```json
      [
      {
            "address": "0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65",
            "private_key": "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a"
      },
      {
            "address": "0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc",
            "private_key": "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba"
      },
      {
            "address": "0x976EA74026E726554dB657fA54763abd0C3a0aa9",
            "private_key": "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e"
      },
      {
            "address": "0x14dC79964da2C08b23698B3D3cc7Ca32193d9955",
            "private_key": "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356"
      }
      ]
      ```

3. Run the service:

      - Option 1: Step-by-step

      ```bash
      autonomy fetch elcollectooorr/elcollectooorr:0.1.0:bafybeidifw22pd3asyglwrfkamhiho6q7pc3erasejwg6clshxplzr3smq --service
      cd elcollectooorr
      ```

      Replace the API key placeholder for the RPC endpoint.

      ```bash
      autonomy build-image
      autonomy deploy build keys.json --force --local
      ```

      (On MAC OS manually update permissions with `chmod 777 abci_build` and it's subfolders!)

      Substitute the safe address taken from on-chain. In `abci_build/docker-compose.yaml`, replace
      ```bash
            - SKILL_ELCOLLECTOOORR_ABCI_MODELS_PARAMS_ARGS_SETUP_SAFE_CONTRACT_ADDRESS=[]
      ```
      with
      ```bash
            - SKILL_ELCOLLECTOOORR_ABCI_MODELS_PARAMS_ARGS_SETUP_SAFE_CONTRACT_ADDRESS=["0x123a3d66cf688b676f9b7a6bcc3991f62fec7f0a"]
      ```
      where `0x123a3d66cf688b676f9b7a6bcc3991f62fec7f0a` should match the correct address from the on-chain service deployment.

      Then run the service:

      ``` bash
      cd abci_build
      docker-compose up --force-recreate
      ```

      - Option 2: One-step (requires on-chain to reference the correct hash)

      ```bash
      autonomy deploy from-token 1 keys.json
      ````

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make formatters`, `make generators`, `make code-checks`, as well
as `make common-checks-1`. To run all tests use `make test`. Or simply use `tox`.

### Running a fork of Ethereum

You can run a fork of Ethereum Mainnet via [ganache](https://github.com/trufflesuite/ganache) in the following way:
```
ganache --fork.network mainnet
```
