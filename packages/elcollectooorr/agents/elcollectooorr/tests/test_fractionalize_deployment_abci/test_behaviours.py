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
# pylint: skip-file

"""Tests for valory/fractionalize_deployment_abci skill's behaviours."""
import logging
from enum import Enum
from typing import List, Optional, cast
from unittest.mock import patch

from aea.helpers.transaction.base import State

from packages.elcollectooorr.contracts.basket.contract import BasketContract
from packages.elcollectooorr.contracts.basket_factory.contract import (
    BasketFactoryContract,
)
from packages.elcollectooorr.contracts.token_vault.contract import TokenVaultContract
from packages.elcollectooorr.contracts.token_vault_factory.contract import (
    TokenVaultFactoryContract,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.behaviours import (
    FundingRoundBehaviour,
    WEI_TO_ETH,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.rounds import SynchronizedData
from packages.elcollectooorr.skills.elcollectooorr_abci.tests import (
    PACKAGE_DIR as ELCOLLECTOOORR_PACKAGE_DIR,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.behaviours import (
    BasketAddressesRoundBehaviour,
    DeployBasketTxRoundBehaviour,
    DeployDecisionRoundBehaviour,
    DeployTokenVaultTxRoundBehaviour,
    PermissionVaultFactoryRoundBehaviour,
    VaultAddressesRoundBehaviour,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.rounds import Event
from packages.valory.contracts.gnosis_safe.contract import GnosisSafeContract
from packages.valory.protocols.contract_api.message import ContractApiMessage
from packages.valory.skills.abstract_round_abci.base import AbciAppDB as StateDB
from packages.valory.skills.abstract_round_abci.behaviours import (
    BaseBehaviour as BaseState,
)
from packages.valory.skills.abstract_round_abci.test_tools.base import (
    FSMBehaviourBaseCase,
)
from packages.valory.skills.transaction_settlement_abci.behaviours import (
    RandomnessTransactionSubmissionBehaviour,
)


class FractionalizeFSMBehaviourBaseCase(
    FSMBehaviourBaseCase
):  # pylint: disable=protected-access
    """Base case for testing PriceEstimation FSMBehaviour."""

    path_to_skill = ELCOLLECTOOORR_PACKAGE_DIR

    def end_round(self, event: Optional[Enum] = None) -> None:  # type: ignore
        """End the test round."""
        done_event = event or Event.DONE
        super().end_round(done_event)


class TestDeployDecisionRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for the Deploy Decision Round Behaviour"""

    behaviour_class = DeployDecisionRoundBehaviour
    decided_yes_class = DeployBasketTxRoundBehaviour
    decided_no_class = FundingRoundBehaviour

    def test_no_vault_was_previously_deployed(self) -> None:
        """No vault was previously deployed, new one needs to be deployed."""
        amount_spent: int = 0

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            amount_spent=amount_spent,
                        ),
                    )
                )
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? deploy_full."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_class.auto_behaviour_id()

    def test_over_the_budget(self) -> None:
        """We are over the budget for the current vault, we need to deploy a new one."""
        amount_spent: int = int(10.4 * WEI_TO_ETH)

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            vault_addresses=["0x0"],  # a vault exists
                            amount_spent=amount_spent,
                        ),
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

            mock_logger.assert_any_call(
                logging.INFO, "Deploy new basket and vault? deploy_full."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_class.auto_behaviour_id()

    def test_the_vault_is_inactive(self) -> None:
        """The status of the auction in the vault is not 0 (inactive), so the reserve has been met."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            vault_addresses=vault_addresses,
                            amount_spent=amount_spent,
                        ),
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

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
                logging.INFO, "Deploy new basket and vault? deploy_full."
            )
        self.mock_a2a_transaction()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_class.auto_behaviour_id()

    def test_the_vault_has_no_tokens_left(self) -> None:
        """There are no tokens left in the vault, we need to deploy a new vault."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            vault_addresses=vault_addresses,
                            amount_spent=amount_spent,
                            safe_contract_address="0x0",
                        ),
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

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
                logging.INFO, "Deploy new basket and vault? deploy_full."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_YES)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_class.auto_behaviour_id()

    def test_no_vault_needs_to_be_deployed(self) -> None:
        """There are still tokens left in the safe."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            vault_addresses=vault_addresses,
                            amount_spent=amount_spent,
                            safe_contract_address="0x0",
                        ),
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

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
                logging.INFO, "Deploy new basket and vault? dont_deploy."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_no_class.auto_behaviour_id()

    def test_bad_response_from_contract(self) -> None:
        """The contract returns a bad response."""
        amount_spent: int = 10 ** 19
        vault_addresses: List[str] = ["0x0"]

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        dict(
                            vault_addresses=vault_addresses,
                            amount_spent=amount_spent,
                            safe_contract_address="0x0",
                        ),
                    )
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

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
                logging.INFO, "Deploy new basket and vault? dont_deploy."
            )
        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_no_class.auto_behaviour_id()


class TestDeployBasketTxRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for DeployBasketTxRoundBehaviour"""

    behaviour_class = DeployBasketTxRoundBehaviour
    decided_yes_state = RandomnessTransactionSubmissionBehaviour
    decided_no_state = FundingRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
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
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_yes_state.auto_behaviour_id()

    def test_contract_returns_invalid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
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
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()
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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.decided_no_state.auto_behaviour_id()


class TestDeployTokenVaultTxRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for DeployTokenVaultTxRoundBehaviour"""

    behaviour_class = DeployTokenVaultTxRoundBehaviour
    next_behaviour_class = RandomnessTransactionSubmissionBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a mint tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.auto_behaviour_id()

    def test_contract_returns_invalid_data(self) -> None:
        """The agent compiles a mint tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert (
            state.behaviour_id == self.behaviour_class.auto_behaviour_id()
        )  # should be in the same behaviour


class TestBasketAddressesRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for BasketAddressesRoundBehaviour"""

    behaviour_class = BasketAddressesRoundBehaviour
    next_behaviour_class = PermissionVaultFactoryRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                            "vault_addresses": ["0x0"],
                            "final_tx_hash": "0x0",
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()
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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.auto_behaviour_id()

    def test_contract_returns_invalid_data(self) -> None:
        """The agent fails to get the basket addresses."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                            "vault_addresses": ["0x0"],
                            "final_tx_hash": "0x0",
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()
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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert (
            state.behaviour_id == self.behaviour_class.auto_behaviour_id()
        )  # should stay in the same round


class TestVaultAddressesRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for VaultAddressesRoundBehaviour"""

    behaviour_class = VaultAddressesRoundBehaviour
    next_behaviour_class = FundingRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a create basket tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                            "final_tx_hash": "0x0",
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()
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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.next_behaviour_class.auto_behaviour_id()

    def test_contract_returns_invalid_data(self) -> None:
        """The agent fails to extract vault address."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": ["0x0"],
                            "final_tx_hash": "0x0",
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()
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

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert (
            state.behaviour_id == self.behaviour_class.auto_behaviour_id()
        )  # it should stay in the same state


class TestPermissionVaultFactoryRoundBehaviour(FractionalizeFSMBehaviourBaseCase):
    """Tests for PermissionVaultFactoryRoundBehaviour"""

    behaviour_class = PermissionVaultFactoryRoundBehaviour
    next_yes_behaviour_class = RandomnessTransactionSubmissionBehaviour
    next_no_behaviour_class = DeployTokenVaultTxRoundBehaviour

    def test_contract_returns_valid_data(self) -> None:
        """The agent compiles a permission vault factory tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": [
                                "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
                            ],
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(BasketContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={"operator": "0x0000000000000000000000000000000000000000"},
                    ledger_id="ethereum",
                ),
            ),
        )

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
        self.end_round(event=Event.DECIDED_YES)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.next_yes_behaviour_class.auto_behaviour_id()

    def test_contract_returns_valid_data_already_permissioned(self) -> None:
        """The agent compiles a permission vault factory tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": [
                                "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
                            ],
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )

        self.behaviour.act_wrapper()

        self.mock_contract_api_request(
            contract_id=str(BasketContract.contract_id),
            request_kwargs=dict(
                performative=ContractApiMessage.Performative.GET_STATE,
                contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
            ),
            response_kwargs=dict(
                performative=ContractApiMessage.Performative.STATE,
                state=State(
                    body={"operator": "0x85Aa7f78BdB2DE8F3e0c0010d99AD5853fFcfC63"},
                    ledger_id="ethereum",
                ),
            ),
        )

        self.mock_a2a_transaction()
        self._test_done_flag_set()
        self.end_round(event=Event.DECIDED_NO)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.next_no_behaviour_class.auto_behaviour_id()

    def test_contract_returns_invalid_data(self) -> None:
        """The fails to compile a permission vault factory tx."""

        self.fast_forward_to_behaviour(
            self.behaviour,
            self.behaviour_class.auto_behaviour_id(),
            SynchronizedData(
                StateDB(
                    setup_data=StateDB.data_to_lists(
                        {
                            "safe_contract_address": "0x1CD623a86751d4C4f20c96000FEC763941f098A3",
                            "basket_addresses": [
                                "0x1CD623a86751d4C4f20c96000FEC763941f098A2"
                            ],
                        },
                    ),
                ),
            ),
        )

        assert (
            cast(
                BaseState,
                self.behaviour.current_behaviour,
            ).behaviour_id
            == self.behaviour_class.auto_behaviour_id()
        )
        with patch.object(self.behaviour.context.logger, "log") as mock_logger:
            self.behaviour.act_wrapper()

            self.mock_contract_api_request(
                contract_id=str(BasketContract.contract_id),
                request_kwargs=dict(
                    performative=ContractApiMessage.Performative.GET_STATE,
                    contract_address="0x1CD623a86751d4C4f20c96000FEC763941f098A2",
                ),
                response_kwargs=dict(
                    performative=ContractApiMessage.Performative.STATE,
                    state=State(
                        body={"operator": "0x1CD623a86751d4C4f20c96000FEC763941f098A3"},
                        ledger_id="ethereum",
                    ),
                ),
            )

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
        self.end_round(event=Event.ERROR)

        state = cast(BaseState, self.behaviour.current_behaviour)
        assert state.behaviour_id == self.behaviour_class.auto_behaviour_id()
