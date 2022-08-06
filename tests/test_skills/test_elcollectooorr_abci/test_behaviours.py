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

"""Tests for valory/elcollectooorr_abci skill's behaviours."""
import json
import logging
from copy import copy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Type, cast
from unittest import mock
from unittest.mock import patch

from aea.helpers.transaction.base import RawTransaction, SignedMessage, State
from aea.test_tools.test_skill import BaseSkillTestCase

from packages.elcollectooorr.contracts.artblocks.contract import ArtBlocksContract
from packages.elcollectooorr.contracts.artblocks_minter_filter.contract import (
    ArtBlocksMinterFilterContract,
)
from packages.elcollectooorr.contracts.artblocks_periphery.contract import (
    ArtBlocksPeripheryContract,
)
from packages.elcollectooorr.contracts.basket_factory.contract import (
    BasketFactoryContract,
)
from packages.elcollectooorr.contracts.token_vault.contract import TokenVaultContract
from packages.elcollectooorr.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.behaviours import (
    DecisionRoundBehaviour,
    DetailsRoundBehaviour,
    ElcollectooorrABCIBaseState,
    FundingRoundBehaviour,
    ObservationRoundBehaviour,
    PayoutFractionsRoundBehaviour,
    PostPayoutRoundBehaviour,
    PostTransactionSettlementBehaviour,
    ProcessPurchaseRoundBehaviour,
    ResyncRoundBehaviour,
    TransactionRoundBehaviour,
    TransferNFTRoundBehaviour,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.decision_models import (
    SimpleDecisionModel as DecisionModel,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.handlers import (
    ContractApiHandler,
    HttpHandler,
    LedgerApiHandler,
    SigningHandler,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.rounds import (
    Event,
    PeriodState,
    PostTransactionSettlementEvent,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.behaviours import (
    DeployDecisionRoundBehaviour,
)
from packages.open_aea.protocols.signing import SigningMessage
from packages.valory.connections.http_client.connection import (
    PUBLIC_ID as HTTP_CLIENT_PUBLIC_ID,
)
from packages.valory.connections.ledger.base import (
    CONNECTION_ID as LEDGER_CONNECTION_PUBLIC_ID,
)
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.contracts.multisend.contract import MultiSendContract
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.protocols.http import HttpMessage
from packages.valory.protocols.ledger_api.message import LedgerApiMessage
from packages.valory.skills.abstract_round_abci.base import AbciAppDB as StateDB
from packages.valory.skills.abstract_round_abci.base import AbstractRound
from packages.valory.skills.abstract_round_abci.base import (
    BaseSynchronizedData as BasePeriodState,
)
from packages.valory.skills.abstract_round_abci.base import (
    BaseTxPayload,
    OK_CODE,
    _MetaPayload,
)
from packages.valory.skills.abstract_round_abci.behaviours import AbstractRoundBehaviour
from packages.valory.skills.abstract_round_abci.behaviours import (
    BaseBehaviour as BaseState,
)
from packages.valory.skills.reset_pause_abci.behaviours import ResetAndPauseBehaviour
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    RandomnessTransactionSubmissionBehaviour,
)

from tests.conftest import ROOT_DIR
from tests.helpers.constants import WEI_TO_ETH


class DummyRoundId:
    """Dummy class for setting round_id for exit condition."""

    round_id: str

    def __init__(self, round_id: str) -> None:
        """Dummy class for setting round_id for exit condition."""
        self.round_id = round_id


class ElCollectooorrFSMBehaviourBaseCase(BaseSkillTestCase):
    """Base case for testing PriceEstimation FSMBehaviour."""

    path_to_skill = Path(
        ROOT_DIR, "packages", "elcollectooorr", "skills", "elcollectooorr_abci"
    )

    elcollectooorr_abci_behaviour: AbstractRoundBehaviour
    ledger_handler: LedgerApiHandler
    http_handler: HttpHandler
    contract_handler: ContractApiHandler
    signing_handler: SigningHandler
    old_tx_type_to_payload_cls: Dict[str, Type[BaseTxPayload]]

    @classmethod
    def setup(cls, **kwargs: Any) -> None:
        """Setup the test class."""
        # we need to store the current value of the meta-class attribute
        # _MetaPayload.transaction_type_to_payload_cls, and restore it
        # in the teardown function. We do a shallow copy so we avoid
        # to modify the old mapping during the execution of the tests.
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
        cls.elcollectooorr_abci_behaviour = cast(
            AbstractRoundBehaviour,
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

        if kwargs.get("param_overrides") is not None:
            for param_name, param_value in kwargs["param_overrides"].items():
                setattr(
                    cls.elcollectooorr_abci_behaviour.context.params,
                    param_name,
                    param_value,
                )

        cls.elcollectooorr_abci_behaviour.setup()
        cls._skill.skill_context.state.setup()
        cls._skill.skill_context.state.round_sequence.end_sync()
        assert (
            cast(
                BaseState, cls.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == cls.elcollectooorr_abci_behaviour.initial_behaviour_cls.behaviour_id
        )

    def fast_forward_to_state(
        self,
        behaviour: AbstractRoundBehaviour,
        state_id: str,
        period_state: BasePeriodState,
    ) -> None:
        """Fast forward the FSM to a state."""
        next_state = {s.behaviour_id: s for s in behaviour.behaviours}[state_id]
        assert next_state is not None, f"State {state_id} not found"
        next_state = cast(Type[BaseState], next_state)
        behaviour.current_behaviour = next_state(
            name=next_state.behaviour_id, skill_context=behaviour.context
        )
        self.skill.skill_context.state.round_sequence.abci_app._round_results.append(
            period_state
        )
        self.skill.skill_context.state.round_sequence.abci_app._extend_previous_rounds_with_current_round()
        self.skill.skill_context.behaviours.main._last_round_height = (
            self.skill.skill_context.state.round_sequence.abci_app.current_round_height
        )
        self.skill.skill_context.state.round_sequence.abci_app._current_round = (
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
        self.elcollectooorr_abci_behaviour.act_wrapper()

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
        self.elcollectooorr_abci_behaviour.act_wrapper()

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
            contract_id="mock_contract_id",
            **response_kwargs,
        )
        self.contract_handler.handle(incoming_message)
        self.elcollectooorr_abci_behaviour.act_wrapper()

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
        self.elcollectooorr_abci_behaviour.act_wrapper()
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
        self.elcollectooorr_abci_behaviour.act_wrapper()

    def mock_signing_request(self, request_kwargs: Dict, response_kwargs: Dict) -> None:
        """Mock signing request."""
        self.assert_quantity_in_decision_making_queue(1)
        actual_signing_message = self.get_message_from_decision_maker_inbox()
        assert actual_signing_message is not None, "No message in outbox."
        has_attributes, error_str = self.message_has_attributes(
            actual_message=actual_signing_message,
            message_type=SigningMessage,
            to=self.skill.skill_context.decision_maker_address,
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
            sender=self.skill.skill_context.decision_maker_address,
            **response_kwargs,
        )
        self.signing_handler.handle(incoming_message)
        self.elcollectooorr_abci_behaviour.act_wrapper()

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
                body=json.dumps({"result": {"hash": "", "code": OK_CODE}}).encode(
                    "utf-8"
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
                body=json.dumps({"result": {"tx_result": {"code": OK_CODE}}}).encode(
                    "utf-8"
                ),
            ),
        )

    def end_round(self, event: Enum = Event.DONE) -> None:
        """Ends round early to cover `wait_for_end` generator."""
        current_state = cast(
            BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
        )
        if current_state is None:
            return
        current_state = cast(BaseState, current_state)
        if current_state.matching_round is None:
            return
        abci_app = current_state.context.state.round_sequence.abci_app
        old_round = abci_app._current_round
        abci_app._last_round = old_round
        abci_app._current_round = abci_app.transition_function[
            current_state.matching_round
        ][event](abci_app.synchronized_data, abci_app.consensus_params)
        abci_app._previous_rounds.append(old_round)
        abci_app._current_round_height += 1
        self.elcollectooorr_abci_behaviour._process_current_round()

    def _test_done_flag_set(self) -> None:
        """Test that, when round ends, the 'done' flag is set."""
        current_state = cast(
            BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
        )
        assert not current_state.is_done()
        with mock.patch.object(
            self.elcollectooorr_abci_behaviour.context.state, "_round_sequence"
        ) as mock_period:
            mock_period.last_round_id = cast(
                AbstractRound, current_state.matching_round
            ).round_id
            current_state.act_wrapper()
            assert current_state.is_done()

    @classmethod
    def teardown(cls) -> None:
        """Teardown the test class."""
        _MetaPayload.transaction_type_to_payload_cls = cls.old_tx_type_to_payload_cls  # type: ignore


class TestObservationRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for the Observation Round Behaviour"""

    behaviour_class = ObservationRoundBehaviour
    next_behaviour_class = DecisionRoundBehaviour

    def test_new_projects_observed(self) -> None:
        """The agent queries the contract and a project has become active."""
        # projects 1 and 2 were previously observed
        finished_projects: List = [1]
        active_projects: List = []
        inactive_projects: List = [2]
        most_recent_project: int = 2

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            finished_projects=finished_projects,
                            active_projects=active_projects,
                            inactive_projects=inactive_projects,
                            most_recent_project=most_recent_project,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            # project 2 gets finished, project 3 is observed
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "results": [
                                {
                                    "project_id": 1,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 100,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 2,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 100,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 3,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": True,
                                },
                            ]
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Most recent project is 3.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 1 newly finished projects.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 1 active projects.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == DetailsRoundBehaviour.behaviour_id

    def test_no_project_was_previously_observed(self) -> None:
        """The agent queries the contract for the first time."""
        # no projects were previously observed
        finished_projects: List = []
        active_projects: List = []
        inactive_projects: List = []
        most_recent_project: int = 0

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            finished_projects=finished_projects,
                            active_projects=active_projects,
                            inactive_projects=inactive_projects,
                            most_recent_project=most_recent_project,
                        ),
                    )
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            # project 2 gets finished, project 3 is observed
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "results": [
                                {
                                    "project_id": 1,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 100,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 2,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 100,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 3,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": True,
                                },
                            ]
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Most recent project is 3.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 2 newly finished projects.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 1 active projects.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == DetailsRoundBehaviour.behaviour_id

    def test_project_becomes_active(self) -> None:
        """The agent queries the contract and a project has become active."""
        # projects 1-6 were previously observed
        finished_projects: List = [1, 2, 3]
        active_projects: List = []
        inactive_projects: List = [4, 5, 6]
        most_recent_project: int = 6

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            finished_projects=finished_projects,
                            active_projects=active_projects,
                            inactive_projects=inactive_projects,
                            most_recent_project=most_recent_project,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            # project 6 becomes active
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "results": [
                                {
                                    "project_id": 6,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": True,
                                }
                            ]
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Most recent project is 6.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 0 newly finished projects.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 1 active projects.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == DetailsRoundBehaviour.behaviour_id

    def test_no_new_projects(self) -> None:
        """The agent queries the contract and nothing has changed."""
        # projects 1-6 were previously observed
        finished_projects: List = [1, 2, 3]
        active_projects: List = []
        inactive_projects: List = [4, 5, 6]
        most_recent_project: int = 6

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            finished_projects=finished_projects,
                            active_projects=active_projects,
                            inactive_projects=inactive_projects,
                            most_recent_project=most_recent_project,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            # project 6 becomes active
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={
                            "results": [
                                {
                                    "project_id": 4,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 5,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": False,
                                },
                                {
                                    "project_id": 6,
                                    "price_per_token_in_wei": 1,
                                    "max_invocations": 100,
                                    "invocations": 99,
                                    "is_active": False,
                                },
                            ]
                        },
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "Most recent project is 6.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 0 newly finished projects.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "There are 0 active projects.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == DetailsRoundBehaviour.behaviour_id

    def test_bad_response(self) -> None:
        """The agent queries the contract and nothing has changed."""
        # projects 1-6 were previously observed
        finished_projects: List = [1, 2, 3]
        active_projects: List = []
        inactive_projects: List = [4, 5, 6]
        most_recent_project: int = 6

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            finished_projects=finished_projects,
                            active_projects=active_projects,
                            inactive_projects=inactive_projects,
                            most_recent_project=most_recent_project,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body={}),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't get the projects, the following error was encountered AEAEnforceError: "
                "response, response.state, response.state.body must exist",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()

        self.end_round()

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == DetailsRoundBehaviour.behaviour_id


class TestDetailsRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for details round behaviour"""

    behaviour_class = DetailsRoundBehaviour
    next_behaviour_class = DecisionRoundBehaviour

    def test_details_happy_path(self) -> None:
        """The agent fetches details of 3 projects."""
        active_projects = [
            {
                "project_id": 1,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 2,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 3,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            active_projects=active_projects,
                        ),
                    )
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        http_response = {
            "data": {
                "projects": [
                    {"projectId": "1"},
                    {"projectId": "2"},
                    {"projectId": "3"},
                ]
            }
        }
        query = '{projects(where:{curationStatus:"curated"}){projectId}}'

        self.mock_http_request(
            request_kwargs=dict(
                method="POST",
                headers="",
                version="",
                body=json.dumps({"query": query}).encode(),
                url="https://api.thegraph.com/subgraphs/name/artblocks/art-blocks",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=json.dumps(http_response).encode(),
            ),
        )

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksMinterFilterContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x4aafce293b9b0fad169c78049a81e400f518e199",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    ledger_id="ethereum",
                    body={  # type: ignore
                        1: {  # type: ignore
                            "minter_for_project": "0x1",
                        },
                        2: {  # type: ignore
                            "minter_for_project": "0x2",
                        },
                        3: {  # type: ignore
                            "minter_for_project": "0x",  # no minter assigned
                        },
                    },
                ),
            ),
        )

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    ledger_id="ethereum",
                    body={  # type: ignore
                        1: {  # type: ignore
                            "is_mintable_via_contract": True,
                            "price_per_token_in_wei": 1,
                            "is_price_configured": True,
                            "currency_symbol": "ETH",
                            "currency_address": "0x0000000000000000000000000000000000000000",
                        },
                    },
                ),
            ),
        )

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x2",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    ledger_id="ethereum",
                    body={  # type: ignore
                        2: {  # type: ignore
                            "is_mintable_via_contract": True,
                            "price_per_token_in_wei": 1,
                            "is_price_configured": True,
                            "currency_symbol": "ETH",
                            "currency_address": "0x0000000000000000000000000000000000000000",
                        },
                    },
                ),
            ),
        )
        # test passes if no exception is thrown

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_bad_response_graph(self) -> None:
        """Bad response from the graph."""
        active_projects = [
            {
                "project_id": 1,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 2,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 3,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            active_projects=active_projects,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            query = '{projects(where:{curationStatus:"curated"}){projectId}}'
            http_response = {
                "data": {
                    "projects": [
                        {"projectId": "1"},
                        {"projectId": "2"},
                        {"projectId": "3"},
                    ]
                }
            }

            self.mock_http_request(
                request_kwargs=dict(
                    method="POST",
                    headers="",
                    version="",
                    body=json.dumps({"query": query}).encode(),
                    url="https://api.thegraph.com/subgraphs/name/artblocks/art-blocks",
                ),
                response_kwargs=dict(
                    version="",
                    status_code=500,
                    status_text="",
                    headers="",
                    body=json.dumps(http_response).encode(),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't get projects details, the following error was encountered "
                "AEAEnforceError: Bad response from the graph api.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_bad_response_contract(self) -> None:
        """Bad response from the contract."""
        active_projects = [
            {
                "project_id": 1,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 2,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
            {
                "project_id": 3,
                "price_per_token_in_wei": 1,
                "max_invocations": 100,
                "invocations": 99,
                "is_active": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            active_projects=active_projects,
                        ),
                    )
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            http_response = {
                "data": {
                    "projects": [
                        {"projectId": "1"},
                        {"projectId": "2"},
                        {"projectId": "3"},
                    ]
                }
            }
            query = '{projects(where:{curationStatus:"curated"}){projectId}}'

            self.mock_http_request(
                request_kwargs=dict(
                    method="POST",
                    headers="",
                    version="",
                    body=json.dumps({"query": query}).encode(),
                    url="https://api.thegraph.com/subgraphs/name/artblocks/art-blocks",
                ),
                response_kwargs=dict(
                    version="",
                    status_code=200,
                    status_text="",
                    headers="",
                    body=json.dumps(http_response).encode(),
                ),
            )

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksMinterFilterContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x4aafce293b9b0fad169c78049a81e400f518e199",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={},
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't get projects details, the following error was encountered "
                "AEAEnforceError: Invalid response was received from 'get_multiple_projects_minter'.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id


class TestDecisionRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Decision Round Behaviour"""

    behaviour_class = DecisionRoundBehaviour
    decided_yes_behaviour_class = TransactionRoundBehaviour
    decided_no_behaviour_class = ResetAndPauseBehaviour
    gib_details_behaviour_class = DetailsRoundBehaviour

    def test_decided_yes(self) -> None:
        """The agent evaluated the project and decides to purchase"""
        active_projects = [
            {
                "project_id": 1,
                "price": 1,
                "minted_percentage": 0.99,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 2,
                "price": 1,
                "minted_percentage": 0.98,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 3,
                "price": 1,
                "minted_percentage": 0.97,
                "is_active": True,
                "is_curated": True,
                "currency_symbol": "ETH",
                "is_mintable_via_contract": True,
                "minter": "0x0",
                "is_price_configured": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            safe_contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
                            active_projects=active_projects,
                            purchased_projects=[active_projects[-1]],
                            amount_spent=WEI_TO_ETH,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={"balance": 2 * WEI_TO_ETH},
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "The safe contract balance is 2.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "Already spent 1.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "The current budget is 2.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "2 projects fit the reqs.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_YES)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_behaviour_class.behaviour_id

    def test_decided_no(self) -> None:
        """The agent evaluated the project and decided for NO"""

        active_projects = [
            {
                "project_id": 1,
                "price": 1,
                "minted_percentage": 0.99,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 2,
                "price": 1,
                "minted_percentage": 0.98,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 3,
                "price": 1,
                "minted_percentage": 0.97,
                "is_active": True,
                "is_curated": True,
                "currency_symbol": "ETH",
                "is_mintable_via_contract": True,
                "minter": "0x0",
                "is_price_configured": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            safe_contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
                            active_projects=active_projects,
                            purchased_projects=active_projects,
                            amount_spent=WEI_TO_ETH,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={"balance": 2 * WEI_TO_ETH},
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "The safe contract balance is 2.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "Already spent 1.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "The current budget is 2.0Ξ.",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "0 projects fit the reqs.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_no_behaviour_class.behaviour_id

    def test_decided_gib_details(self) -> None:
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
        test_details: List[Dict] = [{}]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            most_voted_project=json.dumps(test_project),
                            most_voted_details=json.dumps(test_details),
                        ),
                    ),
                ),
            ),
        )

        self.end_round(event=Event.GIB_DETAILS)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)

        assert state.behaviour_id == self.gib_details_behaviour_class.behaviour_id

    def test_bad_response(self) -> None:
        """The agent receives a bad response from the contract."""
        active_projects = [
            {
                "project_id": 1,
                "price": 1,
                "minted_percentage": 0.99,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 2,
                "price": 1,
                "minted_percentage": 0.98,
                "is_active": True,
                "is_curated": True,
                "is_mintable_via_contract": True,
                "currency_symbol": "ETH",
                "minter": "0x0",
                "is_price_configured": True,
            },
            {
                "project_id": 3,
                "price": 1,
                "minted_percentage": 0.97,
                "is_active": True,
                "is_curated": True,
                "currency_symbol": "ETH",
                "is_mintable_via_contract": True,
                "minter": "0x0",
                "is_price_configured": True,
            },
        ]

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            safe_contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
                            active_projects=active_projects,
                            purchased_projects=[active_projects[-1]],
                            amount_spent=WEI_TO_ETH,
                        )
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body={"bad_balance": 2 * WEI_TO_ETH},
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't make a decision, the following error was encountered "
                "AEAEnforceError: response, response.state, response.state.body must exist.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_YES)
        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_behaviour_class.behaviour_id


class TestTransactionRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Transaction Round Behaviour"""

    behaviour_class = TransactionRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent gathers the necessary data to make the purchase,makes a contract requests and receives valid data"""

        test_project = {
            "project_id": 3,
            "price": 1,
            "minted_percentage": 0.97,
            "is_active": True,
            "is_curated": True,
            "is_mintable": True,
            "minter": "0x1",
        }

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "project_to_purchase": test_project,
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "most_voted_details": json.dumps(
                                [{"price_per_token_in_wei": 123}]
                            ),
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksPeripheryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1",
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

        self.mock_contract_api_request(
            contract_id=str(GnosisSafeContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A3",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={"tx_hash": "0x" + "0" * 64},
                    ledger_id="ethereum",
                ),
            ),
        )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent gathers the necessary data to make the purchase,makes a contract requests and receives valid data"""

        test_project = {
            "project_id": 3,
            "price": 1,
            "minted_percentage": 0.97,
            "is_active": True,
            "is_curated": True,
            "is_mintable": True,
            "minter": "0x1",
        }

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "project_to_purchase": test_project,
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "most_voted_details": json.dumps(
                                [{"price_per_token_in_wei": 123}]
                            ),
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )
        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksPeripheryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1",
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

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={"bad_tx_hash": "0x" + "0" * 64},
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create transaction payload, the following error was encountered "
                "AEAEnforceError: contract returned and empty body or empty tx_hash.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == ObservationRoundBehaviour.behaviour_id


class TestFundingRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Funding Round Behaviour"""

    behaviour_class = FundingRoundBehaviour
    next_behaviour_class = PayoutFractionsRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent gets the ingoing transfers."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={
                            "data": [
                                {
                                    "sender": "0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0",
                                    "amount": 1,
                                    "blockNumber": 1,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": 2,
                                    "blockNumber": 2,
                                },
                            ]
                        },
                        ledger_id="ethereum",
                    ),
                ),
            )

            elcol_state = cast(
                ElcollectooorrABCIBaseState,
                self.elcollectooorr_abci_behaviour.current_behaviour,
            )
            if elcol_state.params.enforce_investor_whitelisting:
                mock_logger.assert_any_call(
                    logging.INFO,
                    "1 transfers from whitelisted investors.",
                )
                mock_logger.assert_any_call(
                    logging.INFO,
                    "1 transfers from non-whitelisted investors.",
                )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent can't get the ingoing transfers."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )
        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={"bad_tx_hash": "0x" + "0" * 64},
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't get transfers to the safe contract, "
                "the following error was encountered AEAEnforceError: contract returned and empty body or empty data.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id


class TestPayoutFractionsRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Payout Fractions Round Behaviour"""

    behaviour_class = PayoutFractionsRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour
    no_payouts_next_behaviour = ObservationRoundBehaviour
    fraction_price = 10500000000000000

    def _mock_available_tokens(
        self, address: str = "0x0", balance: int = 1000, bad_response: bool = False
    ) -> None:
        """Mock the response of the TokenVault when calling get_balance."""
        body = dict(balance=balance) if not bad_response else {}

        self.mock_contract_api_request(
            contract_id=str(TokenVaultContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=address,
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body=body,  # type: ignore
                    ledger_id="ethereum",
                ),
            ),
        )

    def _mock_multisend_tx(
        self,
        address: str = "0xA238CBeb142c10Ef7Ad8442C6D1f9E89e07e7761",
        bad_response: bool = False,
    ) -> None:
        """Mock the response of the Multisend Address."""

        body = dict(data=b"multisend_data".hex()) if not bad_response else dict()

        self.mock_contract_api_request(
            contract_id=str(MultiSendContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_RAW_TRANSACTION,
                contract_address=address,
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.RAW_TRANSACTION,
                raw_transaction=RawTransaction(
                    body=body,  # type: ignore
                    ledger_id="ethereum",
                ),
            ),
        )

    def _mock_transferERC20_tx(
        self, address: str = "0x0", bad_response: bool = False
    ) -> None:
        """Mock the ERC20 transfer tx."""
        body = {"data": b"erc20_tx"} if not bad_response else {}

        self.mock_contract_api_request(
            contract_id=str(TokenVaultContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=address,
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body=body,  # type: ignore
                    ledger_id="ethereum",
                ),
            ),
        )

    def _mock_tx_hash(self, address: str = "0x0") -> None:
        """Mock the response of the gnosis safe contract."""
        self.mock_contract_api_request(
            contract_id=str(GnosisSafeContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=address,
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={"tx_hash": "0x" + "0" * 64},
                    ledger_id="ethereum",
                ),
            ),
        )

    def test_the_happy_path(self) -> None:
        """There is an address waiting to be paid, the agent prepares a tx to pay to it."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": WEI_TO_ETH,  # 1ETH
                                    "blockNumber": 0,
                                }
                            ],
                        },
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens()
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(
                logging.INFO,
                "1 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_two_users_get_paid(self) -> None:
        """Two users need to get paid."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": WEI_TO_ETH,  # 1ETH
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": WEI_TO_ETH,  # 1ETH
                                    "blockNumber": 0,
                                },
                            ],
                        },
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens()
            self._mock_transferERC20_tx()
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(
                logging.INFO,
                "2 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_no_users_get_paid(self) -> None:
        """No users need to get paid."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": 0,  # assume 0 ETH transfers
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": 0,  # assume 0 ETH transfers
                                    "blockNumber": 0,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()
        self._mock_available_tokens()

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_no_investments(self) -> None:
        """No users need to get paid."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()
        self._mock_available_tokens()

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.NO_PAYOUTS)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.no_payouts_next_behaviour.behaviour_id

    def test_a_user_invests_twice(self) -> None:
        """A user has invested once before, but needs to get paid for the new investment."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {
                                "0x0": 1
                            },  # address 0x0 has been paid 1, 10 more need to be paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": self.fraction_price,
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x0",
                                    "amount": 10 * self.fraction_price,
                                    "blockNumber": 10,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens()
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(
                logging.INFO,
                "1 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_a_user_invests_twice_consecutively(self) -> None:
        """A user has invested twice."""
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {
                                "0x0": 0
                            },  # address 0x0 has been paid 1, 10 more need to be paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": self.fraction_price,
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x0",
                                    "amount": 10 * self.fraction_price,
                                    "blockNumber": 10,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens()
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(
                logging.INFO,
                "1 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_not_enough_tokens_for_two_users(self) -> None:
        """
        Two users are owned 10 tokens each, there are only 10 tokens available, only one of the users should get them.

        NOTE: The other user will get their share once the next vault has been created.
        """

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": 10
                                    * self.fraction_price,  # the first user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": 10
                                    * self.fraction_price,  # the second  user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens(balance=10)
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(logging.WARNING, "No more tokens left!")

            mock_logger.assert_any_call(
                logging.INFO,
                "1 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_not_enough_tokens_to_fully_pay_two_users(self) -> None:
        """
        Two users are owned 10 tokens each, there are only 19 tokens available, one will get 10, the other 9.

        NOTE: The user owned 1 token will get that token once a new vault has been deployed.
        """

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": 10
                                    * self.fraction_price,  # the first user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": 10
                                    * self.fraction_price,  # the second  user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens(balance=19)
            self._mock_transferERC20_tx()
            self._mock_transferERC20_tx()
            self._mock_multisend_tx()
            self._mock_tx_hash()

            mock_logger.assert_any_call(
                logging.WARNING,
                "Not enough funds to payout all the owned tokens, they will be paid when the next vault is created!",
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "2 user(s) is(are) getting paid their fractions.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_bad_contract_response(self) -> None:
        """A contract returns a bad response."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "most_voted_funds": [
                                {
                                    "sender": "0x0",
                                    "amount": 10
                                    * self.fraction_price,  # the first user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                                {
                                    "sender": "0x1",
                                    "amount": 10
                                    * self.fraction_price,  # the second  user has paid for 10 tokens
                                    "blockNumber": 0,
                                },
                            ],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self._mock_available_tokens(bad_response=True)
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create PayoutFractions payload, the following error was encountered "
                "AEAEnforceError: Could not retrieve the token balance of the safe contract.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.NO_PAYOUTS)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.no_payouts_next_behaviour.behaviour_id


class TestPostPayoutRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Payout Fractions Round Behaviour"""

    behaviour_class = PostPayoutRoundBehaviour
    next_behaviour_class = ObservationRoundBehaviour

    def test_the_happy_path(self) -> None:
        """The users that got paid get logged."""
        users_being_paid = {
            "0x0": 1,
            "0x1": 1,
        }
        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "vault_addresses": ["0x0"],
                            "paid_users": {},  # no user has yet been paid
                            "users_being_paid": users_being_paid,
                        },
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            mock_logger.assert_any_call(
                logging.INFO,
                f"The following users were paid: {users_being_paid}",
            )

        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id


class TestProcessPurchaseRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Payout Fractions Round Behaviour"""

    behaviour_class = ProcessPurchaseRoundBehaviour
    next_behaviour_class = TransferNFTRoundBehaviour
    failed_next_behaviour = ObservationRoundBehaviour

    def test_the_happy_path(self) -> None:
        """A token has been purchased, the agent extracts the data from the tx hash."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "final_tx_hash": "0x0",
                        },
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body=dict(token_id=1)),
                ),
            )
            mock_logger.assert_any_call(
                logging.INFO,
                "Purchased token id=1.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_contract_returns_bad_response(self) -> None:
        """The contract returns a bad response."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "final_tx_hash": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body=dict(bad_token_id=1)),
                ),
            )
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create PurchasedNFTPayload payload, "
                "the following error was encountered AEAEnforceError: Couldn't get token_id from the purchase tx hash.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.failed_next_behaviour.behaviour_id


class TestTransferNFTRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for Payout Fractions Round Behaviour"""

    behaviour_class = TransferNFTRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour
    no_transfer = ResetAndPauseBehaviour

    def test_the_happy_path(self) -> None:
        """A token has been purchased, the agent transfers it to the safe contract."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "basket_addresses": ["0x1"],
                            "purchased_nft": 1,
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        self.elcollectooorr_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(ArtBlocksContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(data=b"123".hex())),
            ),
        )

        self.mock_contract_api_request(
            contract_id=str(GnosisSafeContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x0",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={"tx_hash": "0x" + "0" * 64},
                    ledger_id="ethereum",
                ),
            ),
        )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_contract_returns_bad_response(self) -> None:
        """The contract returns a bad response."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "basket_addresses": ["0x1"],
                            "purchased_nft": 1,
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(ArtBlocksContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body=dict(data=b"123".hex())),
                ),
            )

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x0",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={"bad_tx_hash": "0x" + "0" * 64},
                        ledger_id="ethereum",
                    ),
                ),
            )
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create TransferNFT payload, "
                "the following error was encountered AEAEnforceError: contract returned and empty body or empty tx_hash.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.NO_TRANSFER)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.no_transfer.behaviour_id

    def test_the_token_id_is_none(self) -> None:
        """The token_id is none."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                            "basket_addresses": ["0x1"],
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create TransferNFT payload, "
                "the following error was encountered AEAEnforceError: No token to be transferred.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.NO_TRANSFER)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.no_transfer.behaviour_id


class TestPostTransactionSettlementBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for PostTransactionSettlemenBehaviour"""

    behaviour_class = PostTransactionSettlementBehaviour
    next_behaviour_class = ProcessPurchaseRoundBehaviour
    error_next_behaviour_class = RandomnessTransactionSubmissionBehaviour

    def test_the_happy_path(self) -> None:
        """A tx with value 1ETH was settled."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "final_tx_hash": "0x0",
                            "tx_submitter": "elcollectooorr_transaction_collection",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x0000000000000000000000000000000000000000",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body=dict(amount_spent=WEI_TO_ETH),
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO,
                "The TX submitted by elcollectooorr_transaction_collection was settled.",
            )

            mock_logger.assert_any_call(logging.INFO, "The settled tx cost: 1.0Ξ.")

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_contract_returns_bad_response(self) -> None:
        """The contract returns a bad response."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "final_tx_hash": "0x0",
                            "tx_submitter": "elcollectooorr_transaction_collection",
                        },
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x0000000000000000000000000000000000000000",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body=dict(bad_amount_spent=WEI_TO_ETH),
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create the PostTransactionSettlement payload, the following error was encountered "
                "AEAEnforceError: response, response.state, response.state.body must exist.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.error_next_behaviour_class.behaviour_id

    def test_the_the_tx_submitter_is_missing(self) -> None:
        """A token with value 1ETH was settled, but the tx_submitter is missing."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "final_tx_hash": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x0000000000000000000000000000000000000000",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body=dict(amount_spent=WEI_TO_ETH),
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "A TX was settled, but the `tx_submitter` is unavailable!",
            )

            mock_logger.assert_any_call(logging.INFO, "The settled tx cost: 1.0Ξ.")

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id


class TestResyncRoundBehaviour(ElCollectooorrFSMBehaviourBaseCase):
    """Tests for TestResyncRoundBehaviour"""

    behaviour_class = ResyncRoundBehaviour
    next_behaviour_class = DeployDecisionRoundBehaviour

    def _mock_safe_tx(self, txs: List[Dict]) -> None:
        """Mocks the response of 'get_safe_txs'"""
        self.mock_contract_api_request(
            contract_id=str(GnosisSafeContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x0",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(txs=txs)),
            ),
        )

    def _mock_all_mints(self, mints: List[Dict]) -> None:
        """Mocks the response of 'get_mints'"""
        self.mock_contract_api_request(
            contract_id=str(ArtBlocksContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(mints=mints)),
            ),
        )

    def _mock_amount_spent(self, amount_spent: int) -> None:
        """Mocks the response of 'get_amount_spent'"""
        self.mock_contract_api_request(
            contract_id=str(GnosisSafeContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x0000000000000000000000000000000000000000",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(amount_spent=amount_spent)),
            ),
        )

    def _mock_deployed_baskets(self, baskets: List[Dict]) -> None:
        """Mocks the response of 'get_deployed_baskets'"""
        self.mock_contract_api_request(
            contract_id=str(BasketFactoryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(baskets=baskets)),
            ),
        )

    def _mock_deployed_vaults(self, vaults: List[str]) -> None:
        """Mocks the response of 'get_deployed_vaults'"""
        self.mock_contract_api_request(
            contract_id=str(TokenVaultFactoryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(ledger_id="ethereum", body=dict(vaults=vaults)),
            ),
        )

    def _mock_get_payouts(
        self, vault_address: str, address_to_fractions: List[Dict]
    ) -> None:
        """Mocks the response of 'get_all_erc20_transfers'"""
        self.mock_contract_api_request(
            contract_id=str(TokenVaultContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address=vault_address,
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    ledger_id="ethereum", body=dict(payouts=address_to_fractions)
                ),
            ),
        )

    def _mock_curated_projects(self, projects: List[int]) -> None:
        """Mocks the response of the artblocks api."""

        http_response = {
            "data": {"projects": [{"projectId": str(project)} for project in projects]}
        }
        query = '{projects(where:{curationStatus:"curated"}){projectId}}'

        self.mock_http_request(
            request_kwargs=dict(
                method="POST",
                headers="",
                version="",
                body=json.dumps({"query": query}).encode(),
                url="https://api.thegraph.com/subgraphs/name/artblocks/art-blocks",
            ),
            response_kwargs=dict(
                version="",
                status_code=200,
                status_text="",
                headers="",
                body=json.dumps(http_response).encode(),
            ),
        )

    def test_the_happy_path(self) -> None:
        """The service was restarted with no vaults deployed."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            txs = [
                dict(tx_hash="0x0", block_number=0),
                dict(tx_hash="0x0", block_number=1),
                dict(tx_hash="0x0", block_number=2),
            ]
            self._mock_safe_tx(txs=txs)

            mints = [
                dict(token_id=0, project_id=0),
                dict(token_id=1, project_id=1),
                dict(token_id=2, project_id=2),
            ]
            self._mock_all_mints(mints)
            self._mock_curated_projects([0, 1, 2])

            baskets = [
                dict(basket_address="0x0", block_number=0),
                dict(basket_address="0x1", block_number=1),
                dict(basket_address="0x2", block_number=2),
            ]
            self._mock_deployed_baskets(baskets)

            for basket in baskets:
                self._mock_deployed_vaults([str(basket["basket_address"])])

            vaults = ["0x0", "0x1", "0x2"]
            for vault in vaults:
                self._mock_get_payouts(vault, [dict(value=1, to=vault)])

            self._mock_amount_spent(10)
            mock_logger.assert_any_call(logging.INFO, f"found safe txs: {txs}")
            mock_logger.assert_any_call(
                logging.INFO, "earliest tx block num: 0; latest tx block num: 2"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"already purchased projects: {[0, 1, 2]}"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"all deployed baskets: {['0x0', '0x1', '0x2']}"
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed basket: 0x2")
            mock_logger.assert_any_call(
                logging.INFO, f"all deployed vaults: {['0x0', '0x1', '0x2']}"
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed vault: 0x2")

            address_to_fractions = {
                "0x0": 1,
                "0x1": 1,
                "0x2": 1,
            }
            mock_logger.assert_any_call(
                logging.INFO,
                f"address to fraction amount already paid out: {address_to_fractions}",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                f"amount spent since last basket was deployed: {10 / WEI_TO_ETH}Ξ",
            )
            mock_logger.assert_any_call(
                logging.INFO, f"txs since the deployment of the last basket: {['0x0']}"
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_bad_response(self) -> None:
        """The service was restarted with no vaults deployed."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(GnosisSafeContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x0",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(ledger_id="ethereum", body=dict(bad_res=[])),
                ),
            )
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't resync, the following error was encountered AEAEnforceError: "
                "response, response.state, response.state.body must exist",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_more_than_1_vault_per_basket(self) -> None:
        """More than 1 vault is present per basket."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            txs = [
                dict(tx_hash="0x0", block_number=0),
                dict(tx_hash="0x0", block_number=1),
                dict(tx_hash="0x0", block_number=2),
            ]
            self._mock_safe_tx(txs=txs)

            mints = [
                dict(token_id=0, project_id=0),
                dict(token_id=1, project_id=1),
                dict(token_id=2, project_id=2),
            ]
            self._mock_all_mints(mints)
            self._mock_curated_projects([0, 1, 2])

            baskets = [
                dict(basket_address="0x0", block_number=0),
                dict(basket_address="0x1", block_number=1),
                dict(basket_address="0x2", block_number=2),
            ]
            self._mock_deployed_baskets(baskets)

            for basket in baskets:
                self._mock_deployed_vaults(
                    [str(basket["basket_address"]), str(basket["basket_address"])]
                )

            vaults = ["0x0", "0x1", "0x2"]
            for vault in vaults:
                self._mock_get_payouts(vault, [dict(value=1, to=vault)])
                self._mock_get_payouts(vault, [dict(value=1, to=vault)])

            self._mock_amount_spent(10)
            mock_logger.assert_any_call(logging.INFO, f"found safe txs: {txs}")
            mock_logger.assert_any_call(
                logging.INFO, "earliest tx block num: 0; latest tx block num: 2"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"already purchased projects: {[0, 1, 2]}"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"all deployed baskets: {['0x0', '0x1', '0x2']}"
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed basket: 0x2")
            mock_logger.assert_any_call(
                logging.INFO,
                f"all deployed vaults: {['0x0', '0x0', '0x1', '0x1', '0x2', '0x2']}",
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed vault: 0x2")

            address_to_fractions = {
                "0x0": 2,
                "0x1": 2,
                "0x2": 2,
            }
            mock_logger.assert_any_call(
                logging.INFO,
                f"address to fraction amount already paid out: {address_to_fractions}",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                f"amount spent since last basket was deployed: {10 / WEI_TO_ETH}Ξ",
            )
            mock_logger.assert_any_call(
                logging.INFO, f"txs since the deployment of the last basket: {['0x0']}"
            )
            mock_logger.assert_any_call(
                logging.WARN, "basket 0x0 is associated with 2 vaults"
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id

    def test_basket_without_vault(self) -> None:
        """A basket doesn't have a vault associated with it."""

        self.fast_forward_to_state(
            self.elcollectooorr_abci_behaviour,
            self.behaviour_class.behaviour_id,
            PeriodState(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x0",
                        },
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.elcollectooorr_abci_behaviour.current_behaviour
            ).behaviour_id
            == self.behaviour_class.behaviour_id
        )

        with patch.object(
            self.elcollectooorr_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.elcollectooorr_abci_behaviour.act_wrapper()
            txs = [
                dict(tx_hash="0x0", block_number=0),
                dict(tx_hash="0x0", block_number=1),
                dict(tx_hash="0x0", block_number=2),
            ]
            self._mock_safe_tx(txs=txs)

            mints = [
                dict(token_id=0, project_id=0),
                dict(token_id=1, project_id=1),
                dict(token_id=2, project_id=2),
            ]
            self._mock_all_mints(mints)
            self._mock_curated_projects([0, 1, 2])

            baskets = [
                dict(basket_address="0x0", block_number=0),
                dict(basket_address="0x1", block_number=1),
                dict(basket_address="0x2", block_number=2),
            ]
            self._mock_deployed_baskets(baskets)

            for basket in baskets[:-1]:
                self._mock_deployed_vaults([str(basket["basket_address"])])
            self._mock_deployed_vaults([])

            vaults = ["0x0", "0x1"]
            for vault in vaults:
                self._mock_get_payouts(vault, [dict(value=1, to=vault)])

            self._mock_amount_spent(10)
            mock_logger.assert_any_call(logging.INFO, f"found safe txs: {txs}")
            mock_logger.assert_any_call(
                logging.INFO, "earliest tx block num: 0; latest tx block num: 2"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"already purchased projects: {[0, 1, 2]}"
            )
            mock_logger.assert_any_call(
                logging.INFO, f"all deployed baskets: {['0x0', '0x1', '0x2']}"
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed basket: 0x2")
            mock_logger.assert_any_call(
                logging.INFO, f"all deployed vaults: {['0x0', '0x1']}"
            )
            mock_logger.assert_any_call(logging.INFO, "latest deployed vault: 0x1")

            address_to_fractions = {
                "0x0": 1,
                "0x1": 1,
            }
            mock_logger.assert_any_call(
                logging.INFO,
                f"address to fraction amount already paid out: {address_to_fractions}",
            )
            mock_logger.assert_any_call(
                logging.INFO,
                f"amount spent since last basket was deployed: {10 / WEI_TO_ETH}Ξ",
            )
            mock_logger.assert_any_call(
                logging.INFO, f"txs since the deployment of the last basket: {['0x0']}"
            )
            mock_logger.assert_any_call(
                logging.WARN,
                "basket 0x2 is not associated with any vault.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(BaseState, self.elcollectooorr_abci_behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.behaviour_id


class TestDecisionModel:
    """Tests for the Decision Model"""

    def test_static_should_return_1_when_no_royalty_receiver(self) -> None:
        """Static should return 1, when there is no royalty receiver"""

        test_project_details = {
            "royalty_receiver": "0x0000000000000000000000000000000000000000",
            "description": "some desc",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)

        assert 1 == static_score

    def test_static_should_return_1_when_empty_desc_and_royalty_receiver(self) -> None:
        """Static should return 1, when the description is empty"""

        test_project_details = {
            "royalty_receiver": "0x1000000000000000000010000000000000000001",
            "description": "",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)
        assert static_score == 1

    def test_static_should_return_0_when_empty_desc_and_no_royalty_receiver(
        self,
    ) -> None:
        """Static should return 1 when there is no royalty receiver, and empty desc"""

        test_project_details = {
            "royalty_receiver": "0x0000000000000000000000000000000000000000",
            "description": "",
        }
        model = DecisionModel()
        static_score = model.static(test_project_details)
        assert static_score == 0

    def test_static_should_return_1_when_nonempty_desc_and_no_royalty_receiver(
        self,
    ) -> None:
        """Static should return 1 when there is no royalty receiver and the description is not empty."""

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
    def test_dynamic_should_return_1_when_cheap_often_minted_NFT_is_observed(
        self,
    ) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""

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

    def test_dynamic_should_return_0_when_NFT_rarely_minted_after_some_time(
        self,
    ) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""
        model = DecisionModel()

        project_hist = []
        for _ in range(1010):
            project_dict_example = {
                "price_per_token_in_wei": 10 ** 19,
                "invocations": 0,
                "max_invocations": 9,
            }
            project_hist.append(project_dict_example)

        assert model.dynamic(project_hist) == 0

    def test_dynamic_should_return_negative_1_when_data_inconclusive(self) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""
        model = DecisionModel()

        project_dict_example = [
            {"price_per_token_in_wei": 1, "invocations": 2, "max_invocations": 1000}
        ]

        assert model.dynamic(project_dict_example) == -1

    def test_dynamic_should_return_negative_1_when_too_expensive_minted_NFT_is_observed(
        self,
    ) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""
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

    def test_dynamic_is_non_dutch(self) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""
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

    def test_dynamic_is_dutch(self) -> None:
        """Dynamic should return 1 when there is a well-bought project with a low price and it is expected that it is completely sold soon."""
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
