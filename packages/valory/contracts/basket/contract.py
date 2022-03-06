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
            cls, ledger_api: EthereumApi, contract_address: str
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
    def set_approve_for_all(
            cls,
            ledger_api: EthereumApi,
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
