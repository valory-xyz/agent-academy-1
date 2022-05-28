const globals = require("../globals/globals.js");

module.exports = async (hre) => {
    const randomizerFactory = await hre.ethers.getContractFactory(globals.artblocksRandomizerContractName);
    const randomizer = await randomizerFactory.deploy();
    await randomizer.deployed();
    console.log(`${globals.artblocksRandomizerContractName} deployed to: ${randomizer.address}`);
    globals.contractMap.set(globals.artblocksRandomizerContractName, randomizer.address);

    const artblocksCoreFactory = await hre.ethers.getContractFactory(globals.artblocksCoreContractName);
    const artblocksCore = await artblocksCoreFactory.deploy("testToken", "TST", randomizer.address);
    await artblocksCore.deployed();
    console.log(`${globals.artblocksCoreContractName} deployed to: ${artblocksCore.address}`);
    globals.contractMap.set(globals.artblocksCoreContractName, artblocksCore.address);

    const artblocksMinterFilterV0Factory = await hre.ethers.getContractFactory(globals.artblocksMinterFilterV0ContractName);
    const artblocksMinterFilterV0 = await artblocksMinterFilterV0Factory.deploy(artblocksCore.address);
    await artblocksMinterFilterV0.deployed();
    console.log(`${globals.artblocksMinterFilterV0ContractName} deployed to: ${artblocksMinterFilterV0.address}`);
    globals.contractMap.set(globals.artblocksMinterFilterV0ContractName, artblocksMinterFilterV0.address);

    const setPriceMinterFactory = await hre.ethers.getContractFactory(globals.artblocksMinterSetPriceV0ContractName);
    const setPriceMinter = await setPriceMinterFactory.deploy(artblocksCore.address, artblocksMinterFilterV0.address);
    await setPriceMinter.deployed();
    console.log(`${globals.artblocksMinterSetPriceContractName} deployed to: ${setPriceMinter.address}`);
    globals.contractMap.set(globals.artblocksMinterSetPriceContractName, setPriceMinter.address);

    const dALinMinterFactory = await hre.ethers.getContractFactory(globals.artblocksMinterDALinV0ContractName);
    const dALinMinter = await dALinMinterFactory.deploy(artblocksCore.address, artblocksMinterFilterV0.address);
    await dALinMinter.deployed();
    console.log(`${globals.artblocksMinterDALinV0ContractName} deployed to: ${dALinMinter.address}`);
    globals.contractMap.set(globals.artblocksMinterDALinV0ContractName, dALinMinter.address);

    const dAExpMinterFactory = await hre.ethers.getContractFactory(globals.artblocksMinterDAExpV0ContractName);
    const dAExpMinter = await dAExpMinterFactory.deploy(artblocksCore.address, artblocksMinterFilterV0.address);
    await dAExpMinter.deployed();
    console.log(`${globals.artblocksMinterDAExpV0ContractName} deployed to: ${dAExpMinter.address}`);
    globals.contractMap.set(globals.artblocksMinterDAExpV0ContractName, dAExpMinter.address);
    
    await globals.verifyContractAddresses();
};