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
from typing import Any, Optional, List, cast
from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi

_logger = logging.getLogger(
    f"aea.packages.valory.contracts.artblocks_periphery.contract"
)


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
        is_mintable = instance.functions.contractFilterProject(project_id).call()

        return {
            "project_id": project_id,
            "is_mintable": is_mintable,
        }

    @classmethod
    def are_projects_mintable(
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            project_ids: Optional[List[int]] = None,
    ) -> JSONLike:
        """
        Check if the projects are mintable via contracts.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_ids: the ids of the projects to check whether they are mintable.
        :return: the active projects
        """
        if len(project_ids) == 0:
            _logger.warning("An empty list of projects was provided. Returning an empty array.")

            return {
                "results": []
            }

        num_threads = math.ceil(len(project_ids) / 30)  # 30 projects per thread

        with concurrent.futures.ThreadPoolExecutor(num_threads) as pool:
            loop = asyncio.new_event_loop()
            tasks = []

            for project_id in project_ids:
                task = loop.run_in_executor(pool, cls.is_project_mintable, ledger_api, contract_address, project_id)
                tasks.append(task)

            list_of_results = cast(List[JSONLike], loop.run_until_complete(asyncio.gather(*tasks)))
            results = {r["project_id"]: r["is_mintable"] for r in list_of_results}

            loop.close()

        return results
