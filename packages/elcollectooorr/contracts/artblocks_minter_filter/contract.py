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

"""This module contains the scaffold contract definition."""
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi

from packages.elcollectooorr.contracts.multicall2.contract import Multicall2Contract


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
    def _batch_request(
            cls,
            ledger_api: LedgerApi,
            multicall_contract_address: str,
            calls: List[Tuple[Dict[str, Any], Callable]],
            batch_size: int,
    ) -> List[Any]:
        """Make batch requests to the Multicall contract."""
        responses = []
        num_calls = len(calls)
        for i in range(0, num_calls, batch_size):
            batch = calls[i:i + batch_size]
            _block_number, batch_responses = Multicall2Contract.aggregate_and_decode(ledger_api,
                                                                                     multicall_contract_address, batch)
            responses.extend(batch_responses)
        return responses

    @classmethod
    def get_multiple_projects_minter(  # pylint: disable=too-many-locals
            cls,
            ledger_api: LedgerApi,
            contract_address: str,
            multicall2_contract_address: str,
            project_ids: Optional[List[int]] = None,
    ) -> JSONLike:
        """
        Get the minter of multiple projects.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param multicall2_contract_address: the multicall2 contract address.
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

        instance = cls.get_instance(ledger_api, contract_address)

        has_minter_calls = []
        for project_id in project_ids:
            call = Multicall2Contract.encode_function_call(
                ledger_api,
                instance,
                fn_name="projectHasMinter",
                args=[project_id],
            )
            has_minter_calls.append(call)

        batch_size = 50
        results = {}
        has_minter_responses = cls._batch_request(ledger_api, multicall2_contract_address, has_minter_calls, batch_size)
        project_ids_with_minter = []
        for project_id, res_tuple in zip(project_ids, has_minter_responses):
            # decoding of responses will always be a tuple
            # we get the first (and only) element of the tuple
            has_minter = res_tuple[0]
            if has_minter:
                # this project has a minter, we need an additional call to get the minter address
                project_ids_with_minter.append(project_id)
            else:
                # the project doesn't have a minter, we add it to the results with 0x as the minter
                results[project_id] = {
                    "project_id": project_id,
                    "minter_for_project": "0x",
                }

        get_minter_for_project_calls = []
        for project_id in project_ids_with_minter:
            call = Multicall2Contract.encode_function_call(
                ledger_api,
                instance,
                "getMinterForProject",
                [project_id],
            )
            get_minter_for_project_calls.append(call)

        minter_for_project_responses = cls._batch_request(
            ledger_api,
            multicall2_contract_address,
            get_minter_for_project_calls,
            batch_size,
        )
        for project_id, res_tuple in zip(project_ids_with_minter, minter_for_project_responses):
            # decoding of responses will always be a tuple
            # we get the first (and only) element of the tuple
            minter_address = res_tuple[0]
            results[project_id] = {
                "project_id": project_id,
                "minter_for_project": minter_address,
            }
        return results  # type: ignore
