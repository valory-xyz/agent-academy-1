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

"""This module contains the class to connect to a Token Settings contract."""
import logging
from typing import Any, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from web3.types import Nonce, TxParams, Wei


PUBLIC_ID = PublicId.from_str("elcollectooorr/token_settings:0.1.0")

_logger = logging.getLogger(
    f"aea.packages.{PUBLIC_ID.author}.contracts.{PUBLIC_ID.name}.contract"
)


class TokenSettingsContract(Contract):
    """The Fractional Token Settings contract."""

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
    def transfer_ownership(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        current_owner_address: str,
        new_owner_address: str,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Transfer the ownership of the Settings Contract.

        :param ledger_api: ledger API object.
        :param contract_address: the address of the contract to change the owner of.
        :param current_owner_address: current owner.
        :param new_owner_address: the new owner.
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max

        :return: the raw transaction.
        """
        eth_api = cast(EthereumApi, ledger_api)
        settings_contract = cls.get_instance(ledger_api, contract_address)

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
            tx_parameters.update(eth_api.try_get_gas_pricing())

        if gas is not None:
            tx_parameters["gas"] = Wei(gas)

        nonce = eth_api._try_get_transaction_count(  # pylint: disable=protected-access
            current_owner_address
        )
        tx_parameters["nonce"] = Nonce(nonce)

        if nonce is None:
            raise ValueError("No nonce returned.")  # pragma: nocover

        transaction_dict = settings_contract.functions.transferOwnership(
            new_owner_address
        ).build_transaction(tx_parameters)

        return transaction_dict

    @classmethod
    def set_fee_receiver(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        owner_address: str,
        new_receiver_address: str,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Change the fee receiver of the contract.

        :param ledger_api: ledger API object.
        :param contract_address: the address of the contract.
        :param new_receiver_address: the deployer address.
        :param owner_address: the owner of the contract
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max

        :return: the raw tx.
        """
        eth_api = cast(EthereumApi, ledger_api)
        settings_contract = cls.get_instance(ledger_api, contract_address)

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
            tx_parameters.update(eth_api.try_get_gas_pricing())

        if gas is not None:
            tx_parameters["gas"] = Wei(gas)

        nonce = eth_api._try_get_transaction_count(  # pylint: disable=protected-access
            owner_address
        )
        tx_parameters["nonce"] = Nonce(nonce)

        if nonce is None:
            raise ValueError("No nonce returned.")  # pragma: nocover

        raw_tx = settings_contract.functions.setFeeReceiver(
            new_receiver_address
        ).build_transaction(tx_parameters)

        return raw_tx

    @classmethod
    def verify_contract(
        cls,
        ledger_api: EthereumApi,
        contract_address: str,
        expected_owner_address: str,
    ) -> JSONLike:
        """
        Verify the contract's bytecode, owner and fee receiver

        :param ledger_api: the ledger API object
        :param contract_address: the contract address
        :param expected_owner_address: the expected owner and of the contract
        :return: the verified status
        """
        ledger_api = cast(EthereumApi, ledger_api)
        contract = cls.get_instance(ledger_api, contract_address)
        deployed_bytecode = ledger_api.api.eth.get_code(contract_address).hex()
        local_bytecode = cls.contract_interface["ethereum"]["deployedBytecode"]

        is_bytecode_ok = deployed_bytecode == local_bytecode
        is_owner_ok = expected_owner_address == contract.functions.owner().call()
        is_fee_receiver_ok = (
            expected_owner_address == contract.functions.feeReceiver().call()
        )

        return dict(
            bytecode=is_bytecode_ok,
            owner=is_owner_ok,
            fee_receiver=is_fee_receiver_ok,
        )
