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
import logging
from typing import Any, Optional, cast

from aea.common import JSONLike
from aea.configurations.base import PublicId
from aea.contracts.base import Contract
from aea.crypto.base import LedgerApi
from aea.exceptions import enforce
from aea_ledger_ethereum import EthereumApi


_logger = logging.getLogger(
    f"aea.packages.valory.contracts.artblocks.contract"
)


class ArtBlocksContract(Contract):
    """The scaffold contract class for a smart contract."""

    contract_id = PublicId.from_str("valory/artblocks:0.1.0")

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
    def get_active_project(
            cls,  # pylint: disable=unused-argument
            ledger_api: LedgerApi,
            contract_address: str,
            starting_id: Optional[int] = None,
    ) -> JSONLike:
        """
        Handler method for the 'get_active_project' requests.

        Implement this method in the sub class if you want
        to handle the contract requests manually.

        :param ledger_api: the ledger apis.
        :param contract_address: the contract address.
        :param starting_id: the starting id of projects from which to work backwards.
        :return: the tx  # noqa: DAR202
        """
        instance = cls.get_instance(ledger_api, contract_address)
        if starting_id is None:
            next_project_id = instance.functions.nextProjectId().call()
            project_id = next_project_id - 1
        else:
            project_id = starting_id - 1
        while project_id > 0:
            project_info = instance.functions.projectTokenInfo(project_id).call()
            # check if active
            if project_info[4]:
                script_info = instance.functions.projectScriptInfo(project_id).call()
                # check if paused
                if not script_info[5]:
                    break
            project_id -= 1
        if project_id == 0:
            return {"project_id": None}
        project_details = instance.functions.projectDetails(project_id).call()
        # project_script = instance.functions.projectScriptByIndex(
        #     project_id, script_info[1] - 1
        # ).call()

        result = {
            "artist_address": project_info[0],
            "price_per_token_in_wei": project_info[1],
            "project_id": project_id,
            "project_name": project_details[0],
            "artist": project_details[1],
            "description": project_details[2],
            "website": project_details[3],
            # "script": project_script,
            "invocations": project_info[2],
            "max_invocations": project_info[3],
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
            _logger.warning(f"{len(logs)} 'Mint' events were emitted in the tx={tx_hash}")

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
        :param project_id: the project id.
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
            ]
        )

        return {"data": data}