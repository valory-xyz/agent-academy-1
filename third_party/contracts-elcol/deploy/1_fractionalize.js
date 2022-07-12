const globals = require("../globals/globals.js");

module.exports = async (hre) => {
    // Get the signers (default, pre-funded accounts)
    const settingsFactory = await hre.ethers.getContractFactory(globals.settingsContractName);
    const settings = await settingsFactory.deploy();
    await settings.deployed();
    console.log(`${globals.settingsContractName} deployed to: ${settings.address}`);
    globals.contractMap.set(globals.settingsContractName, settings.address);

    const vaultFactoryFactory = await hre.ethers.getContractFactory(globals.erc721VaultFactoryContractName);
    const vaultFactory = await vaultFactoryFactory.deploy(settings.address);
    await vaultFactory.deployed();
    console.log(`${globals.erc721VaultFactoryContractName} deployed to: ${vaultFactory.address}`);
    globals.contractMap.set(globals.erc721VaultFactoryContractName, vaultFactory.address);

    const basketFactoryFactory = await hre.ethers.getContractFactory(globals.basketFactoryContractName);
    const basketFactory = await basketFactoryFactory.deploy();
    await basketFactory.deployed();
    console.log(`${globals.basketFactoryContractName} deployed to: ${basketFactory.address}`);
    globals.contractMap.set(globals.basketFactoryContractName, basketFactory.address);

    await globals.verifyContractAddresses();
};