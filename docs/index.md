![MintKit](images/mintkit.svg){ align=left }
The MintKit is a toolkit to build services with minting capabilities. For example, El Collectooorr service, which is based on the MintKit, aims to autonomously create collections of NFTs by minting them as they drop on Art Blocks. It uses complex logic to decide which mints to participate in and what prices to bid at, so users don’t have to. The service is fuelled by the community of users who fund collections. Each collection is designed to have its own unique ERC-20 token, for users to vote and collectively decide on what happens to the collection.

## Demo

!!! warning "Important"

	This section is under active development - please report issues in the [Autonolas Discord](https://discord.com/invite/z2PT65jKqQ).

In order to run a local demo of the El Collectooorr service:

1. [Set up your system](https://docs.autonolas.network/open-autonomy/guides/set_up/) to work with the Open Autonomy framework. We recommend that you use these commands:

    ```bash
    mkdir your_workspace && cd your_workspace
    touch Pipfile && pipenv --python 3.10 && pipenv shell

    pipenv install open-autonomy[all]==0.10.3
    autonomy init --remote --ipfs --reset --author=your_name
    ```

2. Fetch the El Collectooorr service.

	```bash
	autonomy fetch elcollectooorr/elcollectooorr:0.1.0:bafybeid2u6uibyeexb2v6lnjgtrgsu7a4ol56prd4iyhclqvx22k6wv5xi --service
	```

3. Build the Docker image of the service agents

	```bash
	cd elcollectooorr
	autonomy build-image
	```

4. Prepare the `keys.json` file containing the wallet address and the private key for each of the agents.

    ??? example "Example of a `keys.json` file"

        <span style="color:red">**WARNING: Use this file for testing purposes only. Never use the keys or addresses provided in this example in a production environment or for personal use.**</span>

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

   5. Prepare the environment and build the service deployment.

       1. Export the required environment variables.

          ```bash
          export SAFE_CONTRACT_ADDRESS="0x123a3d66cf688b676f9b7a6bcc3991f62fec7f0a"
          export WHITELISTED_INVESTOR_ADDRESSES='["YOUR_WHITELISTED_ADDRESS"]'
          export SERVICE_ELCOLLECTOOORR_RPC_0="YOUR_RPC_URL"
          export SERVICE_ELCOLLECTOOORR_RPC_1="YOUR_RPC_URL"
          export SERVICE_ELCOLLECTOOORR_RPC_2="YOUR_RPC_URL"
          export SERVICE_ELCOLLECTOOORR_RPC_3="YOUR_RPC_URL"
          export ALL_PARTICIPANTS='["0x15d34AAf54267DB7D7c367839AAf71A00a2C6A65","0x9965507D1a55bcC2695C58ba16FB37d819B0A4dc","0x976EA74026E726554dB657fA54763abd0C3a0aa9","0x14dC79964da2C08b23698B3D3cc7Ca32193d9955"]'
          ```

          where `0x123a3d66cf688b676f9b7a6bcc3991f62fec7f0a` should match the correct address from the on-chain service deployment, and `YOUR_WHITELISTED_ADDRESS`, `YOUR_RPC_URL` should be replaced accordingly.
          Note that `0x123a3d66cf688b676f9b7a6bcc3991f62fec7f0a` is the mainnet safe address of the El Collectooorr. You will be able to run the service by setting this address. However, any on-chain transaction will fail unless you have the operator keys.


        !!! warning "Important"

            The keys provided in this example are for testing purposes. You must ensure to use your own keys in the `keys.json` file, and ensure that the environment variable `ALL_PARTICIPANTS` matches their addresses.

       2. Build the service deployment.

          ```bash
          autonomy deploy build keys.json --aev -ltm
          ```

6. Run the service.

	```bash
	cd abci_build
	autonomy deploy run
	```

	You can cancel the local execution at any time by pressing ++ctrl+c++.

## Build

1. Fork the [MintKit repository](https://github.com/valory-xyz/agent-academy-1).
2. Make the necessary adjustments to tailor the service to your needs. This could include:
    * Adjust configuration parameters (e.g., in the `service.yaml` file).
    * Expand the service finite-state machine with your custom states.
3. Run your service as detailed above.

!!! tip "Looking for help building your own?"

    Refer to the [Autonolas Discord community](https://discord.com/invite/z2PT65jKqQ), or consider ecosystem services like [Valory Propel](https://propel.valory.xyz) for the fastest way to get your first autonomous service in production.