# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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
# pylint: disable=consider-iterating-dictionary
"""This module contains the class to connect to an ERC721 Token Vault Factory contract."""
import logging
from typing import Any, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from web3.types import BlockIdentifier, Nonce, TxParams, Wei


PUBLIC_ID = PublicId.from_str("elcollectooorr/token_vault_factory:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class TokenVaultFactoryContract(Contract):
    """The Fractional Token Vault Factory contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_deploy_transaction(
            cls, ledger_api: LedgerApi, deployer_address: str, **kwargs: Any
    ) -> Optional[JSONLike]:
        """
        Get deploy transaction.

        :param ledger_api: ledger API object.
        :param deployer_address: the deployer address.
        :param kwargs: the keyword arguments.
        :return: an optional JSON-like object.
        """
        if "_settings" not in kwargs.keys():
            _logger.error("'_settings' is required to construct ")
        return super().get_deploy_transaction(ledger_api, deployer_address, **kwargs)

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
    def verify_contract(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            settings_address: str,
    ) -> JSONLike:
        """
        Verify the contract's bytecode

        :param ledger_api: the ledger API object
        :param contract_address: the contract address
        :param settings_address: the settings contract address
        :return: the verified status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        contract_address = ledger_api.api.to_checksum_address(contract_address)
        deployed_bytecode = cls._process_deployed_bytecode(
            ledger_api.api.eth.get_code(contract_address).hex(),
        )
        local_bytecode = cls._process_local_bytecode(
            cls.contract_interface["ethereum"]["deployedBytecode"], settings_address
        )

        verified = deployed_bytecode == local_bytecode

        return dict(verified=verified)

    @classmethod
    def _process_deployed_bytecode(cls, bytecode: str) -> str:
        """
        Remove the logic address from the deployed bytecode.

        :param bytecode: the bytecode
        :return: the processed bytecode
        """

        parts = [
            bytecode[:3016],
            "0" * 64,  # zero address (padded)
            bytecode[3080:3890],
            "0" * 64,  # zero address (padded)
            bytecode[3954:],
        ]

        return "".join(parts).lower()

    @classmethod
    def _process_local_bytecode(cls, bytecode: str, settings_address: str) -> str:
        """
        Add encoded settings address to local bytecode.

        :param bytecode: the bytecode
        :param settings_address: the settings contract address
        :return: the processed bytecode
        """
        parts = [
            bytecode[:3962],
            "0" * 24,
            settings_address[2:],  # padded settings address
            bytecode[4026:],
        ]

        return "".join(parts).lower()

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
    def mint(  # pylint: disable=too-many-locals
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            name: str,
            symbol: str,
            token_address: str,
            token_id: int,
            token_supply: int,
            list_price: int,
            fee: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Mint a new vault.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param name: name of the vault
        :param symbol: symbol of the vault
        :param token_address: ERC721 address of the token to fractionalize
        :param token_id: the ID of the token (ERC721)
        :param token_supply: the initial number of fractions
        :param list_price: initial price of the NFT
        :param fee: curator fee on creation
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

        raw_tx = token_vault_contract.functions.mint(
            name,
            symbol,
            token_address,
            token_id,
            token_supply,
            list_price,
            fee,
        ).build_transaction(tx_parameters)

        return raw_tx

    @classmethod
    def pause(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Pause the factory.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
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

        raw_tx = token_vault_contract.functions.pause().build_transaction(tx_parameters)

        return raw_tx

    @classmethod
    def renounce_ownership(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Renounce ownership of the factory.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
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

        raw_tx = token_vault_contract.functions.renounceOwnership().build_transaction(
            tx_parameters
        )

        return raw_tx

    @classmethod
    def transfer_ownership(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            new_owner_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Renounce ownership of the factory.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param new_owner_address: the address of the new owner
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

        raw_tx = token_vault_contract.functions.transferOwnership(
            new_owner_address
        ).build_transaction(tx_parameters)

        return raw_tx

    @classmethod
    def unpause(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Unpause the factory.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
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

        raw_tx = token_vault_contract.functions.unpause().build_transaction(
            tx_parameters
        )

        return raw_tx

    @classmethod
    def get_logic(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[str]:
        """
        Get the address of the logic contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the address of the logic contract
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        logic_address = token_vault_contract.functions.logic().call()

        return logic_address

    @classmethod
    def is_paused(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[bool]:
        """
        Get the address of the logic contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: paused status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        is_paused = token_vault_contract.functions.paused().call()

        return is_paused

    @classmethod
    def get_owner(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[str]:
        """
        Get the address of the logic contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the owner of the factory
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        contract_owner = token_vault_contract.functions.owner().call()

        return contract_owner

    @classmethod
    def get_settings_address(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[str]:
        """
        Get the address of the settings contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the address of the settings
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        settings = token_vault_contract.functions.settings().call()

        return settings

    @classmethod
    def get_vault_count(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[int]:
        """
        Get the number of vaults.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the number of ERC721 vaults
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        vault_count = token_vault_contract.functions.vaultCount().call()

        return vault_count

    @classmethod
    def get_vault(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            index: int,
    ) -> Optional[str]:
        """
        Get the address of the vault at the given index.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param index: the index of the vault
        :return: the address of the vault
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        vault_address = token_vault_contract.functions.vaults(index).call()

        return vault_address

    @classmethod
    def mint_abi(  # pylint: disable=too-many-locals
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            name: str,
            symbol: str,
            token_address: str,
            token_id: int,
            token_supply: int,
            list_price: int,
            fee: int,
    ) -> JSONLike:
        """
        Mint a new vault.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault factory to be used
        :param name: name of the vault
        :param symbol: symbol of the vault
        :param token_address: ERC721 address of the token to fractionalize
        :param token_id: the ID of the token (ERC721)
        :param token_supply: the initial number of fractions
        :param list_price: initial price of the NFT
        :param fee: curator fee on creation
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        token_vault_contract = cls.get_instance(ledger_api, contract_address)
        data = token_vault_contract.encodeABI(
            fn_name="mint",
            args=[name, symbol, token_address, token_id, token_supply, list_price, fee],
        )

        return {"data": data}

    @classmethod
    def get_vault_address(
            cls, ledger_api: LedgerApi, contract_address: str, tx_hash: str
    ) -> Optional[JSONLike]:
        """
        Get the basket address and its creator from the events emitted by the "createBasket" transaction.

        :param ledger_api: the ledger API object
        :param contract_address: the address of the factory contract
        :param tx_hash: tx hash of "createBasket"
        :return: basket contract address and the address of the creator
        """
        ledger_api = cast(EthereumApi, ledger_api)
        contract_address = ledger_api.api.to_checksum_address(contract_address)
        contract = cls.get_instance(ledger_api, contract_address)
        receipt = ledger_api.api.eth.get_transaction_receipt(tx_hash)  # type: ignore
        logs = contract.events.Mint().process_receipt(receipt)

        if len(logs) == 0:
            _logger.error(f"No 'Mint' events were emitted in the tx={tx_hash}")
            return None

        args = logs[-1]["args"]  # in case of multiple logs, take the last

        response = {
            "vault_address": args["vault"],
        }

        return response

    @classmethod
    def get_deployed_vaults(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            token_address: str,
            from_block: BlockIdentifier = "earliest",
            to_block: BlockIdentifier = "latest",
    ) -> JSONLike:
        """
        Get created vaults from the deployer_address.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the token vault to be used
        :param token_address: the address of the nft tied to the vault.
        :param from_block: from which block to search for events
        :param to_block: to which block to search for events
        :return: the curator's address
        """
        ledger_api = cast(EthereumApi, ledger_api)
        factory_contract = cls.get_instance(ledger_api, contract_address)
        entries = factory_contract.events.Mint.createFilter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters=dict(token=token_address),
        ).get_all_entries()

        return dict(
            vaults=list(
                map(
                    lambda entry: entry.args["vault"],
                    entries,
                )
            )
        )
