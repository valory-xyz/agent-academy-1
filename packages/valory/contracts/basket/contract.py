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

        :return: the transaction params
        """

        factory_address = kwargs.pop("basket_factory_address", None)
        gas = kwargs.pop("gas", None)
        gas_price = kwargs.pop("gas_price", None)
        max_fee_per_gas = kwargs.pop("max_fee_per_gas", None)
        max_priority_fee_per_gas = kwargs.pop("max_priority_fee_per_gas", None)

        tx_params = BasketFactoryContract.create_basket(
            ledger_api,
            factory_address,
            deployer_address,
            gas,
            gas_price,
            max_fee_per_gas,
            max_priority_fee_per_gas,
        )

        return tx_params

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
