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


_logger = logging.getLogger(
    "aea.packages.elcollectooorr.contracts.artblocks_minter_filter.contract"
)


class ArtBlocksMinterFilterContract(Contract):
    """The scaffold contract class for a smart contract."""

    contract_id = PublicId.from_str("elcollectooorr/artblocks_minter_filter:0.1.0")

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
    def get_minter_for_project(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int,
    ) -> JSONLike:
        """
        Method to get the minter of a project.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the project id.
        :return: the minter  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        minter_address = "0x"
        has_minter = instance.functions.projectHasMinter(project_id).call()

        if has_minter:
            minter_address = instance.functions.getMinterForProject(project_id).call()

        return {
            "project_id": project_id,
            "minter_for_project": minter_address,
        }

    @classmethod
    def get_multiple_projects_minter(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        project_ids: Optional[List[int]] = None,
    ) -> JSONLike:
        """
        Get the minter of multiple projects.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_ids: the ids of the projects to get the details of.
        :return: the project minters.
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
                    cls.get_minter_for_project,
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
