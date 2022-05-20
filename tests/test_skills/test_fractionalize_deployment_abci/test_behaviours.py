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

"""Tests for valory/fractionalize_deployment_abci skill's behaviours."""
import json
import logging
from copy import copy
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Type, cast
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
from packages.valory.contracts.basket.contract import BasketContract
from packages.valory.contracts.basket_factory.contract import BasketFactoryContract
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.contracts.token_vault.contract import TokenVaultContract
from packages.valory.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
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
from packages.valory.skills.abstract_round_abci.behaviours import (
    AbstractRoundBehaviour,
    BaseState,
)
from packages.valory.skills.elcollectooorr_abci.behaviours import FundingRoundBehaviour
from packages.valory.skills.elcollectooorr_abci.handlers import (
    ContractApiHandler,
    HttpHandler,
    LedgerApiHandler,
    SigningHandler,
)
from packages.valory.skills.elcollectooorr_abci.rounds import PeriodState
from packages.valory.skills.fractionalize_deployment_abci.behaviours import (
    BasketAddressesRoundBehaviour,
    DeployBasketTxRoundBehaviour,
    DeployDecisionRoundBehaviour,
    DeployTokenVaultTxRoundBehaviour,
    PermissionVaultFactoryRoundBehaviour,
    VaultAddressesRoundBehaviour,
)
from packages.valory.skills.fractionalize_deployment_abci.rounds import Event
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    RandomnessTransactionSubmissionBehaviour,
)

from tests.conftest import ROOT_DIR


class DummyRoundId:
    """Dummy class for setting round_id for exit condition."""

    round_id: str

    def __init__(self, round_id: str) -> None:
        """Dummy class for setting round_id for exit condition."""
        self.round_id = round_id


class FractionalizeFSMBehaviourBaseCase(BaseSkillTestCase):
    """Base case for testing Fractionalize FSMBehaviour."""

    path_to_skill = Path(
        ROOT_DIR, "packages", "valory", "skills", "elcollectooorr_abci"
    )

    fractionalize_deployment_abci_behaviour: AbstractRoundBehaviour
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
        cls.fractionalize_deployment_abci_behaviour = cast(
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
                    cls.fractionalize_deployment_abci_behaviour.context.params,
                    param_name,
                    param_value,
                )

        cls.fractionalize_deployment_abci_behaviour.setup()
        cls._skill.skill_context.state.setup()
        cls._skill.skill_context.state.period.end_sync()
        assert (
            cast(
                BaseState, cls.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == cls.fractionalize_deployment_abci_behaviour.initial_state_cls.state_id
        )

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
        self.skill.skill_context.state.period.abci_app._extend_previous_rounds_with_current_round()
        self.skill.skill_context.behaviours.main._last_round_height = (
            self.skill.skill_context.state.period.abci_app.current_round_height
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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()

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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()

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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()

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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()
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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()

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
        self.fractionalize_deployment_abci_behaviour.act_wrapper()

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
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
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
        abci_app._current_round_height += 1
        self.fractionalize_deployment_abci_behaviour._process_current_round()

    def _test_done_flag_set(self) -> None:
        """Test that, when round ends, the 'done' flag is set."""
        current_state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert not current_state.is_done()
        with mock.patch.object(
            self.fractionalize_deployment_abci_behaviour.context.state, "_period"
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


class TestDeployDecisionRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for the Deploy Decision Round Behaviour"""

    behaviour_class = DeployDecisionRoundBehaviour
    decided_yes_class = DeployBasketTxRoundBehaviour
    decided_no_class = FundingRoundBehaviour

    def test_no_vault_was_previously_deployed(self) -> None:
        """No vault was previously deployed, new one needs to be deployed."""
        amount_spent: int = 0

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        amount_spent=amount_spent,
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? True."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_yes_class.state_id

    def test_over_the_budget(self) -> None:
        """We are over the budget for the current vault, we need to deploy a new one."""
        amount_spent: int = int(10.4 * (10 ** 18))

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        vault_addresses=["0x0"],  # a vault exists
                        amount_spent=amount_spent,
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? True."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_yes_class.state_id

    def test_the_vault_is_inactive(self) -> None:
        """The status of the auction in the vault is not 0 (inactive), so the reserve has been met."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        vault_addresses=vault_addresses,
                        amount_spent=amount_spent,
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(state=1),
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? True."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_yes_class.state_id

    def test_the_vault_has_no_tokens_left(self) -> None:
        """There are no tokens left in the vault, we need to deploy a new vault."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        vault_addresses=vault_addresses,
                        amount_spent=amount_spent,
                        safe_contract_address="0x0",
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(state=0),
                    ),
                ),
            )

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(balance=0),
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? True."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_yes_class.state_id

    def test_no_vault_needs_to_be_deployed(self) -> None:
        """There are still tokens left in the safe."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        vault_addresses=vault_addresses,
                        amount_spent=amount_spent,
                        safe_contract_address="0x0",
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(state=0),
                    ),
                ),
            )

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(balance=1),
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? False."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_no_class.state_id

    def test_bad_response_from_contract(self) -> None:
        """The contract returns a bad response."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    dict(
                        vault_addresses=vault_addresses,
                        amount_spent=amount_spent,
                        safe_contract_address="0x0",
                    ),
                )
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(state=0),
                    ),
                ),
            )

            self.mock_contract_api_request(
                contract_id=str(TokenVaultContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address=vault_addresses[-1],
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        ledger_id="ethereum",
                        body=dict(bad_key=1),
                    ),
                ),
            )
            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create the DeployDecisionRound payload, AEAEnforceError: response, response.state, "
                "response.state.body must exist.",
            )
            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? False."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_no_class.state_id


class TestDeployBasketTxRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for DeployBasketTxRoundBehaviour"""

    behaviour_class = DeployBasketTxRoundBehaviour
    decided_yes_state = RandomnessTransactionSubmissionBehaviour
    decided_no_state = FundingRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(BasketFactoryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
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

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_yes_state.state_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(BasketFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
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
                "Couldn't create DeployBasketTxRound payload, AEAEnforceError: contract returned "
                "and empty body or empty tx_hash.",
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.decided_no_state.state_id


class TestDeployTokenVaultTxRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for DeployTokenVaultTxRoundBehaviour"""

    behaviour_class = DeployTokenVaultTxRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a mint tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(TokenVaultFactoryContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63",
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

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.next_behaviour_class.state_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent compiles a mint tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(TokenVaultFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63",
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
                "Couldn't create DeployVaultTxRound payload, AEAEnforceError: contract returned "
                "and empty body or empty tx_hash.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert (
            state.state_id == self.behaviour_class.state_id
        )  # should be in the same behaviour


class TestBasketAddressesRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for BasketAddressesRoundBehaviour"""

    behaviour_class = BasketAddressesRoundBehaviour
    next_behaviour_class = PermissionVaultFactoryRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(BasketFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={
                            "basket_address": "0x1",
                            "creator_address": "0x2",
                        },
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(logging.INFO, "New basket address=0x1")

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.next_behaviour_class.state_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent fails to get the basket addresses."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(BasketFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0xde771104C0C44123d22D39bB716339cD0c3333a1",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={
                            "bad_basket_address": "0x1",
                            "creator_address": "0x2",
                        },
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create BasketAddressRound payload, "
                "AEAEnforceError: couldn't extract the 'basket_address' from the BaketFactoryContract.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert (
            state.state_id == self.behaviour_class.state_id
        )  # should stay in the same round


class TestVaultAddressesRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for VaultAddressesRoundBehaviour"""

    behaviour_class = VaultAddressesRoundBehaviour
    next_behaviour_class = FundingRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(TokenVaultFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={
                            "vault_address": "0x1",
                        },
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.INFO, "Deployed new TokenVault at: 0x1."
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.next_behaviour_class.state_id

    def test_contract_returns_invalid_data(self) -> None:
        """The agent fails to extract vault address."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": ["0x0"],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()
            self.mock_contract_api_request(
                contract_id=str(TokenVaultFactoryContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={
                            "bad_vault_address": "0x1",
                        },
                        ledger_id="ethereum",
                    ),
                ),
            )

            mock_logger.assert_any_call(
                logging.ERROR,
                "Couldn't create VaultAddressesRoundBehaviour payload, AEAEnforceError:"
                " couldn't extract vault_address from the vault_factory.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.ERROR)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert (
            state.state_id == self.behaviour_class.state_id
        )  # it should stay in the same state


class TestPermissionVaultFactoryRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for PermissionVaultFactoryRoundBehaviour"""

    behaviour_class = PermissionVaultFactoryRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a permission vault factory tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": [
                            "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
                        ],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )

        self.fractionalize_deployment_abci_behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(BasketContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
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

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.next_behaviour_class.state_id

    def test_contract_returns_invalid_data(self) -> None:
        """The fails to compile a permission vault factory tx."""

        self.fast_forward_to_state(
            self.fractionalize_deployment_abci_behaviour,
            self.behaviour_class.state_id,
            PeriodState(
                StateDB(
                    0,
                    {
                        "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                        "basket_addresses": [
                            "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
                        ],
                    },
                ),
            ),
        )

        assert (
            cast(
                BaseState, self.fractionalize_deployment_abci_behaviour.current_state
            ).state_id
            == self.behaviour_class.state_id
        )
        with patch.object(
            self.fractionalize_deployment_abci_behaviour.context.logger, "log"
        ) as mock_logger:
            self.fractionalize_deployment_abci_behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(BasketContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
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
                "Couldn't create PermissionVaultFactoryRound payload, AEAEnforceError: "
                "contract returned and empty body or empty tx_hash.",
            )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DONE)

        state = cast(
            BaseState, self.fractionalize_deployment_abci_behaviour.current_state
        )
        assert state.state_id == self.next_behaviour_class.state_id
