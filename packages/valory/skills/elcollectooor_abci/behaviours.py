# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021 Valory AG
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

"""This module contains the behaviour_classes for the 'elcollectooor_abci' skill."""

import datetime
import json
from abc import ABC
from math import floor
from typing import Any, Generator, List, Optional, Set, Type, cast

from aea.exceptions import AEAEnforceError, enforce

from packages.valory.contracts.artblocks.contract import ArtBlocksContract
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.protocols.contract_api import ContractApiMessage
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.abstract_round_abci.common import (
    RandomnessBehaviour,
    SelectKeeperBehaviour,
)
from packages.valory.skills.abstract_round_abci.utils import BenchmarkTool
from packages.valory.skills.elcollectooor_abci.models import Params, SharedState
from packages.valory.skills.elcollectooor_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    RandomnessPayload,
    RegistrationPayload,
    ResetPayload,
    SelectKeeperPayload,
    TransactionPayload,
)
from packages.valory.skills.elcollectooor_abci.rounds import (
    DecisionRound,
    DetailsRound,
    ElCollectooorAbciApp,
    ObservationRound,
    PeriodState,
    RandomnessStartupRound,
    RegistrationRound,
    ResetFromObservationRound,
    ResetFromRegistrationRound,
    SelectKeeperAStartupRound,
    TransactionRound,
)
from packages.valory.skills.elcollectooor_abci.simple_decision_model import (
    DecisionModel,
)


def random_selection(elements: List[str], randomness: float) -> str:
    """
    Select a random element from a list.

    :param: elements: a list of elements to choose among
    :param: randomness: a random number in the [0,1) interval
    :return: a randomly chosen element
    """
    random_position = floor(randomness * len(elements))
    return elements[random_position]


benchmark_tool = BenchmarkTool()


class ElCollectooorABCIBaseState(BaseState, ABC):
    """Base state behaviour for the El Collectooor abci skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, cast(SharedState, self.context.state).period_state)

    @property
    def params(self) -> Params:
        """Return the params."""
        return cast(Params, self.context.params)


class TendermintHealthcheckBehaviour(BaseState):
    """Check whether Tendermint nodes are running."""

    state_id = "tendermint_healthcheck"
    matching_round = None

    _check_started: Optional[datetime.datetime] = None
    _timeout: float

    def start(self) -> None:
        """Set up the behaviour."""
        if self._check_started is None:
            self._check_started = datetime.datetime.now()
            self._timeout = self.params.max_healthcheck

    def _is_timeout_expired(self) -> bool:
        """Check if the timeout expired."""
        if self._check_started is None:
            return False  # pragma: no cover
        return datetime.datetime.now() > self._check_started + datetime.timedelta(
            0, self._timeout
        )

    def async_act(self) -> Generator:
        """Do the action."""
        self.start()
        if self._is_timeout_expired():
            # if the Tendermint node cannot update the app then the app cannot work
            raise RuntimeError("Tendermint node did not come live!")
        status = yield from self._get_status()
        try:
            json_body = json.loads(status.body.decode())
        except json.JSONDecodeError:
            self.context.logger.error(
                "Tendermint not running or accepting transactions yet, trying again!"
            )
            yield from self.sleep(self.params.sleep_time)
            return
        remote_height = int(json_body["result"]["sync_info"]["latest_block_height"])
        local_height = self.context.state.period.height
        self.context.logger.info(
            "local-height = %s, remote-height=%s", local_height, remote_height
        )
        if local_height != remote_height:
            self.context.logger.info("local height != remote height; retrying...")
            yield from self.sleep(self.params.sleep_time)
            return
        self.context.logger.info("local height == remote height; done")
        self.set_done()


class RegistrationBehaviour(ElCollectooorABCIBaseState):
    """Register to the next round."""

    state_id = "register"
    matching_round = RegistrationRound

    def async_act(self) -> Generator:
        """
        Do the action.

        Steps:
        - Build a registration transaction.
        - Send the transaction and wait for it to be mined.
        - Wait until ABCI application transitions to the next round.
        - Go to the next behaviour state (set done event).
        """

        with benchmark_tool.measure(
            self,
        ).local():
            payload = RegistrationPayload(self.context.agent_address)

        with benchmark_tool.measure(
            self,
        ).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()


class RandomnessAtStartupBehaviour(RandomnessBehaviour):
    """Retrive randomness at startup."""

    state_id = "retrieve_randomness_at_startup"
    matching_round = RandomnessStartupRound
    payload_class = RandomnessPayload


class SelectKeeperAtStartupBehaviour(SelectKeeperBehaviour):
    """Select the keeper agent at startup."""

    state_id = "select_keeper_a_at_startup"
    matching_round = SelectKeeperAStartupRound
    payload_class = SelectKeeperPayload


class BaseResetBehaviour(ElCollectooorABCIBaseState):
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
            benchmark_tool.save()
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


class ObservationRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "observation"
    matching_round = ObservationRound

    def __init__(self, *args: Any, **kwargs: Any):
        """Init the observing behaviour."""
        super().__init__(**kwargs)
        # TODO: not all vars are necessary
        self.max_eth_in_wei = kwargs.pop("max_eth_in_wei", 1000000000000000000)
        self.safe_tx_gas = kwargs.pop("safe_tx_gas", 4000000)
        self.artblocks_contract = kwargs.pop(
            "artblocks_contract", "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
        )
        self.artblocks_periphery_contract = kwargs.pop(
            "artblocks_periphery_contract", "0x58727f5Fc3705C30C9aDC2bcCC787AB2BA24c441"
        )
        self.safe_contract = kwargs.pop(
            "safe_contract", "0x2caB92c1E9D2a701Ca0411b0ff35A0907Ca31F7f"
        )
        self.seconds_between_periods = kwargs.pop("seconds_between_periods", 30)
        self.starting_id = kwargs.pop("starting_id", 0)

        self.max_retries = kwargs.pop("max_retries", 5)
        self._retries_made = 0

    def async_act(self) -> Generator:
        """Implement the act."""

        if self.is_retries_exceeded():
            with benchmark_tool.measure(
                self,
            ).consensus():
                yield from self.wait_until_round_end()

            self.set_done()
            self._reset_retries()
            return

        with benchmark_tool.measure(
            self,
        ).local():
            # fetch an active project
            response = yield from self.get_contract_api_response(
                request_callback=self.default_callback_request,
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=self.artblocks_contract,
                contract_id=str(ArtBlocksContract.contract_id),
                contract_callable="get_active_project",
                starting_id=self.starting_id,
            )

            # response body also has project details
            project_details = response.state.body
            project_id = (
                project_details["project_id"]
                if "project_id" in project_details.keys()
                else None
            )

        if project_id:
            self.context.logger.info(f"Retrieved project id: {project_id}.")
            payload = ObservationPayload(
                self.context.agent_address,
                project_details,
            )

            with benchmark_tool.measure(
                self,
            ).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()
        else:
            self.context.logger.error(
                "project_id couldn't be extracted from contract response"
            )
            yield from self.sleep(self.params.sleep_time)
            self._increment_retries()

        self.set_done()

    def _increment_retries(self):
        self._retries_made += 1

    def is_retries_exceeded(self) -> bool:
        return self._retries_made > self.max_retries

    def _reset_retries(self):
        self._retries_made = 0


class DetailsRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "details"
    matching_round = DetailsRound

    def __init__(self, *args: Any, **kwargs: Any):
        """Init the details behaviour"""
        super().__init__(**kwargs)
        self.artblocks_contract = kwargs.pop(
            "artblocks_contract", "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
        )

    def async_act(self) -> Generator:
        with benchmark_tool.measure(
            self,
        ).local():
            # fetch an active project
            most_voted_project = json.loads(self.period_state.most_voted_project)

            try:
                all_details = json.loads(self.period_state.most_voted_details)
            except AEAEnforceError:
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

        with benchmark_tool.measure(
            self,
        ).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _get_details(self, project: dict) -> dict:
        self.context.logger.info(
            f"Gathering details on project with id={project['project_id']}."
        )

        response = yield from self.get_contract_api_response(
            request_callback=self.default_callback_request,
            performative=ContractApiMessage.Performative.GET_STATE,
            contract_address=self.artblocks_contract,
            contract_id=str(ArtBlocksContract.contract_id),
            contract_callable="get_dynamic_details",
            project_id=project["project_id"],
        )

        new_details = response.state.body

        self.context.logger.info(
            f"Successfully gathered details on project with id={project['project_id']}."
        )

        return new_details


class DecisionRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "decision"
    matching_round = DecisionRound

    def async_act(self) -> Generator:
        with benchmark_tool.measure(
            self,
        ).local():
            # fetch an active project
            most_voted_project = json.loads(self.period_state.most_voted_project)
            most_voted_details = json.loads(self.period_state.most_voted_details)

            enforce(type(most_voted_project) == dict, "most_voted_project is not dict")
            enforce(
                type(most_voted_details) == list, "most_voted_details is not an array"
            )

            decision = self._make_decision(most_voted_project, most_voted_details)
            payload = DecisionPayload(
                self.context.agent_address,
                decision,
            )

        with benchmark_tool.measure(
            self,
        ).consensus():
            yield from self.send_a2a_transaction(payload)
            yield from self.wait_until_round_end()

        self.set_done()

    def _make_decision(self, project_details: dict, most_voted_details: [dict]) -> int:
        """Method that decides on an outcome"""
        decision_model = DecisionModel()
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


class TransactionRoundBehaviour(ElCollectooorABCIBaseState):
    state_id = "transaction_collection"
    matching_round = TransactionRound

    def __init__(self, *args: Any, **kwargs: Any):
        """Init the observing behaviour."""
        super().__init__(**kwargs)
        # TODO: not all vars are necessary
        self.max_eth_in_wei = kwargs.pop("max_eth_in_wei", 1000000000000000000)
        self.safe_tx_gas = kwargs.pop("safe_tx_gas", 4000000)
        self.artblocks_contract = kwargs.pop(
            "artblocks_contract", "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
        )
        self.artblocks_periphery_contract = kwargs.pop(
            "artblocks_periphery_contract", "0x58727f5Fc3705C30C9aDC2bcCC787AB2BA24c441"
        )
        self.safe_contract = kwargs.pop(
            "safe_contract", "0x2caB92c1E9D2a701Ca0411b0ff35A0907Ca31F7f"
        )
        self.seconds_between_periods = kwargs.pop("seconds_between_periods", 30)
        self.starting_id = kwargs.pop("starting_id", 0)
        self.max_retries = kwargs.pop("max_retries", 5)
        self._retries_made = 0

    def async_act(self) -> Generator:
        """Implement the act."""

        if self.is_retries_exceeded():
            with benchmark_tool.measure(
                self,
            ).consensus():
                yield from self.wait_until_round_end()

            self.set_done()
            self._reset_retries()
            return

        with benchmark_tool.measure(
            self,
        ).local():
            # we extract the project_id from the frozen set, and throw an error if it doest exist
            project_id = json.loads(self.period_state.most_voted_project)["project_id"]
            enforce(
                project_id is not None,
                "couldn't find project_id, or project_id is None",
            )

            response = yield from self.get_contract_api_response(
                request_callback=self.default_callback_request,
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=self.artblocks_periphery_contract,
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
            data: Optional[str] = cast(Optional[str], response.state.body["data"])

        if data:
            payload = TransactionPayload(
                self.context.agent_address,
                data,
            )
            with benchmark_tool.measure(
                self,
            ).consensus():
                yield from self.send_a2a_transaction(payload)
                yield from self.wait_until_round_end()
        else:
            self.context.logger.error(
                "couldn't extract purchase_data from contract response"
            )
            yield from self.sleep(self.params.sleep_time)
            self._increment_retries()
        self.set_done()

    def _increment_retries(self):
        self._retries_made += 1

    def is_retries_exceeded(self) -> bool:
        return self._retries_made > self.max_retries

    def _reset_retries(self):
        self._retries_made = 0


class ResetFromRegistrationBehaviour(BaseResetBehaviour):
    """Reset state."""

    matching_round = ResetFromRegistrationRound
    state_id = "reset_from_reg"
    pause = False


class ResetFromObservationBehaviour(BaseResetBehaviour):
    """Reset state."""

    matching_round = ResetFromObservationRound
    state_id = "reset_from_obs"
    pause = False


class ElCollectooorAbciConsensusBehaviour(AbstractRoundBehaviour):
    """This behaviour manages the consensus stages for the El Collectooor abci app."""

    initial_state_cls = TendermintHealthcheckBehaviour
    abci_app_cls = ElCollectooorAbciApp
    behaviour_states: Set[Type[ElCollectooorABCIBaseState]] = {
        TendermintHealthcheckBehaviour,  #
        RegistrationBehaviour,
        RandomnessAtStartupBehaviour,
        SelectKeeperAtStartupBehaviour,
        ObservationRoundBehaviour,
        DetailsRoundBehaviour,
        DecisionRoundBehaviour,
        TransactionRoundBehaviour,
        ResetFromRegistrationBehaviour,
        ResetFromObservationBehaviour,
    }

    def setup(self) -> None:
        """Set up the behaviour."""
        super().setup()
        benchmark_tool.logger = self.context.logger
