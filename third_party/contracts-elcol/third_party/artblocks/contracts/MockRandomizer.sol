pragma solidity ^0.8.0;

/**
 * Contract to mock the behaviour of a randomizer contract.
 */
contract MockRandomizer {
    function returnValue() external view returns (bytes32) {
        return 0x9abd19d60c3a8ffe7402a2faaf3fcfc00b9ba9bcf6ed1240d51bf5c2677e8239;
    }
}
