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

"""This module contains the class to connect to a Fractional Basket contract."""
import logging
from typing import Any, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from web3.types import TxParams, Wei, Nonce

from packages.valory.contracts.basket_factory.contract import BasketFactoryContract

PUBLIC_ID = PublicId.from_str("valory/basket:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class BasketContract(Contract):
    """The Basket contract."""

    contract_id = PUBLIC_ID

    @classmethod
    def get_raw_transaction(cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any) -> Optional[JSONLike]:
        """Get raw message."""
        raise NotImplementedError

    @classmethod
    def get_raw_message(cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any) -> Optional[bytes]:
        """Get raw message."""
        raise NotImplementedError

    @classmethod
    def get_state(cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any) -> Optional[JSONLike]:
        """Get raw message."""
        raise NotImplementedError

    @classmethod
    def get_deploy_transaction(
            cls, ledger_api: LedgerApi, deployer_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Get deploy transaction.

        :param ledger_api: ledger API object.
        :param deployer_address: the deployer address.
        :param kwargs: the keyword arguments.

        :return: the raw tx
        """

        factory_address = kwargs.pop("basket_factory_address", None)
        gas = kwargs.pop("gas", None)
        gas_price = kwargs.pop("gas_price", None)
        max_fee_per_gas = kwargs.pop("max_fee_per_gas", None)
        max_priority_fee_per_gas = kwargs.pop("max_priority_fee_per_gas", None)

        raw_tx = BasketFactoryContract.create_basket(
            ledger_api,
            factory_address,
            deployer_address,
            gas,
            gas_price,
            max_fee_per_gas,
            max_priority_fee_per_gas,
        )

        return raw_tx

    @classmethod
    def verify_contract(
            cls, ledger_api: LedgerApi, contract_address: str
    ) -> JSONLike:
        """
        Verify the contract's bytecode

        :param ledger_api: the ledger API object
        :param contract_address: the contract address
        :return: the verified status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        deployed_bytecode = ledger_api.api.eth.get_code(contract_address).hex()
        local_bytecode = cls.contract_interface["ethereum"]["deployedBytecode"]
        verified = deployed_bytecode == local_bytecode
        return dict(verified=verified)

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
        :return: None
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
            cls,
            tx_parameters: TxParams,
            ledger_api: EthereumApi,
            sender_address: str
    ) -> None:
        """
        Handle gas nonce operations

        :param tx_parameters: the transaction params to update
        :param ledger_api: the ledger api to be used
        :param sender_address: the address to be used for finding nonce
        :return: None
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
    def approve(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            operator_address: str,
            token_id: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Gives permission to `operator_address` to transfer `tokenId` token to another account.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param operator_address: the address to set the approval status of
        :param token_id: the id of the token which should be approved.
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.approve(
            operator_address,
            token_id,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def set_approve_for_all(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            operator_address: str,
            is_approved: bool,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Set the approval status for the operator.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param operator_address: the address to set the approval status of
        :param is_approved: the address of the tx sender
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.setApprovalForAll(
            operator_address,
            is_approved,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def withdraw_erc721(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            token_address: str,
            token_id: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Withdraw an ERC721 token from the contract into the wallet of the sender.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param token_address: the address of the NFT getting withdrawn
        :param token_id: the ID of the NFT getting withdrawn
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.withdrawERC721(
            token_address,
            token_id,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def withdraw_erc721_unsafe(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            token_address: str,
            token_id: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Withdraw an ERC721 token from the contract into the wallet of the sender.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param token_address: the address of the NFT getting withdrawn
        :param token_id: the ID of the NFT getting withdrawn
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.withdrawERC721Unsafe(
            token_address,
            token_id,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def withdraw_eth(
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
        Withdraw ETH in the case a held NFT earned ETH (ie. euler beats).

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.withdrawETH().buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def withdraw_erc20(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            token_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Withdraw ERC20 in the case a held NFT earned ERC20.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender
        :param token_address: the address of the NFT getting withdrawn
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.withdrawERC20(
            token_address,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def transfer_from(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            new_owner_address: str,
            token_id: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Transfers `tokenId` token to `new_owner_address`
        WARNING: Usage of this method is discouraged, use `safe_transfer_from` whenever possible.

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender, should be the current owner
        :param new_owner_address: the address of the new owner
        :param token_id: the ID of the NFT getting transferred
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.transferFrom(
            sender_address,
            new_owner_address,
            token_id,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def safe_transfer_from(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            sender_address: str,
            new_owner_address: str,
            token_id: int,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Transfers `tokenId` token to `new_owner_address`

        :param ledger_api: EthereumApi object
        :param contract_address: the address of the token vault factory to be used
        :param sender_address: the address of the tx sender, should be the current owner
        :param new_owner_address: the address of the new owner
        :param token_id: the ID of the NFT getting transferred
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
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

        raw_tx = basket.functions.safeTransferFrom(
            sender_address,
            new_owner_address,
            token_id,
        ).buildTransaction(tx_parameters)

        return raw_tx

    @classmethod
    def get_balance_of(
            cls,
            ledger_api: EthereumApi,
            contract_address: str,
            owner_address: str,
    ) -> Optional[int]:
        """
        Returns the number of tokens in `owner_address`'s account.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param owner_address: the address to check the balance of
        :return: the balance of the owner
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        balance = basket.functions.owner(owner_address).call()

        return balance

    @classmethod
    def get_owner_of(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            token_id: int,
    ) -> Optional[str]:
        """
        Returns the owner's address of the `tokenId` token.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param token_id: the token to check the owner of
        :return: the owner of the token with id `token_id`
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        owner = basket.functions.ownerOf(token_id).call()

        return owner

    @classmethod
    def get_base_uri(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
    ) -> Optional[str]:
        """
        Get the address of the logic contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the baseURI
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        base_uri = basket.functions.baseURI().call()

        return base_uri

    @classmethod
    def get_approved_account(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            token_id: int,
    ) -> Optional[str]:
        """
        Returns the account approved for `tokenId` token.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param token_id: the id of the token to check the approved operator of.
        :return: address of this token's operator
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        operator = basket.functions.getApproved(token_id).call()

        return operator

    @classmethod
    def is_approved_for_all(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            owner_address: str,
            operator_address: str,
    ) -> Optional[bool]:
        """
        Returns if the `operator` is allowed to manage all the assets of `owner`.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param owner_address: the token owner's address
        :param operator_address: the operator's address
        :return: the approval status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        is_approved_for_all = basket.functions.isApprovedForAll(
            owner_address,
            operator_address,
        ).call()

        return is_approved_for_all

    @classmethod
    def get_total_supply(
            cls,
            ledger_api: EthereumApi,
            contract_address: str,
    ) -> Optional[int]:
        """
        Returns the total amount of tokens stored by the contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :return: the total number of tokens in the basket
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        total_amount = basket.functions.totalSupply().call()

        return total_amount

    @classmethod
    def get_token_of_owner_by_index(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            owner_address: str,
            index: int,
    ) -> Optional[int]:
        """
        Returns a token ID owned by `owner` at a given `index` of its token list.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param owner_address: the token owner's address
        :param index: the index of the token by owner
        :return: the token id
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        token_id = basket.functions.tokenOfOwnerByIndex(
            owner_address,
            index,
        ).call()

        return token_id

    @classmethod
    def get_token_by_index(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            index: int,
    ) -> Optional[int]:
        """
        Returns a token ID at a given `index` of all the tokens stored by the contract.

        :param ledger_api: the LedgerApi object
        :param contract_address: the contract address to target
        :param index: the index of the token by owner
        :return: the token id
        """
        ledger_api = cast(EthereumApi, ledger_api)
        basket = cls.get_instance(ledger_api, contract_address)
        token_id = basket.functions.tokenByIndex(index).call()

        return token_id