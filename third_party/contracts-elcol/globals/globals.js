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
    [gnosisProxyFactoryContractName, "0xD3aA556287Afe63102e5797BFDDd2A1E8DbB3eA5"],
    [gnosisSafeL2ContractName, "0x32Cf1f3a98aeAF57b88b3740875D19912A522c1A"],
    [gnosisSafeContractName, "0xD17e1233A03aFFB9092D5109179B43d6A8828607"],
    [defaultFallbackHandlerContractName, "0x5Cca2cF3f8a0e5a5aF6A1E9A54A0c98510D92081"],
    [wethContractName, "0x559E01ac5e8fe78963998D632e510bEF3e306A78"],
    ["SimulateTxAccessor", "0x1967D06b1fabA91eAadb1be33b277447ea24fa0e"],
    ["CompatibilityFallbackHandler", "0x336e71DaB0302774b1e4c53202bF3f2D1aD1a8e6"],
    ["CreateCall", "0x3635D6aE8610Ea00b6AD8342b819fD21c7Db77Ed"],
    ["MultiSend", "0x9e2C43153aa0007E6172af3733021A227480f008"],
    ["MultiSendCallOnly", "0x3f3993D6a6cE7af16662fbCF2fc270683fC56345"],
    ["SignMessageLib", "0xAEF6182310E3D34b6EA138b60d36A245386f3201"],
    [settingsContractName, "0xb2443146EC9F5a1a5Fd5c1C9C0fe5f5cC459A31A"],
    [erc721VaultFactoryContractName, "0x2C03ca9fb5a7b5B26996c00F7c419C5E9C706196"],
    [basketFactoryContractName, "0x9623B3C78e77Ea8c1A544cB73108B04787f96b08"],
    [artblocksRandomizerContractName, "0xd1a269d9b0dfb66cFdAF89Cf0c6e6F8Df0615ad0"],
    [artblocksCoreContractName, "0xE0F8cEe346A702CCA192a6Ec807ff89B4c6bC70E"],
    [artblocksMinterFilterV0ContractName, "0x3A78BF1783a0187c1C8000e41C2a008897D0a35f"],
    [artblocksMinterDAExpV0ContractName, "0x297D631516A2f66216980c37ce2DE9E1F5CF64e5"],
    [artblocksMinterDALinV0ContractName, "0xC97b465daC9f52A26F2A234c658a57f5B3f15D19"],
    [artblocksMinterSetPriceV0ContractName, "0xfe46A8F577d3367848bdd127173B7d5F14a6088C"],
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