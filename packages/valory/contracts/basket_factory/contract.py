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

"""This module contains the class to connect to a Fractional Basket Factory contract."""
import binascii
import logging
import secrets
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from eth_typing import ChecksumAddress, HexAddress, HexStr
from hexbytes import HexBytes
from packaging.version import Version
from py_eth_sig_utils.eip712 import encode_typed_data
from requests import HTTPError
from web3.exceptions import SolidityError, TransactionNotFound
from web3.types import Nonce, TxData, TxParams, Wei

from packages.valory.contracts.gnosis_safe_proxy_factory.contract import (
    GnosisSafeProxyFactoryContract,
)

PUBLIC_ID = PublicId.from_str("valory/basket_factory:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class BasketFactoryContract(Contract):
    """The Basket Factory contract."""

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
    ) -> Optional[JSONLike]:
        """
        Get deploy transaction.

        :param ledger_api: ledger API object.
        :param deployer_address: the deployer address.
        :param kwargs: the keyword arguments.
        :return: an optional JSON-like object.
        """
        return super().get_deploy_transaction(ledger_api, deployer_address, **kwargs)

    @classmethod
    def create_basket(
            cls, ledger_api: LedgerApi,
            factory_contract_address: str,
            deployer_address: str,
            gas: Optional[int] = None,
            gas_price: Optional[int] = None,
            max_fee_per_gas: Optional[int] = None,
            max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Builds and returns the tx to create a basket

        :param ledger_api: ledger API object.
        :param factory_contract_address: Address of the Basket Factory Contract
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the
        """

        ledger_api = cast(EthereumApi, ledger_api)
        factory_contract = cls.get_instance(ledger_api, factory_contract_address)
        tx_parameters = TxParams()

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

        nonce = (
            ledger_api._try_get_transaction_count(  # pylint: disable=protected-access
                deployer_address
            )
        )
        tx_parameters["nonce"] = Nonce(nonce)

        if nonce is None:
            raise ValueError("No nonce returned.")  # pragma: nocover

        tx_response = factory_contract.functions.createBasket().buildTransaction(tx_parameters)

        return tx_response

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
    def get_basket_address(
            cls,
            ledger_api: LedgerApi,
            factory_contract: str,
            tx_hash: str
    ) -> Optional[JSONLike]:
        """
        Get the basket address and its creator from the events emitted by the "createBasket" transaction.

        :param ledger_api: the ledger API object
        :param factory_contract: the address of the factory contract
        :param tx_hash: tx hash of "createBasket"
        :return: basket contract address and the address of the creator
        """

        factory_contract = cls.get_instance(ledger_api, factory_contract)
        receipt = ledger_api.api.eth.getTransactionReceipt(tx_hash)
        logs = factory_contract.events.NewBasket().processReceipt(receipt)

        if len(logs) == 0:
            _logger.error(f"No 'NewBasket' events were emitted in the tx={tx_hash}")
            return None

        args = logs[-1]["args"]  # in case of multiple logs, take the last

        response = {
            "basket_address": args["_address"],
            "creator_address": args["_creator"],
        }

        return response