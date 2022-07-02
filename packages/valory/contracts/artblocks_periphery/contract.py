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

"""This module contains the scaffold contract definition."""
import asyncio
import concurrent.futures
import logging
import math
from typing import Any, List, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea_ledger_ethereum import EthereumApi
from web3.types import Nonce, TxParams, Wei


_logger = logging.getLogger(
    "aea.packages.valory.contracts.artblocks_periphery.contract"
)
SUPPORTED_MINTER_TYPES = [
    "MinterSetPriceV0",
    "MinterSetPriceV1",
    "MinterDALinV0",
    "MinterDALinV1",
    "MinterDAExpV0",
    "MinterDAExpV1",
]


class ArtBlocksPeripheryContract(Contract):
    """The scaffold contract class for a smart contract."""

    contract_id = PublicId.from_str("valory/artblocks_periphery:0.1.0")

    @classmethod
    def get_raw_transaction(
        cls, ledger_api: LedgerApi, contract_address: str, **kwargs: Any
    ) -> JSONLike:
        """
        Handler method for the 'GET_RAW_TRANSACTION' requests.

        Implement this method in the sub class if you want
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

        Implement this method in the sub class if you want
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

        Implement this method in the sub class if you want
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
    def purchase_to(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
        sender_address: str,
        to_address: str,
        value: int,
        gas: Optional[int] = None,
        gas_price: Optional[int] = None,
        max_fee_per_gas: Optional[int] = None,
        max_priority_fee_per_gas: Optional[int] = None,
    ) -> JSONLike:
        """
        Handler method for the 'purchase_to' requests.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of artblocks periphery contract
        :param project_id: the project to purchase
        :param sender_address: the address of the tx sender
        :param to_address: the address of the receiver of the token
        :param value: the value in eth
        :param gas: Gas
        :param gas_price: Gas Price
        :param max_fee_per_gas: max
        :param max_priority_fee_per_gas: max
        :return: the raw transaction
        """
        ledger_api = cast(EthereumApi, ledger_api)
        contract = cls.get_instance(ledger_api, contract_address)
        tx_parameters = TxParams()
        tx_parameters["value"] = Wei(value)

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

        raw_tx = contract.functions.purchaseTo(to_address, project_id).buildTransaction(
            tx_parameters
        )

        return raw_tx

    @classmethod
    def purchase_data(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
    ) -> JSONLike:
        """
        Handler method for the 'get_active_project' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the project id.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        data = instance.encodeABI(fn_name="purchase", args=[project_id])
        return {"data": data}

    @classmethod
    def is_project_mintable(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
    ) -> JSONLike:
        """
        Method to check whether a project is mintable via a contract.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the project id.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        minter_type = instance.functions.minterType().call()

        if minter_type not in SUPPORTED_MINTER_TYPES:
            # unknown minter
            _logger.warning(
                "Minter of type {minter_type} deployed at address {contract_address} is not supported."
            )
            return {
                "project_id": project_id,
                "is_mintable_via_contract": False,
            }

        if minter_type[-2:] == "V1":
            # V1 minters are always contract mintable
            return {
                "project_id": project_id,
                "is_mintable_via_contract": True,
            }

        is_mintable = instance.functions.contractMintable(project_id).call()

        return {
            "project_id": project_id,
            "is_mintable_via_contract": is_mintable,
        }

    @classmethod
    def get_price_info(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
    ) -> JSONLike:
        """
        Method to check whether a project's price is set in the contract.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the project id.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        price_info = instance.functions.getPriceInfo(project_id).call()

        return {
            "project_id": project_id,
            "is_price_configured": price_info[0],
            "price_per_token_in_wei": price_info[1],
            "currency_symbol": price_info[2],
            "currency_address": price_info[3],
        }

    @classmethod
    def get_project_details(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
    ) -> JSONLike:
        """
        Get project details.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the id of the project to get the data for.
        :return: the project details
        """
        price_info = cls.get_price_info(ledger_api, contract_address, project_id)
        is_project_mintable = cls.is_project_mintable(
            ledger_api, contract_address, project_id
        )

        return {
            **price_info,
            **is_project_mintable,
        }

    @classmethod
    def get_multiple_project_details(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        project_ids: Optional[List[int]] = None,
    ) -> JSONLike:
        """
        Get project details.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_ids: the ids of the projects to get the details of.
        :return: the active projects
        """
        if project_ids is None:
            _logger.warning("No projects were provided. Returning an empty object.")

            return {}

        project_ids = cast(List[int], project_ids)

        if len(project_ids) == 0:
            _logger.warning(
                "An empty list of projects was provided. Returning an empty object."
            )

            return {}

        num_threads = math.ceil(len(project_ids) / 30)  # 30 projects per thread

        with concurrent.futures.ThreadPoolExecutor(num_threads) as pool:
            loop = asyncio.new_event_loop()
            tasks = []

            for project_id in project_ids:
                task = loop.run_in_executor(
                    pool,
                    cls.get_project_details,
                    ledger_api,
                    contract_address,
                    project_id,
                )
                tasks.append(task)

            list_of_results = cast(
                List[JSONLike], loop.run_until_complete(asyncio.gather(*tasks))
            )
            results = {p["project_id"]: p for p in list_of_results}

            loop.close()

        return results  # type: ignore
