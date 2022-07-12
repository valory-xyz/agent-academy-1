require("@nomiclabs/hardhat-waffle");
require("solidity-coverage");
require("hardhat-deploy");
require("@ethersproject/constants");
require("@gnosis.pm/safe-contracts");

// import('hardhat/config').HardhatUserConfig;
// import('hardhat/config').HttpNetworkUserConfig;
// import("dotenv").dotenv;
// import("yargs").yargs;

// const argv = yargs
//   .option("network", {
//     type: "string",
//     default: "hardhat",
//   })
//   .help(false)
//   .version(false).argv;

// // Load environment variables.
// dotenv.config();
// const { NODE_URL, INFURA_KEY, MNEMONIC, ETHERSCAN_API_KEY, PK, SOLIDITY_VERSION, SOLIDITY_SETTINGS } = process.env;

// const DEFAULT_MNEMONIC =
//   "candy maple cake sugar pudding cream honey rich smooth crumble sweet treat";

// const sharedNetworkConfig: HttpNetworkUserConfig = {};
// if (PK) {
//   sharedNetworkConfig.accounts = [PK];
// } else {
//   sharedNetworkConfig.accounts = {
//     mnemonic: MNEMONIC || DEFAULT_MNEMONIC,
//   };
// }

// if (["mainnet", "ropsten", "rinkeby", "kovan", "goerli"].includes(argv.network) && INFURA_KEY === undefined) {
//   throw new Error(
//     `Could not find Infura key in env, unable to connect to network ${argv.network}`,
//   );
// }

// This is a sample Hardhat task. To learn how to create your own go to
// https://hardhat.org/guides/create-task.html

// eslint-disable-next-line
task("accounts", "Prints the list of accounts", async (taskArgs, hre) => {
    const accounts = await hre.ethers.getSigners();

    for (const account of accounts) {
        console.log(account.address);
    }
});

// eslint-disable-next-line
task("deploy-contracts", "Deploys and verifies contracts")
    .setAction(async (_, hre) => {
        await hre.run("deploy");
    });

// eslint-disable-next-line
task("extra-compile", "Compile, updates contracts, then run node")
    .addParam("port", "The port for the node")
    .setAction(async (taskArgs, hre) => {
        await hre.run("compile");
        await hre.run("node", {port: parseInt(taskArgs.port)});
    });


/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
    solidity: {
        compilers: [
            {
                version: "0.5.16",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 1000,
                    },
                },
            },
            {
                version: "0.6.6",
                evmVersion: "istanbul",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 999999,
                    },
                },
            },
            {
                version: "0.7.1",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 1000,
                    },
                },
            },
            {
                version: "0.7.0",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 1000,
                    },
                },
            },
            {
                version: "0.8.2",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 1000,
                    },
                },
            },
            {
                version: "0.8.9",
                settings: {
                    optimizer: {
                        enabled: true,
                        runs: 1000,
                    },
                },
            },
        ],
    },
    paths: {
        sources: "./third_party",
        tests: "./test",
        cache: "./cache",
        artifacts: "./artifacts"
    },
    networks: {
        hardhat: {
            allowUnlimitedContractSize: true,
            accounts: [
                {
                    privateKey: "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1",
                    balance: "100000000000000000000"
                }, 
                {
                    privateKey: "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",
                    balance: "100000000000000000000"
                }, 
                {
                    privateKey: "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c",
                    balance: "100000000000000000000"
                },
                {
                    privateKey: "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913",
                    balance: "100000000000000000000"
                }
            ]
        },
        ganache: {
            url: "http://localhost:8545",
        }
    },
    etherscan: {
        // Your API key for Etherscan
        // Obtain one at https://etherscan.io/
        apiKey: ""
    },
    hardhat: {
        forking: {
            url: "https://eth-mainnet.alchemyapi.io/v2/<key>",
            blockNumber: 13669330
        }
    },
    tenderly: {
        username: "denim",
        project: "project"
    }
};