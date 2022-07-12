const globals = require("../globals/globals.js");

module.exports = async () => {
    // Deployments are done in alphabetical order (by file name). That's the reason for the n_ in every file name.
    // The deployment addresses seem to be derived from the contract file.

    // Deploy all the contracts
    for (const contractName of globals.contractNameList) {
        const contract = await globals.deployContract(contractName);
        console.log("Contract", contractName, "deployed to:", contract.address);
        globals.contractMap.set(contractName, contract.address);
    }

    await globals.verifyContractAddresses();
};