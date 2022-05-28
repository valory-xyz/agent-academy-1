/*global hre*/

// Contract names that are used more often in the scripts
const gnosisSafeContractName = "./third_party/safe-contracts/contracts/GnosisSafe.sol:GnosisSafe";
const gnosisSafeL2ContractName = "GnosisSafeL2";
const gnosisProxyFactoryContractName = "GnosisSafeProxyFactory";
const defaultFallbackHandlerContractName = "DefaultCallbackHandler";
const wethContractName = "./third_party/canonical-weth/contracts/WETH9.sol:WETH9";
const basketFactoryContractName = "BasketFactory";
const erc721VaultFactoryContractName = "ERC721VaultFactory";
const settingsContractName = "Settings";
const artblocksCoreContractName = "GenArt721Core";
const artblocksRandomizerContractName = "MockRandomizer";
const artblocksMinterFilterV0ContractName = "MinterFilterV0";
const artblocksMinterSetPriceV0ContractName = "MinterSetPriceV0";
const artblocksMinterDALinV0ContractName = "MinterDALinV0";
const artblocksMinterDAExpV0ContractName = "MinterDAExpV0";


// List of contract names to deploy
const contractNameList = [
    gnosisProxyFactoryContractName,
    gnosisSafeL2ContractName,
    gnosisSafeContractName,
    defaultFallbackHandlerContractName,
    wethContractName,
    "SimulateTxAccessor",
    "CompatibilityFallbackHandler",
    "CreateCall",
    "MultiSend",
    "MultiSendCallOnly",
    "SignMessageLib",
];

// Map of contract names <-> addresses for the verification
// If you swap the rows, the contract addresses are deterministic and should not change the row number
// TODO: Prefill deterministic set of addresses for testing purposes, such that we know for every new
// contract which address will be assigned.
const contrAddrMap = new Map([
    [gnosisProxyFactoryContractName, "0x5FbDB2315678afecb367f032d93F642f64180aa3"],
    [gnosisSafeL2ContractName, "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"],
    [gnosisSafeContractName, "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"],
    [defaultFallbackHandlerContractName, "0xCf7Ed3AccA5a467e9e704C703E8D87F634fB0Fc9"],
    [wethContractName, "0xDc64a140Aa3E981100a9becA4E685f962f0cF6C9"],
    ["SimulateTxAccessor", "0x5FC8d32690cc91D4c39d9d3abcBD16989F875707"],
    ["CompatibilityFallbackHandler", "0x0165878A594ca255338adfa4d48449f69242Eb8F"],
    ["CreateCall", "0xa513E6E4b8f2a923D98304ec87F64353C4D5C853"],
    ["MultiSend", "0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6"],
    ["MultiSendCallOnly", "0x8A791620dd6260079BF849Dc5567aDC3F2FdC318"],
    ["SignMessageLib", "0x610178dA211FEF7D417bC0e6FeD39F05609AD788"],
    [settingsContractName, "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"],
    [erc721VaultFactoryContractName, "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0"],
    [basketFactoryContractName, "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82"],
    [artblocksRandomizerContractName, "0x9A676e781A523b5d0C0e43731313A708CB607508"],
    [artblocksCoreContractName, "0x0B306BF915C4d645ff596e518fAf3F9669b97016"],
    [artblocksMinterFilterV0ContractName, "0x959922bE3CAee4b8Cd9a407cc3ac1C251C2007B1"],
    [artblocksMinterDAExpV0ContractName, "0x3Aa5ebB10DC797CAC828524e59A333d0A371443c"],
    [artblocksMinterDALinV0ContractName, "0x68B1D87F95878fE05B998F19b66F4baba5De1aed"],
    [artblocksMinterSetPriceV0ContractName, "0x9A9f2CCfdE556A7E9Ff0848998Aa4a0CFD8863AE"],
]);


// Map of contract names <-> contract instances
let contractMap = new Map();

// Map of tokens <-> token instances
let tokenMap = new Map();

// Function to deploy a contract by the contract name / path
async function deployContract(contractName) {
    const Contract = await hre.ethers.getContractFactory(contractName);
    const contractInstance = await Contract.deploy();
    await contractInstance.deployed();
    return contractInstance;
}

// Verify deployed contract addresses. For testing purposes.
async function verifyContractAddresses() {
    contractMap.forEach((value, key) => {
        if (value != contrAddrMap.get(key)) {
            throw new Error("Address matching failed for " + key + " contract");
        }
    });
}

module.exports.gnosisProxyFactoryContractName = gnosisProxyFactoryContractName;
module.exports.gnosisSafeL2ContractName = gnosisSafeL2ContractName;
module.exports.gnosisSafeContractName = gnosisSafeContractName;
module.exports.defaultFallbackHandlerContractName = defaultFallbackHandlerContractName;
module.exports.wethContractName = wethContractName;
module.exports.erc721VaultFactoryContractName = erc721VaultFactoryContractName;
module.exports.settingsContractName = settingsContractName;
module.exports.basketFactoryContractName = basketFactoryContractName;
module.exports.contractNameList = contractNameList;
module.exports.contractMap = contractMap;
module.exports.tokenMap = tokenMap;
module.exports.artblocksCoreContractName = artblocksCoreContractName;
module.exports.artblocksRandomizerContractName = artblocksRandomizerContractName;
module.exports.artblocksMinterFilterV0ContractName = artblocksMinterFilterV0ContractName;
module.exports.artblocksMinterSetPriceV0ContractName = artblocksMinterSetPriceV0ContractName;
module.exports.artblocksMinterDALinV0ContractName = artblocksMinterDALinV0ContractName;
module.exports.artblocksMinterDAExpV0ContractName = artblocksMinterDAExpV0ContractName;
module.exports.artblocksMinterSetPriceContractName = artblocksMinterSetPriceV0ContractName;
module.exports.deployContract = deployContract;
module.exports.verifyContractAddresses = verifyContractAddresses;