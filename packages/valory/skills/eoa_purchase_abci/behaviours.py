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

"""This module contains the data classes for the safe deployment ABCI application."""
import json
from typing import Dict, Generator, List, Optional, Set, Type, cast

from aea.exceptions import AEAEnforceError, enforce

from packages.valory.contracts.artblocks.contract import ArtBlocksContract
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviour_utils import BaseState
from packages.valory.skills.abstract_round_abci.behaviours import AbstractRoundBehaviour
from packages.valory.skills.abstract_round_abci.common import (
    RandomnessBehaviour,
    SelectKeeperBehaviour,
)
from packages.valory.skills.eoa_purchase_abci.models import Params
from packages.valory.skills.eoa_purchase_abci.payloads import (
    PurchaseTokenPayload,
    RandomnessPayload,
    SelectKeeperPayload,
    ValidatePayload,
)
from packages.valory.skills.eoa_purchase_abci.rounds import (
    FundKeeperRound,
    KeeperSelectionAndFundingAbciApp,
    PeriodState,
    PurchaseTokenRound,
    PurchasingAndValidationAbciApp,
    RandomnessEoaRound,
    SelectKeeperEoaRound,
    ValidatePurchaseRound,
)
from packages.valory.skills.fractionalize_deployment_abci.payloads import (
    DeployVaultPayload,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


class EoaPurchaseBaseState(BaseState):
    """Base state behaviour for the common apps' skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, super().period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class RandomnessEoaRoundBehaviour(RandomnessBehaviour):
    """Retrieve randomness for oracle deployment."""

    state_id = "randomness_eoa"
    matching_round = RandomnessEoaRound
    payload_class = RandomnessPayload


class SelectKeeperEoaRoundBehaviour(SelectKeeperBehaviour):
    """Select the keeper agent."""

    state_id = "select_keeper_eoa"
    matching_round = SelectKeeperEoaRound
    payload_class = SelectKeeperPayload


class PurchaseTokenRoundBehaviour(EoaPurchaseBaseState):
    """Keeper purchases the token."""

    state_id = "token_purchase_behaviour"
    matching_round = PurchaseTokenRound

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - If the agent is the keeper, then prepare the transaction and send it.
        - Otherwise, wait until the next round.
        - If a timeout is hit, set exit A event, otherwise set done event.
        """
        if self.context.agent_address != self.period_state.most_voted_keeper_address:
            yield from self._not_keeper_act()
        else:
            yield from self._keeper_act()

    def _not_keeper_act(self) -> Generator:
        """Do the non-keeper action."""
        with self.context.benchmark_tool.measure(self.state_id).consensus():
            yield from self.wait_until_round_end()
            self.set_done()

    def _keeper_act(self) -> Generator:
        """Do the keeper action."""
        with self.context.benchmark_tool.measure(self.state_id).local():
            self.context.logger.info(
                "I am the designated sender, purchasing the token."
            )
            tx_digest = yield from self._send_purchase_transaction()

            if tx_digest:
                self.context.logger.info("The token was purchased successfully.")
                payload_data = dict(success=True, tx_digest=tx_digest)
            else:
                self.context.logger.error(
                    "Something went wrong when purchasing the token, returning the funds."
                )
                tx_digest = yield from self._return_funds()
                payload_data = dict(success=False, tx_digest=tx_digest)

        with self.context.benchmark_tool.measure(self.state_id).consensus():
            payload = PurchaseTokenPayload(
                self.context.agent_address,
                json.dumps(payload_data),
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _send_purchase_transaction(self) -> Generator[None, None, Optional[str]]:
        """Purchase the selected project."""
        project_to_purchase = self.period_state.db.get_strict("project_to_purchase")
        project_id = project_to_purchase["project_id"]
        value = project_to_purchase["price"]  # price of token in the project in wei

        contract_api_response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.params.artblocks_periphery_contract,
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            contract_callable="purchase_to",
            sender_address=self.context.agent_address,
            to_address=self.period_state.db.get("safe_contract_address"),
            project_id=project_id,
            value=value,
        )
        if (
            contract_api_response.performative
            != ContractApiMessage.Performative.RAW_TRANSACTION
        ):  # pragma: nocover
            self.context.logger.warning("`purchase_to` transaction unsuccessful!")
            return None
        tx_digest, _ = yield from self.send_raw_transaction(
            contract_api_response.raw_transaction
        )
        if tx_digest is None:  # pragma: nocover
            self.context.logger.warning("send_raw_transaction unsuccessful!")
            return None
        self.context.logger.info(f"Purchase tx digest: {tx_digest}")
        return tx_digest

    def _return_funds(self) -> Generator[None, None, Optional[str]]:
        """Return the funds in case the transaction didn't go through."""
        # TODO: transfer the same amount of funds to the safe contract as the cost of the intended token to purchase
        self.context.logger.info("Returning borrowed funds to the safe contract.")
        yield

        return "0x0"


class FundKeeperRoundBehaviour(EoaPurchaseBaseState):
    """Fund the keeper."""

    state_id = "fund_keeper_behaviour"
    matching_round = FundKeeperRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                project_to_purchase = self.period_state.db.get_strict(
                    "project_to_purchase"
                )
                value = project_to_purchase[
                    "price"
                ]  # price of token in the project in wei
                tx_hash = yield from self._get_safe_hash(value)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=value,
                    safe_tx_gas=10 ** 7,
                    to_address=self.period_state.most_voted_keeper_address,
                    data=b"",
                )

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"Couldn't create FundKeeperRound payload, {type(e).__name__}: {e}."
                )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = DeployVaultPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, value: int) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.db.get("safe_contract_address"),
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.period_state.most_voted_keeper_address,
            value=value,
            data=b"",
            safe_tx_gas=10 ** 7,
        )

        enforce(
            response.state.body is not None
            and "tx_hash" in response.state.body.keys()
            and response.state.body["tx_hash"] is not None,
            "contract returned and empty body or empty tx_hash",
        )

        tx_hash = cast(str, response.state.body["tx_hash"])[2:]

        return tx_hash


class ValidatePurchaseRoundBehaviour(EoaPurchaseBaseState):
    """Validate Purchase."""

    state_id = "validate_keeper_purchase"
    matching_round = ValidatePurchaseRound

    def async_act(self) -> Generator:
        """Do the action."""
        with self.context.benchmark_tool.measure(self.state_id).local():
            payload_data: Dict = {}
            try:
                is_correct = yield from self._was_purchase_valid()
                payload_data = dict(is_correct=is_correct, slash_tx=None)

                if not is_correct:
                    slash_tx = yield from self._get_slash_tx()
                    payload_data["slash_tx"] = slash_tx

            except (AEAEnforceError, KeyError, ValueError) as e:
                self.context.logger.error(
                    f"Cannot validate the tx, the following error was encountered "
                    f"{type(e).__name__}: {e}"
                )

        with self.context.benchmark_tool.measure(self.state_id).consensus():
            payload = ValidatePayload(
                self.context.agent_address,
                json.dumps(payload_data),
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _was_purchase_valid(self) -> Generator[None, None, bool]:
        """Contract deployment verification."""
        keeper_report = json.loads(self.period_state.db.get_strict("purchase_data"))
        processed_keeper_txs = cast(
            List[str], self.period_state.db.get("processed_keeper_txs", [])
        )
        status = keeper_report["status"]
        tx_digest = keeper_report["tx_digest"]
        project_to_purchase = self.period_state.db.get_strict("project_to_purchase")
        project_id = project_to_purchase["project_id"]

        if status:
            # this means that the keeper claims that the token was purchased
            mint_event = yield from self._get_mint_event(tx_digest)
            return (
                mint_event["to"] == self.period_state.db.get("safe_contract_address")
                and mint_event["project_id"] == project_id
            )

        tx = yield from self._get_tx(tx_digest)
        return (
            tx["value"] == project_to_purchase
            and tx["from"] == self.period_state.most_voted_keeper_address
            and tx["to"] == self.period_state.db.get("safe_contract_address")
            and tx_digest not in processed_keeper_txs
        )

    def _get_mint_event(self, tx_digest: str) -> Generator[None, None, Dict]:
        """Check whether the mint there's a mint event, and if so if its the correct one."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="process_purchase_receipt",
            tx_hash=tx_digest,
        )

        enforce(
            response.state.body is not None
            and "token_id" in response.state.body.keys()
            and "to" in response.state.body.keys()
            and "project_id" in response.state.body.keys(),
            "Couldn't extract mint events.",
        )

        return response.state.body

    def _get_tx(self, tx_digest: str) -> Generator[None, None, Dict]:
        """Get the tx from hash."""
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_transaction",
            tx_hash=tx_digest,
        )

        enforce(response.state.body is not None, "Couldn't extract mint events.")

        return response.state.body

    def _get_slash_tx(self) -> Generator[None, None, str]:
        self.context.logger.info("Preparing a slash tx.")
        # TODO
        yield
        return "0x0"


class KeeperSelectionAndFundingAbciAppBehaviour(AbstractRoundBehaviour):
    """Behaviours for KeeperSelectionAndFundingAbciApp."""

    initial_state_cls = RandomnessEoaRoundBehaviour
    abci_app_cls = KeeperSelectionAndFundingAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        RandomnessEoaRoundBehaviour,
        SelectKeeperEoaRoundBehaviour,
        FundKeeperRoundBehaviour,
    }


class PurchasingAndValidationAbciAppBehaviour(AbstractRoundBehaviour):
    """Behaviours for PurchasingAndValidationAbciApp."""

    initial_state_cls = PurchaseTokenRoundBehaviour
    abci_app_cls = PurchasingAndValidationAbciApp
    behaviour_states: Set[Type[BaseState]] = {
        PurchaseTokenRoundBehaviour,
        ValidatePurchaseRoundBehaviour,
    }
