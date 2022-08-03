# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2022 Valory AG
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
# ------------------------------------------------------------------------------

"""This module contains the class to connect to a Token Vault contract."""
import logging
from typing import Any, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from web3.types import BlockIdentifier, Nonce, TxParams, Wei

from packages.elcollectooorr.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)


PUBLIC_ID = PublicId.from_str("elcollectooorr/token_vault:0.1.0")
TOKEN_VAULT_DEPLOYED_CODE = "0x6080604052600436106100225760003560e01c8063d7dfa0dd1461007557610029565b3661002957005b60007f000000000000000000000000d8058efe0198ae9dd7d563e1b4938dcbc86a1f81905060405136600082376000803683855af43d806000843e8160008114610071578184f35b8184fd5b34801561008157600080fd5b5061008a6100a0565b60405161009791906100d3565b60405180910390f35b7f000000000000000000000000d8058efe0198ae9dd7d563e1b4938dcbc86a1f8181565b6100cd816100ee565b82525050565b60006020820190506100e860008301846100c4565b92915050565b60006100f982610100565b9050919050565b600073ffffffffffffffffffffffffffffffffffffffff8216905091905056fea2646970667358221220dc1b8611c989c28d353f1703711deb09faf9e2c5a24cfef6bacf2bad3a3de59064736f6c63430008040033"  # nosec

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class TokenVaultContract(Contract):
    """The Fractional Token Vault contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_raw_transaction(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the subclass if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        raise NotImplementedError

    @classmethod
    def get_raw_message(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> bytes:
        """
        Handler method for the 'GET_RAW_MESSAGE' requests.

        Implement this method in the subclass if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        raise NotImplementedError

    @classmethod
    def get_state(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_STATE' requests.

        Implement this method in the subclass if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param kwargs: the keyword arguments.
        :return: the tx  # noqa: DAR202
        """
        raise NotImplementedError

    @classmethod
    def _handle_gas_ops(
        cls,
        tx_parameters: TxParams,
        ledger_api: EthereumApi,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> None:
        """
        Handle gas related operations

        :param tx_parameters: the transaction params to update
        :param ledger_api: the ledger api to be used
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: None # noqa: DAR202
        """

        if gas_price is not None:
            tx_parameters["gasPrice"] = Wei(gas_price)  # pragma: nocover

        if max_fee_per_gas is not None:
            tx_parameters["maxFeePerGas"] = Wei(max_fee_per_gas)  # pragma: nocover

        if max_priority_fee_per_gas is not None:
            tx_parameters["maxPriorityFeePerGas"] = Wei(  # pragma: nocover
                max_priority_fee_per_gas
            )

        if (
            gas_price is None
            and max_fee_per_gas is None
            and max_priority_fee_per_gas is None
        ):
            tx_parameters.update(ledger_api.try_get_gas_pricing())

        if gas is not None:
            tx_parameters["gas"] = Wei(gas)

    @classmethod
    def _handle_nonce_ops(
        cls, tx_parameters: TxParams, ledger_api: EthereumApi, sender_address: str
    ) -> None:
        """
        Handle gas nonce operations

        :param tx_parameters: the transaction params to update
        :param ledger_api: the ledger api to be used
        :param sender_address: the address to be used for finding nonce
        :return: None # noqa: DAR202
        """
        nonce = (
            ledger_api._try_get_transaction_count(  # pylint: disable=protected-access
                sender_address
            )
        )
        tx_parameters["nonce"] = Nonce(nonce)

        if nonce is None:
            raise ValueError("No nonce returned.")  # pragma: nocover

    @classmethod
    def get_deploy_transaction(  # pylint: disable=too-many-locals
        cls, ledger_api: LedgerApi, deployer_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Get deploy transaction.

        :param ledger_api: ledger API object.
        :param deployer_address: the deployer address.
        :param kwargs: the keyword arguments.

        :return: the raw tx
        """
        factory_address = kwargs.pop("token_vault_factory_address")
        name = kwargs.pop("name")
        symbol = kwargs.pop("symbol")
        token_address = kwargs.pop("token_address")
        token_id = kwargs.pop("token_id")
        token_supply = kwargs.pop("token_supply")
        list_price = kwargs.pop("list_price")
        fee = kwargs.pop("fee")
        gas = kwargs.pop("gas", None)
        gas_price = kwargs.pop("gas_price", None)
        max_fee_per_gas = kwargs.pop("max_fee_per_gas", None)
        max_priority_fee_per_gas = kwargs.pop("max_priority_fee_per_gas", None)

        raw_tx = TokenVaultFactoryContract.mint(
            ledger_api,
            factory_address,
            deployer_address,
            name,
            symbol,
            token_address,
            token_id,
            token_supply,
            list_price,
            fee,
            gas,
            gas_price,
            max_fee_per_gas,
            max_priority_fee_per_gas,
        )

        return raw_tx

    @classmethod
    def verify_contract(cls, ledger_api: LedgerApi, contract_address: str) -> JSONLike:
        """
        Verify the contract's bytecode

        :param ledger_api: the ledger API object
        :param contract_address: the contract address
        :return: the verified status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        deployed_bytecode = ledger_api.api.eth.get_code(contract_address).hex()
        # we cannot use cls.contract_interface["ethereum"]["deployedBytecode"] because the
        # contract is created via a proxy
        local_bytecode = TOKEN_VAULT_DEPLOYED_CODE
        verified = deployed_bytecode == local_bytecode

        return dict(verified=verified)

    @classmethod
    def kick_curator(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        sender_address: str,
        curator_address: str,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Allow governance to boot a bad actor curator.

        Note: This method should be called directly only if the agent is the Token Settings owner.
        To call it via the Safe Contract use `get_kick_curator_data`.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender, they should be the Token Settings owner
        :param curator_address: the address of the new curator
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        tx_parameters = TxParams()

        cls._handle_gas_ops(
            tx_parameters,
            ledger_api,
            gas,
            gas_price,
            max_fee_per_gas,
            max_priority_fee_per_gas,
        )
        cls._handle_nonce_ops(
            tx_parameters,
            ledger_api,
            sender_address,
        )

        raw_tx = token_vault_contract.functions.kickCurator(
            curator_address
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def transfer_erc20(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        sender_address: str,
        receiver_address: str,
        amount: int,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Transfer tokens.

        Note: This method should be called directly only if the agent has balance.
        To call it via the Safe Contract use `get_transfer_erc20_data`.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param receiver_address: the address of the receiver
        :param amount: the user sends the address
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        tx_parameters = TxParams()

        cls._handle_gas_ops(
            tx_parameters,
            ledger_api,
            gas,
            gas_price,
            max_fee_per_gas,
            max_priority_fee_per_gas,
        )
        cls._handle_nonce_ops(
            tx_parameters,
            ledger_api,
            sender_address,
        )

        raw_tx = token_vault_contract.functions.transfer(
            receiver_address, amount
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def get_transfer_erc20_data(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        receiver_address: str,
        amount: int,
    ) -> JSONLike:
        """
        Transfer tokens.

        Note: The tx submitter of this function must be the Token Settings owner.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :param receiver_address: the receiver
        :param amount: the amount
        :return: the raw transaction
        """

        instance = cls.get_instance(ledger_api, contract_address)
        receiver_address = ledger_api.api.toChecksumAddress(receiver_address)
        data = instance.encodeABI(fn_name="transfer", args=[receiver_address, amount])

        return {"data": data}

    @classmethod
    def get_kick_curator_data(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        curator_address: str,
    ) -> JSONLike:
        """
        Allow governance to remove bad reserve prices.

        Note: The tx submitter of this function must be the Token Settings owner.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :param curator_address: the address of the new curator
        :return: the raw transaction
        """

        instance = cls.get_instance(ledger_api, contract_address)
        data = instance.encodeABI(fn_name="kickCurator", args=[curator_address])

        return {"data": data}

    @classmethod
    def get_curator(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
    ) -> Optional[str]:
        """
        Get the curator of the contract.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :return: the curator's address
        """

        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        curator_address = token_vault_contract.functions.curator().call()

        return curator_address

    @classmethod
    def get_balance(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        address: str,
    ) -> JSONLike:
        """
        Get the curator of the contract.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :param address: the address to check the balance of
        :return: the curator's address
        """

        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        balance = token_vault_contract.functions.balanceOf(address).call()

        return {"balance": balance}

    @classmethod
    def get_auction_state(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
    ) -> JSONLike:
        """
        Get the curator of the contract.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :return: the auction state
        """

        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        state = token_vault_contract.functions.auctionState().call()

        return {"state": state}

    @classmethod
    def get_all_erc20_transfers(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        from_address: str,
        from_block: BlockIdentifier = "earliest",
        to_block: BlockIdentifier = "latest",
    ) -> JSONLike:
        """
        Get all ERC20 transfers from a given address.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :param from_address: the address transferring the tokens.
        :param from_block: from which block to search for events
        :param to_block: to which block to search for events
        :return: the ERC20 transfers
        """
        ledger_api = cast(EthereumApi, ledger_api)
        factory_contract = cls.get_instance(ledger_api, contract_address)
        entries = factory_contract.events.Transfer.createFilter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters={"from": from_address},
        ).get_all_entries()

        return dict(
            payouts=list(
                map(
                    lambda entry: dict(
                        to=entry.args["to"],
                        value=entry.args["value"],
                    ),
                    entries,
                )
            )
        )
