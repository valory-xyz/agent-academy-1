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

"""This module contains the behaviour_classes for the 'elcollectooorr_abci' skill."""

import json
from abc import ABC
from typing import Dict, Generator, List, Set, Type, cast

from aea.exceptions import AEAEnforceError, enforce

from packages.valory.contracts.artblocks.contract import ArtBlocksContract
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.elcollectooorr_abci.models import Params, SharedState
from packages.valory.skills.elcollectooorr_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    ResetPayload,
    TransactionPayload,
)
from packages.valory.skills.elcollectooorr_abci.rounds import (
    DecisionRound,
    DetailsRound,
    ElcollectooorrAbciApp,
    ElcollectooorrBaseAbciApp,
    FinishedElCollectoorBaseRound,
    ObservationRound,
    PeriodState,
    ResetFromObservationRound,
    TransactionRound,
)
from packages.valory.skills.registration_abci.behaviours import (
    AgentRegistrationRoundBehaviour,
    RegistrationStartupBehaviour,
)
from packages.valory.skills.safe_deployment_abci.behaviours import (
    SafeDeploymentRoundBehaviour,
)
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    TransactionSettlementRoundBehaviour,
)
from packages.valory.skills.transaction_settlement_abci.payload_tools import (
    hash_payload_to_hex,
)


class ElcollectooorrABCIBaseState(BaseState, ABC):
    """Base state behaviour for the El collectooorr abci skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, cast(SharedState, self.context.state).period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class ObservationRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Observation round behaviour"""

    state_id = "observation"
    matching_round = ObservationRound

    def async_act(self) -> Generator:
        """The observation act."""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            project_details = {}

            try:
                # fetch an active project
                response = yield from self.get_contract_api_response(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=self.params.artblocks_contract,
                    contract_id=str(ArtBlocksContract.contract_id),
                    contract_callable="get_active_project",
                    starting_id=self.params.starting_project_id,
                )

                # response body also has project details
                enforce(
                    response is not None
                    and response.state is not None
                    and response.state.body is not None,
                    "response, response.state, response.state.body must exist",
                )

                _project_details = response.state.body

                enforce(
                    "project_id" in _project_details.keys(),
                    "project_details was none, or project_id was not found in project_details",
                )

                project_id = _project_details["project_id"]
                project_details = _project_details

                self.context.logger.info(f"Retrieved project with id {project_id}.")

            except AEAEnforceError as e:
                self.context.logger.error(
                    f"project_id couldn't be extracted from contract response, e={e}"
                )

            with self.context.benchmark_tool.measure(
                self,
            ).consensus():
                payload = ObservationPayload(
                    self.context.agent_address,
                    json.dumps(project_details),
                )

                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()

        self.set_done()


class BaseResetBehaviour(ElcollectooorrABCIBaseState):
    """Reset state."""

    pause = True

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Trivially log the state.
        - Sleep for configured interval.
        - Build a registration transaction.
        - Send the transaction and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour state (set done event).
        """
        if self.pause:
            self.context.logger.info("Period end.")
            self.context.benchmark_tool.save()
            yield from self.sleep(self.params.observation_interval)
        else:
            self.context.logger.info(
                f"Period {self.period_state.period_count} was not finished. Resetting!"
            )

        payload = ResetPayload(
            self.context.agent_address, self.period_state.period_count + 1
        )

        yield from self.send_a2a_transaction(payload)
        yield from self.wait_until_round_end()
        self.set_done()


class DetailsRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Details Round behaviour"""

    state_id = "details"
    matching_round = DetailsRound

    def async_act(self) -> Generator:
        """The details act"""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # fetch an active project
            most_voted_project = json.loads(self.period_state.most_voted_project)

            try:
                all_details = json.loads(self.period_state.most_voted_details)
            except ValueError:
                all_details = []

            new_details = yield from self._get_details(most_voted_project)

            all_details.append(new_details)

            self.context.logger.info(
                f"Total length of details array {len(all_details)}."
            )

            payload = DetailsPayload(
                self.context.agent_address,
                json.dumps(all_details),
            )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_details(self, project: dict) -> Generator[None, None, Dict]:
        self.context.logger.info(
            f"Gathering details on project with id={project['project_id']}."
        )

        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="get_dynamic_details",
            project_id=project["project_id"],
        )

        new_details = cast(Dict, response.state.body)

        self.context.logger.info(
            f"Successfully gathered details on project with id={project['project_id']}."
        )

        return new_details


class DecisionRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Decision Round behaviour"""

    state_id = "decision"
    matching_round = DecisionRound

    def async_act(self) -> Generator:
        """The Decision act"""
        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # fetch an active project
            most_voted_project = json.loads(self.period_state.most_voted_project)
            most_voted_details = json.loads(self.period_state.most_voted_details)

            enforce(
                isinstance(most_voted_project, dict), "most_voted_project is not dict"
            )
            enforce(
                isinstance(most_voted_details, list),
                "most_voted_details is not an array",
            )

            decision = self._make_decision(most_voted_project, most_voted_details)
            payload = DecisionPayload(
                self.context.agent_address,
                decision,
            )

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _make_decision(
        self, project_details: dict, most_voted_details: List[dict]
    ) -> int:
        """Method that decides on an outcome"""
        decision_model = self.params.decision_model_type()

        if decision_model.static(project_details):
            self.context.logger.info(
                f'making decision on project with id {project_details["project_id"]}'
            )
            decision = decision_model.dynamic(most_voted_details)
        else:
            decision = 0

        self.context.logger.info(
            f'decided {decision} for project with id {project_details["project_id"]}'
        )

        return decision


class TransactionRoundBehaviour(ElcollectooorrABCIBaseState):
    """Defines the Transaction Round behaviour"""

    state_id = "transaction_collection"
    matching_round = TransactionRound

    def async_act(self) -> Generator:
        """Implement the act."""
        payload_data = ""

        with self.context.benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            try:
                project_id = json.loads(self.period_state.most_voted_project)[
                    "project_id"
                ]

                enforce(
                    project_id is not None,
                    "couldn't find project_id, or project_id is None",
                )

                purchase_data_str = yield from self._get_purchase_data(project_id)
                purchase_data = bytes.fromhex(purchase_data_str[2:])
                tx_hash = yield from self._get_safe_hash(purchase_data)

                payload_data = hash_payload_to_hex(
                    safe_tx_hash=tx_hash,
                    ether_value=self._get_value_in_wei(),
                    safe_tx_gas=10 ** 7,
                    to_address=self.params.artblocks_periphery_contract,
                    data=purchase_data,
                )

            except AEAEnforceError as e:
                self.context.logger.error(f"couldn't create transaction payload, e={e}")

        with self.context.benchmark_tool.measure(
            self,
        ).consensus():
            payload = TransactionPayload(
                self.context.agent_address,
                payload_data,
            )

            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_safe_hash(self, data: bytes) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,  # type: ignore
            contract_address=self.period_state.safe_contract_address,
            contract_id=str(GnosisSafeContract.contract_id),
            contract_callable="get_raw_safe_transaction_hash",
            to_address=self.params.artblocks_periphery_contract,
            value=self._get_value_in_wei(),
            data=data,
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

    def _get_purchase_data(self, project_id: int) -> Generator[None, None, str]:
        response = yield from self.get_contract_api_response(
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.params.artblocks_contract,
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            contract_callable="purchase_data",
            project_id=project_id,
        )

        # response body also has project details
        enforce(
            response.state.body is not None
            and "data" in response.state.body.keys()
            and response.state.body["data"] is not None,
            "contract returned and empty body or empty data",
        )

        purchase_data = cast(str, response.state.body["data"])

        return purchase_data

    def _get_value_in_wei(self) -> int:
        details: List[Dict] = json.loads(self.period_state.most_voted_details)
        min_value = details[0]["price_per_token_in_wei"]

        for detail in details:
            min_value = min(min_value, detail["price_per_token_in_wei"])

        return min_value

    def _format_payload(self, tx_hash: str, data: str) -> str:
        tx_hash = tx_hash[2:]
        ether_value = int.to_bytes(self._get_value_in_wei(), 32, "big").hex().__str__()
        safe_tx_gas = int.to_bytes(10 ** 7, 32, "big").hex().__str__()
        address = self.params.artblocks_periphery_contract
        data = data[2:]  # remove starting '0x'

        return f"{tx_hash}{ether_value}{safe_tx_gas}{address}{data}"


class ResetFromObservationBehaviour(BaseResetBehaviour):
    """Reset state."""

    matching_round = ResetFromObservationRound
    state_id = "reset_from_obs"
    pause = False


class FinishedElCollectoorBaseRoundBehaviour(ElcollectooorrABCIBaseState):
    """Degenerate behaviour for a degenerate round"""

    matching_round = FinishedElCollectoorBaseRound
    state_id = "finished_el_collectooorr_base"

    def async_act(self) -> Generator:
        """Simply log that the app was executed successfully."""
        self.context.logger.info("Successfully executed Elcollectooorr Base app.")
        self.set_done()
        yield


class ElcollectooorroundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El collectooorr abci app."""

    initial_state_cls = ObservationRoundBehaviour
    abci_app_cls = ElcollectooorrBaseAbciApp  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {  # type: ignore
        ObservationRoundBehaviour,  # type: ignore
        DetailsRoundBehaviour,  # type: ignore
        DecisionRoundBehaviour,  # type: ignore
        TransactionRoundBehaviour,  # type: ignore
        ResetFromObservationBehaviour,  # type: ignore
    }


class ElcollectooorrFullRoundBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El collectooorr abci app."""

    initial_state_cls = RegistrationStartupBehaviour
    abci_app_cls = ElcollectooorrAbciApp  # type: ignore
    behaviour_states: Set[Type[BaseState]] = {
        *AgentRegistrationRoundBehaviour.behaviour_states,
        *SafeDeploymentRoundBehaviour.behaviour_states,
        *TransactionSettlementRoundBehaviour.behaviour_states,
        *ElcollectooorroundBehaviour.behaviour_states,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        self.context.benchmark_tool.logger = self.context.logger
