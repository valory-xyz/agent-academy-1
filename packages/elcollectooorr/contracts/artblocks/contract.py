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
from typing import Any, List, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea.exceptions import enforce
from aea_ledger_ethereum import EthereumApi
from web3.types import BlockIdentifier

from packages.elcollectooorr.contracts.multicall2.contract import Multicall2Contract


_logger = logging.getLogger("aea.packages.elcollectooorr.contracts.artblocks.contract")


class ArtBlocksContract(Contract):
    """The scaffold contract class for a smart contract."""

    contract_id = PublicId.from_str("elcollectooorr/artblocks:0.1.0")

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
    def get_dynamic_details(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int = 0,
    ) -> JSONLike:
        """
        Handler method for the 'get_dynamic_details' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the starting id of projects from which to work backwards.
        :return: the tx  # noqa: DAR202
        """
        enforce(project_id > 0, "project_id must be greater than 0")

        instance = cls.get_instance(ledger_api, contract_address)
        project_info = instance.functions.projectTokenInfo(project_id).call()

        result = {
            "price_per_token_in_wei": project_info[1],
            "invocations": project_info[2],
            "max_invocations": project_info[3],
        }

        return result

    @classmethod
    def get_next_project_id(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
    ) -> JSONLike:
        """
        Handler method for the 'get_next_project_id' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :return: the next project id  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        project_id = instance.functions.nextProjectId().call()

        result = {
            "next_project_id": project_id,
        }

        return result

    @classmethod
    def get_multiple_projects_info(  # pylint: disable=too-many-locals
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        multicall2_contract_address: str,
        project_ids: Optional[List[int]] = None,
        last_processed_project: Optional[int] = None,
    ) -> JSONLike:
        """
        Get all active projects in a contract.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param multicall2_contract_address: the multicall2 contract address.
        :param project_ids: the ids of the projects to get the data for, if None all projects are called.
        :param last_processed_project: the project that was evaluated most recently.
        :return: the active projects
        """
        instance = cls.get_instance(ledger_api, contract_address)
        next_project_id = cast(
            int,
            cls.get_next_project_id(ledger_api, contract_address)["next_project_id"],
        )

        if project_ids is None or last_processed_project is None:
            project_ids = list(range(1, next_project_id))
            last_processed_project = next_project_id

        if (last_processed_project + 1) != next_project_id:
            # new projects were added, we need to check for those
            project_ids += list(range(last_processed_project + 1, next_project_id))

        project_token_info_calls = []
        project_script_info_calls = []
        for project_id in project_ids:
            project_token_info_call = Multicall2Contract.encode_function_call(
                ledger_api, instance,
                fn_name="projectTokenInfo",
                args=[project_id],
            )
            project_script_info_call = Multicall2Contract.encode_function_call(
                ledger_api, instance, fn_name="projectScriptInfo", args=[project_id]
            )
            project_token_info_calls.append(project_token_info_call)
            project_script_info_calls.append(project_script_info_call)

        num_calls = len(project_ids)
        project_token_info_responses = []
        project_script_info_responses = []
        batch_size = 50
        for batch in range(0, num_calls, batch_size):
            project_token_info_calls_batch = project_token_info_calls[batch:batch + batch_size]
            project_script_info_calls_batch = project_script_info_calls[batch:batch + batch_size]
            _block_number, project_token_info_batch_responses = Multicall2Contract.aggregate_and_decode(
                ledger_api,
                multicall2_contract_address,
                project_token_info_calls_batch,
            )
            _block_number, project_script_info_batch_responses = Multicall2Contract.aggregate_and_decode(
                ledger_api,
                multicall2_contract_address,
                project_script_info_calls_batch,
            )
            project_token_info_responses.extend(project_token_info_batch_responses)
            project_script_info_responses.extend(project_script_info_batch_responses)

        results = []
        for project_id, project_info, script_info in zip(project_ids, project_token_info_responses, project_script_info_responses):
            price_per_token_in_wei = project_info[1]
            invocations = project_info[2]
            max_invocations = project_info[3]
            is_active = project_info[4]
            is_paused = script_info[5]
            result = {
                "project_id": project_id,
                "price_per_token_in_wei": price_per_token_in_wei,
                "invocations": invocations,
                "max_invocations": max_invocations,
                "is_active": is_active and not is_paused,
            }
            results.append(result)

        return {"results": results}

    @classmethod
    def get_project_info(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        project_id: int = None,
    ) -> JSONLike:
        """
        Handler method for the 'get_active_project' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param project_id: the id of the project to get the info of.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        project_info = instance.functions.projectTokenInfo(project_id).call()
        script_info = instance.functions.projectScriptInfo(project_id).call()
        price_per_token_in_wei = project_info[1]
        invocations = project_info[2]
        max_invocations = project_info[3]
        is_active = project_info[4]
        is_paused = script_info[5]

        result = {
            "project_id": project_id,
            "price_per_token_in_wei": price_per_token_in_wei,
            "invocations": invocations,
            "max_invocations": max_invocations,
            "is_active": is_active and not is_paused,
        }
        return result

    @classmethod
    def process_purchase_receipt(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        tx_hash: str,
    ) -> Optional[JSONLike]:
        """
        Get the Mint event out of the purchase receipt.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param tx_hash: the tx_hash to be processed.
        :return: the token_id of the purchase
        """
        ledger_api = cast(EthereumApi, ledger_api)
        contract = cls.get_instance(ledger_api, contract_address)
        receipt = ledger_api.api.eth.getTransactionReceipt(tx_hash)
        logs = contract.events.Mint().processReceipt(receipt)

        if len(logs) == 0:
            _logger.error(f"No 'Mint' events were emitted in the tx={tx_hash}")
            return None

        if len(logs) != 1:
            _logger.warning(
                f"{len(logs)} 'Mint' events were emitted in the tx={tx_hash}"
            )

        args = logs[-1]["args"]  # in case of multiple logs, take the last

        response = {
            "token_id": args["_tokenId"],
        }

        return response

    @classmethod
    def safe_transfer_from_data(
        cls,  # pylint: disable=unused-argument
        ledger_api: LedgerApi,
        contract_address: str,
        from_address: str,
        to_address: str,
        token_id: int,
    ) -> JSONLike:
        """
        Get `safeTransferFrom` encoded data.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param from_address: origin address.
        :param to_address: destination address.
        :param token_id: token to transfer.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        from_address = ledger_api.api.toChecksumAddress(from_address)
        to_address = ledger_api.api.toChecksumAddress(to_address)
        data = instance.encodeABI(
            fn_name="safeTransferFrom",
            args=[
                from_address,
                to_address,
                token_id,
            ],
        )

        return {"data": data}

    @classmethod
    def get_mints(
        cls,
        ledger_api: LedgerApi,
        contract_address: str,
        minted_to_address: str,
        from_block: BlockIdentifier = "earliest",
        to_block: BlockIdentifier = "latest",
    ) -> JSONLike:
        """
        Get all deployed minted tokens from the minted_to_address.

        :param ledger_api: LedgerApi object
        :param contract_address: the address of the artblocks contract
        :param minted_to_address: the address that the tokens have been minted to
        :param from_block: from which block to search for events
        :param to_block: to which block to search for events
        :return: the minted tokens & projects
        """
        ledger_api = cast(EthereumApi, ledger_api)
        artblocks_contract = cls.get_instance(ledger_api, contract_address)
        entries = artblocks_contract.events.Mint.createFilter(
            fromBlock=from_block,
            toBlock=to_block,
            argument_filters=dict(_to=minted_to_address),
        ).get_all_entries()

        return dict(
            mints=list(
                map(
                    lambda entry: dict(
                        token_id=entry.args["_tokenId"],
                        project_id=entry.args["_projectId"],
                    ),
                    entries,
                )
            )
        )
