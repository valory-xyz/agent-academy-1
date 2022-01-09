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

"""Tests for valory/elcollectooor_abci skill's behaviours."""
import json
import logging
import time
from copy import copy
from pathlib import Path
from typing import Any, Dict, Type, cast
from unittest import mock
from unittest.mock import patch

from aea.helpers.transaction.base import SignedMessage, State
from aea.test_tools.test_skill import BaseSkillTestCase

from packages.open_aea.protocols.signing import SigningMessage
from packages.valory.connections.http_client.connection import (
    PUBLIC_ID as HTTP_CLIENT_PUBLIC_ID,
)
from packages.valory.connections.ledger.base import (
    CONNECTION_ID as LEDGER_CONNECTION_PUBLIC_ID,
)
from packages.valory.contracts.artblocks.contract import ArtBlocksContract
from packages.valory.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.protocols.http import HttpMessage
from packages.valory.protocols.ledger_api.message import LedgerApiMessage
from packages.valory.skills.abstract_round_abci.base import (
    AbstractRound,
    BasePeriodState,
    BaseTxPayload,
    OK_CODE,
    StateDB,
    _MetaPayload,
)
from packages.valory.skills.abstract_round_abci.behaviour_utils import BaseState
from packages.valory.skills.abstract_round_abci.behaviours import AbstractRoundBehaviour
from packages.valory.skills.elcollectooor_abci.behaviours import (
    DecisionRoundBehaviour,
    DetailsRoundBehaviour,
    ObservationRoundBehaviour,
    ResetFromObservationBehaviour,
    TransactionRoundBehaviour, ElCollectooorAbciConsensusBehaviour,
)
from packages.valory.skills.elcollectooor_abci.handlers import (
    ContractApiHandler,
    HttpHandler,
    LedgerApiHandler,
    SigningHandler,
)
from packages.valory.skills.elcollectooor_abci.rounds import Event, PeriodState
from packages.valory.skills.elcollectooor_abci.simple_decision_model import (
    DecisionModel,
)
from tests.conftest import ROOT_DIR


class DummyRoundId:
    """Dummy class for setting round_id for exit condition."""

    round_id: str

    def __init__(self, round_id: str) -> None:
        """Dummy class for setting round_id for exit condition."""
        self.round_id = round_id


class ElCollectooorFSMBehaviourBaseCase(BaseSkillTestCase):
    """Base case for testing PriceEstimation FSMBehaviour."""

    path_to_skill = Path(ROOT_DIR, "packages", "valory", "skills", "elcollectooor_abci")

    elcollectooor_abci_behaviour: ElCollectooorAbciConsensusBehaviour
    ledger_handler: LedgerApiHandler
    http_handler: HttpHandler
    contract_handler: ContractApiHandler
    signing_handler: SigningHandler
    old_tx_type_to_payload_cls: Dict[str, Type[BaseTxPayload]]
    period_state: PeriodState

    @classmethod
    def setup(cls, **kwargs: Any) -> None:
        """Setup the test class."""
        # we need to store the current value of the meta-class attribute
        # _MetaPayload.transaction_type_to_payload_cls, and restore it
        # in the teardown function. We do a shallow copy so we avoid
        # modifying the old mapping during the execution of the tests.
        cls.old_tx_type_to_payload_cls = copy(
            _MetaPayload.transaction_type_to_payload_cls
        )
        _MetaPayload.transaction_type_to_payload_cls = {}
        super().setup()
        assert cls._skill.skill_context._agent_context is not None
        cls._skill.skill_context._agent_context.identity._default_address_key = (
            "ethereum"
        )
        cls._skill.skill_context._agent_context._default_ledger_id = "ethereum"
        cls.elcollectooor_abci_behaviour = cast(
            ElCollectooorAbciConsensusBehaviour,
            cls._skill.skill_context.behaviours.main,
        )
        cls.http_handler = cast(HttpHandler, cls._skill.skill_context.handlers.http)
        cls.signing_handler = cast(
            SigningHandler, cls._skill.skill_context.handlers.signing
        )
        cls.contract_handler = cast(
            ContractApiHandler, cls._skill.skill_context.handlers.contract_api
        )
        cls.ledger_handler = cast(
            LedgerApiHandler, cls._skill.skill_context.handlers.ledger_api
        )

        cls.elcollectooor_abci_behaviour.setup()
        cls._skill.skill_context.state.setup()
        assert (
            cast(BaseState, cls.elcollectooor_abci_behaviour.current_state).state_id
            == cls.elcollectooor_abci_behaviour.initial_state_cls.state_id
        )
        cls.period_state = PeriodState(StateDB(initial_period=0, initial_data={}))

    def fast_forward_to_state(
        self,
        behaviour: AbstractRoundBehaviour,
        state_id: str,
        period_state: BasePeriodState,
    ) -> None:
        """Fast forward the FSM to a state."""
        next_state = {s.state_id: s for s in behaviour.behaviour_states}[state_id]
        assert next_state is not None, f"State {state_id} not found"
        next_state = cast(Type[BaseState], next_state)
        behaviour.current_state = next_state(
            name=next_state.state_id, skill_context=behaviour.context
        )
        self.skill.skill_context.state.period.abci_app._round_results.append(
            period_state
        )
        if next_state.matching_round is not None:
            self.skill.skill_context.state.period.abci_app._current_round = (
                next_state.matching_round(
                    period_state, self.skill.skill_context.params.consensus_params
                )
            )

    def mock_ledger_api_request(
        self, request_kwargs: Dict, response_kwargs: Dict
    ) -> None:
        """
        Mock http request.

        :param request_kwargs: keyword arguments for request check.
        :param response_kwargs: keyword arguments for mock response.
        """

        self.assert_quantity_in_outbox(1)
        actual_ledger_api_message = self.get_message_from_outbox()
        assert actual_ledger_api_message is not None, "No message in outbox."
        has_attributes, error_str = self.message_has_attributes(
            actual_message=actual_ledger_api_message,
            message_type=LedgerApiMessage,
            to=str(LEDGER_CONNECTION_PUBLIC_ID),
            sender=str(self.skill.skill_context.skill_id),
            **request_kwargs,
        )

        assert has_attributes, error_str
        incoming_message = self.build_incoming_message(
            message_type=LedgerApiMessage,
            dialogue_reference=(
                actual_ledger_api_message.dialogue_reference[0],
                "stub",
            ),
            target=actual_ledger_api_message.message_id,
            message_id=-1,
            to=str(self.skill.skill_context.skill_id),
            sender=str(LEDGER_CONNECTION_PUBLIC_ID),
            ledger_id=str(LEDGER_CONNECTION_PUBLIC_ID),
            **response_kwargs,
        )
        self.ledger_handler.handle(incoming_message)
        self.elcollectooor_abci_behaviour.act_wrapper()

    def mock_contract_api_request(
        self, contract_id: str, request_kwargs: Dict, response_kwargs: Dict
    ) -> None:
        """
        Mock http request.

        :param contract_id: contract id.
        :param request_kwargs: keyword arguments for request check.
        :param response_kwargs: keyword arguments for mock response.
        """

        self.assert_quantity_in_outbox(1)
        actual_contract_ledger_message = self.get_message_from_outbox()
        assert actual_contract_ledger_message is not None, "No message in outbox."
        has_attributes, error_str = self.message_has_attributes(
            actual_message=actual_contract_ledger_message,
            message_type=ContractApiMessage,
            to=str(LEDGER_CONNECTION_PUBLIC_ID),
            sender=str(self.skill.skill_context.skill_id),
            ledger_id="ethereum",
            contract_id=contract_id,
            message_id=1,
            **request_kwargs,
        )
        assert has_attributes, error_str
        self.elcollectooor_abci_behaviour.act_wrapper()

        incoming_message = self.build_incoming_message(
            message_type=ContractApiMessage,
            dialogue_reference=(
                actual_contract_ledger_message.dialogue_reference[0],
                "stub",
            ),
            target=actual_contract_ledger_message.message_id,
            message_id=-1,
            to=str(self.skill.skill_context.skill_id),
            sender=str(LEDGER_CONNECTION_PUBLIC_ID),
            ledger_id="ethereum",
            contract_id=contract_id,
            **response_kwargs,
        )
        self.contract_handler.handle(incoming_message)
        self.elcollectooor_abci_behaviour.act_wrapper()

    def mock_http_request(self, request_kwargs: Dict, response_kwargs: Dict) -> None:
        """
        Mock http request.

        :param request_kwargs: keyword arguments for request check.
        :param response_kwargs: keyword arguments for mock response.
        """

        self.assert_quantity_in_outbox(1)
        actual_http_message = self.get_message_from_outbox()
        assert actual_http_message is not None, "No message in outbox."
        has_attributes, error_str = self.message_has_attributes(
            actual_message=actual_http_message,
            message_type=HttpMessage,
            performative=HttpMessage.Performative.REQUEST,
            to=str(HTTP_CLIENT_PUBLIC_ID),
            sender=str(self.skill.skill_context.skill_id),
            **request_kwargs,
        )
        assert has_attributes, error_str
        self.elcollectooor_abci_behaviour.act_wrapper()
        self.assert_quantity_in_outbox(0)
        incoming_message = self.build_incoming_message(
            message_type=HttpMessage,
            dialogue_reference=(actual_http_message.dialogue_reference[0], "stub"),
            performative=HttpMessage.Performative.RESPONSE,
            target=actual_http_message.message_id,
            message_id=-1,
            to=str(self.skill.skill_context.skill_id),
            sender=str(HTTP_CLIENT_PUBLIC_ID),
            **response_kwargs,
        )
        self.http_handler.handle(incoming_message)
        self.elcollectooor_abci_behaviour.act_wrapper()

    def mock_signing_request(self, request_kwargs: Dict, response_kwargs: Dict) -> None:
        """Mock signing request."""
        self.assert_quantity_in_decision_making_queue(1)
        actual_signing_message = self.get_message_from_decision_maker_inbox()
        assert actual_signing_message is not None, "No message in outbox."
        has_attributes, error_str = self.message_has_attributes(
            actual_message=actual_signing_message,
            message_type=SigningMessage,
            to="dummy_decision_maker_address",
            sender=str(self.skill.skill_context.skill_id),
            **request_kwargs,
        )
        assert has_attributes, error_str
        incoming_message = self.build_incoming_message(
            message_type=SigningMessage,
            dialogue_reference=(actual_signing_message.dialogue_reference[0], "stub"),
            target=actual_signing_message.message_id,
            message_id=-1,
            to=str(self.skill.skill_context.skill_id),
            sender="dummy_decision_maker_address",
            **response_kwargs,
        )
        self.signing_handler.handle(incoming_message)
        self.elcollectooor_abci_behaviour.act_wrapper()

    def mock_a2a_transaction(
        self,
    ) -> None:
        """Performs mock a2a transaction."""

        self.mock_signing_request(
            request_kwargs=dict(
                performative=SigningMessage.Performative.SIGN_MESSAGE,
            ),
            response_kwargs=dict(
                performative=SigningMessage.Performative.SIGNED_MESSAGE,
                signed_message=SignedMessage(
                    ledger_id="ethereum", body="stub_signature"
                ),
            ),
        )

        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=json.dumps({"result": {"hash": ""}}).encode("utf-8"),
            ),
        )
        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=json.dumps({"result": {"tx_result": {"code": OK_CODE}}}).encode(
                    "utf-8"
                ),
            ),
        )

    def end_round(self, event: Event = Event.DONE) -> None:
        """Ends round early to cover `wait_for_end` generator."""
        current_state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        if current_state is None:
            return
        current_state = cast(BaseState, current_state)
        if current_state.matching_round is None:
            return
        abci_app = current_state.context.state.period.abci_app
        old_round = abci_app._current_round
        abci_app._last_round = old_round
        abci_app._current_round = abci_app.transition_function[
            current_state.matching_round
        ][event](abci_app.state, abci_app.consensus_params)
        abci_app._previous_rounds.append(old_round)
        self.elcollectooor_abci_behaviour._process_current_round()

    def _test_done_flag_set(self) -> None:
        """Test that, when round ends, the 'done' flag is set."""
        current_state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert not self.elcollectooor_abci_behaviour.current_state.is_done()
        with mock.patch.object(
            self.elcollectooor_abci_behaviour.context.state, "period"
        ) as mock_period:
            mock_period.last_round_id = cast(
                AbstractRound,
                self.elcollectooor_abci_behaviour.current_state.matching_round,
            ).round_id
            current_state.act_wrapper()
            assert current_state.is_done()

    @classmethod
    def teardown(cls) -> None:
        """Teardown the test class."""
        _MetaPayload.transaction_type_to_payload_cls = cls.old_tx_type_to_payload_cls  # type: ignore


class BaseRandomnessBehaviourTest(ElCollectooorFSMBehaviourBaseCase):
    """Test RandomnessBehaviour."""

    randomness_behaviour_class: Type[BaseState]
    next_behaviour_class: Type[BaseState]

    def test_randomness_behaviour(
        self,
    ) -> None:
        """Test RandomnessBehaviour."""

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.randomness_behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )
        # TODO: why casting to BaseState twice?
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.randomness_behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.act_wrapper()
        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
                url="https://drand.cloudflare.com/public/latest",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=json.dumps(
                    {
                        "round": 1283255,
                        "randomness": "04d4866c26e03347d2431caa82ab2d7b7bdbec8b58bca9460c96f5265d878feb",
                    }
                ).encode("utf-8"),
            ),
        )

        self.elcollectooor_abci_behaviour.act_wrapper()
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round()

        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id

    def test_invalid_response(
        self,
    ) -> None:
        """Test invalid json response."""
        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.randomness_behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.randomness_behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.act_wrapper()

        self.mock_http_request(
            request_kwargs=dict(
                method="GET",
                headers="",
                version="",
                body=b"",
                url="https://drand.cloudflare.com/public/latest",
            ),
            response_kwargs=dict(
                version="", status_code=200, status_text="", headers="", body=b""
            ),
        )
        self.elcollectooor_abci_behaviour.act_wrapper()
        time.sleep(1)
        self.elcollectooor_abci_behaviour.act_wrapper()

    def test_max_retries_reached(
        self,
    ) -> None:
        """Test with max retries reached."""
        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.randomness_behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.randomness_behaviour_class.state_id
        )
        with mock.patch.object(
            self.elcollectooor_abci_behaviour.context.randomness_api,
            "is_retries_exceeded",
            return_value=True,
        ):
            self.elcollectooor_abci_behaviour.act_wrapper()
            state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
            assert state.state_id == self.randomness_behaviour_class.state_id
            self._test_done_flag_set()

    def test_clean_up(
        self,
    ) -> None:
        """Test when `observed` value is none."""
        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.randomness_behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.randomness_behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.context.randomness_api._retries_attempted = 1
        assert self.elcollectooor_abci_behaviour.current_state is not None
        self.elcollectooor_abci_behaviour.current_state.clean_up()
        assert (
            self.elcollectooor_abci_behaviour.context.randomness_api._retries_attempted
            == 0
        )


class BaseSelectKeeperBehaviourTest(ElCollectooorFSMBehaviourBaseCase):
    """Test SelectKeeperBehaviour."""

    select_keeper_behaviour_class: Type[BaseState]
    next_behaviour_class: Type[BaseState]

    def test_select_keeper(
        self,
    ) -> None:
        """Test select keeper agent."""
        participants = frozenset({self.skill.skill_context.agent_address, "a_1", "a_2"})
        self.fast_forward_to_state(
            behaviour=self.elcollectooor_abci_behaviour,
            state_id=self.select_keeper_behaviour_class.state_id,
            period_state=PeriodState(
                StateDB(
                    0,
                    dict(
                        participants=participants,
                        most_voted_randomness="56cbde9e9bbcbdcaf92f183c678eaa5288581f06b1c9c7f884ce911776727688",
                    ),
                )
            ),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.select_keeper_behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.act_wrapper()
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round()
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id


class TestResetFromObservationBehaviour(ElCollectooorFSMBehaviourBaseCase):
    """Test ResetFromObservationBehaviour."""

    behaviour_class = ResetFromObservationBehaviour
    next_behaviour_class = ObservationRoundBehaviour

    def test_pause_and_reset_behaviour(
        self,
    ) -> None:
        """Test pause and reset behaviour."""
        self.fast_forward_to_state(
            behaviour=self.elcollectooor_abci_behaviour,
            state_id=self.behaviour_class.state_id,
            period_state=PeriodState(StateDB(0, dict())),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.context.params.observation_interval = 0.1
        self.elcollectooor_abci_behaviour.act_wrapper()
        time.sleep(0.3)
        self.elcollectooor_abci_behaviour.act_wrapper()
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round()
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id

    def test_reset_behaviour(
        self,
    ) -> None:
        """Test reset behaviour."""
        self.fast_forward_to_state(
            behaviour=self.elcollectooor_abci_behaviour,
            state_id=self.behaviour_class.state_id,
            period_state=PeriodState(StateDB(0, dict())),
        )
        self.elcollectooor_abci_behaviour.current_state.pause = False  # type: ignore
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.behaviour_class.state_id
        )
        self.elcollectooor_abci_behaviour.context.params.observation_interval = 0.1
        self.elcollectooor_abci_behaviour.act_wrapper()
        time.sleep(0.3)
        self.elcollectooor_abci_behaviour.act_wrapper()
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round()
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id


class TestObservationRoundBehaviour(ElCollectooorFSMBehaviourBaseCase):
    behaviour_class = ObservationRoundBehaviour
    next_behaviour_class = DecisionRoundBehaviour

    def test_contract_returns_project(self):
        """The agent queries the contract and gets back a project"""

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
                            "price_per_token_in_wei": 1,
                            "project_id": 121,
                            "project_name": "Incomplete Control",
                            "artist": "Tyler Hobbs",
                            "description": "",
                            "website": "tylerxhobbs.com",
                            "script": "too_long",
                            "ipfs_hash": "",
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Retrieved project id: 121.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == DecisionRoundBehaviour.state_id

    def test_contract_returns_empty_project(self):
        """The agent queries the contract and doesnt get back a project"""

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body={}),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "project_id couldn't be extracted from contract response",
            )

            self.elcollectooor_abci_behaviour.act_wrapper()
            time.sleep(1.1)
            self.elcollectooor_abci_behaviour.act_wrapper()

    def test_contract_retries_are_exceeded(self):
        """Test with max retries reached."""
        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict())),
        )
        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        with mock.patch.object(
            target=self.behaviour_class,
            attribute="is_retries_exceeded",
            return_value=True,
        ):
            assert self.behaviour_class.is_retries_exceeded()
            state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
            assert state.state_id == self.behaviour_class.state_id
            # self._test_done_flag_set() # TODO: make this work


class TestDetailsRoundBehaviour(ElCollectooorFSMBehaviourBaseCase):
    behaviour_class = DetailsRoundBehaviour
    next_behaviour_class = DecisionRoundBehaviour

    def test_next_state_is_decision(self):
        """The agent fetches details"""

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "royalty_receiver": "0x00000",
            "invocations": 1,
            "max_invocations": 10,
            "ipfs_hash": "",
        }
        test_details = [{}]

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        most_voted_project=json.dumps(test_project),
                        most_voted_details=json.dumps(test_details),
                    ),
                )
            ),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooor_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "price_per_token_in_wei": 123,
                            "invocations": 2,
                            "max_invocations": 10,
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Gathering details on project with id=121.",
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Successfully gathered details on project with id=121.",
            )

            mock_logger.assert_any_call(
                logging.INFO, "Total length of details array 2."
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id

    def test_calling_details_for_the_first_time(self):
        """The details round is called for the first round, the details array should have a length of 1."""

        """The agent fetches details"""

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "royalty_receiver": "0x00000",
            "invocations": 1,
            "max_invocations": 10,
            "ipfs_hash": "",
        }

        test_details = []

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        most_voted_project=json.dumps(test_project),
                        most_voted_details=json.dumps(test_details),
                    ),
                ),
            ),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooor_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "price_per_token_in_wei": 123,
                            "invocations": 2,
                            "max_invocations": 10,
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Gathering details on project with id=121.",
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Successfully gathered details on project with id=121.",
            )

            mock_logger.assert_any_call(
                logging.INFO, "Total length of details array 1."
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.next_behaviour_class.state_id


class TestDecisionRoundBehaviour(ElCollectooorFSMBehaviourBaseCase):
    behaviour_class = DecisionRoundBehaviour
    decided_yes_behaviour_class = TransactionRoundBehaviour
    decided_no_behaviour_class = ResetFromObservationBehaviour
    gib_details_behaviour_class = DetailsRoundBehaviour

    def test_decided_yes(self):
        """The agent evaluated the project and decided for YES"""

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "royalty_receiver": "0x00000",
            "invocations": 1,
            "max_invocations": 10,
            "ipfs_hash": "",
        }
        test_details = [
            {"price_per_token_in_wei": 1, "invocations": i, "max_invocations": 10}
            for i in range(5)
        ]

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        most_voted_project=json.dumps(test_project),
                        most_voted_details=json.dumps(test_details),
                    ),
                ),
            ),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooor_abci_behaviour.act_wrapper()

        mock_logger.assert_any_call(
            logging.INFO,
            "making decision on project with id 121",
        )

        mock_logger.assert_any_call(
            logging.INFO,
            "decided 1 for project with id 121",
        )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_YES)
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == self.decided_yes_behaviour_class.state_id

    def test_decided_no(self):
        """The agent evaluated the project and decided for NO"""

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "royalty_receiver": "0x00000",
            "invocations": 1,
            "max_invocations": 10,
            "ipfs_hash": "",
        }
        test_details = [{}]

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        most_voted_project=json.dumps(test_project),
                        most_voted_details=json.dumps(test_details),
                    ),
                ),
            ),
        )

        self.end_round(event=Event.DECIDED_NO)
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)

        assert state.state_id == self.decided_no_behaviour_class.state_id

    def test_decided_gib_details(self):
        """The agent decided it needs more data"""

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "royalty_receiver": "0x00000",
            "invocations": 1,
            "max_invocations": 10,
            "ipfs_hash": "",
        }
        test_details = [{}]

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        most_voted_project=json.dumps(test_project),
                        most_voted_details=json.dumps(test_details),
                    ),
                ),
            ),
        )

        self.end_round(event=Event.GIB_DETAILS)
        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)

        assert state.state_id == self.gib_details_behaviour_class.state_id


class TestTransactionRoundBehaviour(ElCollectooorFSMBehaviourBaseCase):
    behaviour_class = TransactionRoundBehaviour
    next_behaviour_class = ResetFromObservationBehaviour

    def test_contract_returns_valid_data(self):
        """
        The agent gathers the necessary data to make the purchase, makes a contract requests and receives valid data
        """

        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "ipfs_hash": "",
        }

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict(most_voted_project=json.dumps(test_project)))),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x58727f5Fc3705C30C9aDC2bcCC787AB2BA24c441",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={
                        "data": "0xefef39a10000000000000000000000000000000000000000000000000000000000000079"
                    },
                    ledger_id="ethereum",
                ),
            ),
        )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
        assert state.state_id == ResetFromObservationBehaviour.state_id

    def test_contract_returns_invalid_data(self):
        """
        The agent gathers the necessary data to make the purchase, makes a contract requests and receives invalid data
        The agent should retry
        """
        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "ipfs_hash": "",
        }

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict(most_voted_project=json.dumps(test_project)))),
        )

        assert (
            cast(BaseState, self.elcollectooor_abci_behaviour.current_state).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooor_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksPeripheryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x58727f5Fc3705C30C9aDC2bcCC787AB2BA24c441",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body={"data": ""}),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "couldn't extract purchase_data from contract response",
            )

            self.elcollectooor_abci_behaviour.act_wrapper()
            time.sleep(1.1)
            self.elcollectooor_abci_behaviour.act_wrapper()

    def test_retries_exceeded(self):
        """
        The agent gathers the necessary data to make the purchase, makes a contract requests and receives invalid data
        The agent should retry
        """
        test_project = {
            "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
            "price_per_token_in_wei": 1,
            "project_id": 121,
            "project_name": "Incomplete Control",
            "artist": "Tyler Hobbs",
            "description": "",
            "website": "tylerxhobbs.com",
            "script": "too_long",
            "ipfs_hash": "",
        }

        self.fast_forward_to_state(
            self.elcollectooor_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(StateDB(0, dict(most_voted_project=json.dumps(test_project)))),
        )

        assert (
            cast(
                BaseState,
                cast(BaseState, self.elcollectooor_abci_behaviour.current_state),
            ).state_id
            == self.behaviour_class.state_id
        )

        self.elcollectooor_abci_behaviour.act_wrapper()

        with mock.patch.object(
            target=self.behaviour_class,
            attribute="is_retries_exceeded",
            return_value=True,
        ):
            assert self.behaviour_class.is_retries_exceeded()
            state = cast(BaseState, self.elcollectooor_abci_behaviour.current_state)
            assert state.state_id == self.behaviour_class.state_id
            # self._test_done_flag_set() # TODO: make this work


class TestDecisionModel:
    def test_static_should_return_1_when_no_royalty_receiver(self):
        """
        Static should return 1, when there is no royalty receiver
        """

        test_project_details = {
            "royalty_receiver": "0x0000000000000000000000000000000000000000",
            "description": "some desc",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)

        assert 1 == static_score

    def test_static_should_return_1_when_empty_desc_and_royalty_receiver(self):
        """
        Static should return 1, when the description is empty
        """
        test_project_details = {
            "royalty_receiver": "0x1000000000000000000010000000000000000001",
            "description": "",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)
        assert static_score == 1

    def test_static_should_return_0_when_empty_desc_and_no_royalty_receiver(self):
        """
        Static should return 1 when there is no royalty receiver, and empty desc
        """
        test_project_details = {
            "royalty_receiver": "0x0000000000000000000000000000000000000000",
            "description": "",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)
        assert static_score == 0

    def test_static_should_return_1_when_nonempty_desc_and_no_royalty_receiver(self):
        """
        Static should return 1 when there is no royalty receiver and the description is not empty.
        """
        test_project_details = {
            "royalty_receiver": "0x0000000000000000000000000000000000000000",
            "description": "Some description.",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)
        assert static_score == 1

    # TODO: if you want, add more tests for static, including "negative" tests cases
    # for example, when the input is not as expected, it's impossible for an app to be over-tested :)

    # TODO: add tests for dynamic part
    def test_dynamic_should_return_1_when_cheap_often_minted_NFT_is_observed(self):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()

        project_hist = []
        for i in range(5):
            project_dict_example = {
                "price_per_token_in_wei": 1,
                "invocations": i,
                "max_invocations": 10,
            }
            project_hist.append(project_dict_example)

        assert model.dynamic(project_hist) == 1

    def test_dynamic_should_return_0_when_NFT_rarely_minted_after_some_time(self):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()

        project_hist = []
        for i in range(1010):
            project_dict_example = {
                "price_per_token_in_wei": 10 ** 19,
                "invocations": 0,
                "max_invocations": 9,
            }
            project_hist.append(project_dict_example)

        assert model.dynamic(project_hist) == 0

    def test_dynamic_should_return_negative_1_when_data_inconclusive(self):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()

        project_dict_example = [
            {"price_per_token_in_wei": 1, "invocations": 2, "max_invocations": 1000}
        ]

        assert model.dynamic(project_dict_example) == -1

    def test_dynamic_should_return_negative_1_when_too_expensive_minted_NFT_is_observed(
        self,
    ):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()
        project_hist = []

        for i in range(5):
            project_dict_example = {
                "price_per_token_in_wei": 1500000000000000000,
                "invocations": i,
                "max_invocations": 10,
            }
            project_hist.append(project_dict_example)

        assert model.dynamic(project_hist) == -1

    def test_dynamic_is_non_dutch(self):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()
        project_hist = []

        for i in range(152):
            project_dict_example = {
                "price_per_token_in_wei": 400000000000000000,
                "invocations": 2 * i,
                "max_invocations": 300,
            }
            project_hist.append(project_dict_example)

        logger = model.logger
        with mock.patch.object(logger, "info") as mock_debug:
            model.dynamic(project_hist)
            mock_debug.assert_called_with("This is no Dutch auction.")
        assert model.dynamic(project_hist) == 1

    def test_dynamic_is_dutch(self):
        """
        Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon.
        """
        model = DecisionModel()
        project_hist = []

        for i in range(102):
            project_dict_example = {
                "price_per_token_in_wei": (1500000000000000000 if i < 101 else 1),
                "invocations": 2 * i,
                "max_invocations": 300,
            }
            project_hist.append(project_dict_example)
        logger = model.logger
        with mock.patch.object(logger, "info") as mock_debug:
            model.dynamic(project_hist)
            mock_debug.assert_called_with(
                "This is a Dutch auction or something very fast."
            )

        assert model.dynamic(project_hist) == 1
