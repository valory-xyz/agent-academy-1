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

"""This module contains the data classes for the eoa deployment ABCI application."""
import json
from enum import Enum
from types import MappingProxyType
from typing import Dict, List, Optional, Set, Tuple, Type, cast

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BasePeriodState,
    CollectSameUntilThresholdRound,
    DegenerateRound,
    OnlyKeeperSendsRound,
)
from packages.valory.skills.eoa_purchase_abci.payloads import (
    FundingTransactionPayload,
    PurchaseTokenPayload,
    RandomnessPayload,
    SelectKeeperPayload,
    ValidatePayload,
)


class Event(Enum):
    """Event enumeration for the price estimation demo."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    NEGATIVE = "negative"
    NONE = "none"
    FAILED = "failed"
    PURCHASE_TIMEOUT = "deploy_timeout"
    VALIDATE_TIMEOUT = "validate_timeout"


class PeriodState(BasePeriodState):
    """
    Class to represent a period state.

    This state is replicated by the tendermint application.
    """

    @property
    def eoa_contract_address(self) -> str:
        """Get the eoa contract address."""
        return cast(str, self.db.get_strict("eoa_contract_address"))


class RandomnessEoaRound(CollectSameUntilThresholdRound):
    """A round for generating randomness"""

    round_id = "randomness_eoa"
    allowed_tx_type = RandomnessPayload.transaction_type
    payload_attribute = "randomness"
    period_state_class = PeriodState
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = "participant_to_randomness"
    selection_key = "most_voted_randomness"


class SelectKeeperEoaRound(CollectSameUntilThresholdRound):
    """A round in a which keeper is selected"""

    round_id = "select_keeper_eoa"
    allowed_tx_type = SelectKeeperPayload.transaction_type
    payload_attribute = "keeper"
    period_state_class = PeriodState
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = "participant_to_selection"
    selection_key = "most_voted_keeper_address"


class FundKeeperRound(CollectSameUntilThresholdRound):
    """A round in a which a funding transaction for the keeper is prepared."""

    round_id = "fund_keeper"
    allowed_tx_type = FundingTransactionPayload.transaction_type
    payload_attribute = "funding_tx_data"
    period_state_class = PeriodState
    done_event = Event.DONE
    no_majority_event = Event.NO_MAJORITY
    collection_key = "participant_to_fund_tx"
    selection_key = "most_voted_tx_hash"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Enum]]:
        """Add the current round id as tx_submitter, then call the superclass impl."""
        # if the round were to fail, the `tx_submitter` attribute
        # would be overwritten by the next round that would try to send a tx
        self.period_state.update(tx_submitter=self.round_id)
        return super().end_block()


class PurchaseTokenRound(OnlyKeeperSendsRound):
    """A round in a which the keeper purchases the token"""

    round_id = "deploy_eoa"
    allowed_tx_type = PurchaseTokenPayload.transaction_type
    payload_attribute = "purchase_data"
    period_state_class = PeriodState
    done_event = Event.DONE
    fail_event = Event.FAILED
    payload_key = "purchase_data"


class ValidatePurchaseRound(CollectSameUntilThresholdRound):
    """A round in a which the purchase done by the keeper is validated"""

    round_id = "validate_purchase"
    allowed_tx_type = ValidatePayload.transaction_type
    payload_attribute = "validation_data"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""

        if self.threshold_reached:
            validation_payload = json.loads(self.most_voted_payload)

            if validation_payload == {}:
                # an error occurred, we just retry for now.
                return self.period_state, Event.FAILED

            processed_txs = cast(
                List[str], self.period_state.db.get("processed_txs", [])
            )
            is_correct = validation_payload["is_correct"]
            purchase_data = json.loads(self.period_state.db.get_strict("purchase_data"))
            keeper_tx_digest = purchase_data["tx_digest"]
            keeper_status = purchase_data["status"]

            processed_txs.append(keeper_tx_digest)

            if is_correct:
                # the keeper acted as expected
                purchased_project = self.period_state.db.get_strict(
                    "project_to_purchase"
                )  # the project that got purchased
                all_purchased_projects = cast(
                    List[Dict], self.period_state.db.get("purchased_projects", [])
                )
                all_purchased_projects.append(purchased_project)

                if keeper_status:
                    state = self.period_state.update(
                        period_state_class=self.period_state_class,
                        participant_to_keeper_validation=MappingProxyType(
                            self.collection
                        ),
                        processed_txs=processed_txs,
                        purchased_projects=all_purchased_projects,
                    )
                    return state, Event.DONE

                return self._handle_refund()

            # the keeper misbehaved, we need to slash his operator's stake/security deposit
            slash_tx = validation_payload["slash_tx"]
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_keeper_validation=MappingProxyType(self.collection),
                most_voted_tx_hash=slash_tx,
                processed_txs=processed_txs,
                tx_submitter=self.round_id,
            )
            return state, Event.NEGATIVE

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None

    def _handle_refund(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Handle the case when the keeper refunds the safe."""
        value = self.period_state.db.get_strict("project_to_purchase")["price"]
        total_amount_spent = self.period_state.db.get_strict("amount_spent") - value
        state = self.period_state.update(
            period_state_class=self.period_state_class,
            amount_spent=total_amount_spent,
        )

        return state, Event.DONE


class FinishedPurchasingRound(DegenerateRound):
    """A round that represents that the keeper has purchased and transferred the token."""

    round_id = "finished_purchasing"


class FinishedWithSafeTxRound(DegenerateRound):
    """A round that represents that a safe tx should follow next."""

    round_id = "finished_with_safe_tx"


class FinishedWithSlashTxRound(DegenerateRound):
    """A round that represents that a slash tx should follow next."""

    round_id = "finished_with_slash_tx"


class KeeperSelectionAndFundingAbciApp(AbciApp[Event]):
    """
    Abci App to select a keeper and prepare a funding tx.

    Initial round: RandomnessEoaRound

    Initial states: {RandomnessEoaRound}

    Transition states:
        0. RandomnessEoaRound
            - done: 1.
            - round timeout: 0.
            - no majority: 0.
        1. SelectKeeperEoaRound
            - done: 2.
            - round timeout: 0.
            - no majority: 0.
        2. FundKeeperRound
            - done: TransactionSettlementAbci.
            - deploy timeout: 1.
            - failed: 1.

    Final states: {FinishedEoaRound}

    Timeouts:
        round timeout: 30.0
    """

    initial_round_cls: Type[AbstractRound] = RandomnessEoaRound
    transition_function: AbciAppTransitionFunction = {
        RandomnessEoaRound: {
            Event.DONE: SelectKeeperEoaRound,
            Event.ROUND_TIMEOUT: RandomnessEoaRound,
            Event.NO_MAJORITY: RandomnessEoaRound,
        },
        SelectKeeperEoaRound: {
            Event.DONE: FundKeeperRound,
            Event.ROUND_TIMEOUT: RandomnessEoaRound,
            Event.NO_MAJORITY: RandomnessEoaRound,
        },
        FundKeeperRound: {
            Event.DONE: FinishedWithSafeTxRound,
            Event.PURCHASE_TIMEOUT: SelectKeeperEoaRound,
            Event.FAILED: SelectKeeperEoaRound,
        },
        FinishedWithSafeTxRound: {},
        FinishedPurchasingRound: {},
    }
    final_states: Set[AppState] = {FinishedWithSafeTxRound, FinishedPurchasingRound}
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.VALIDATE_TIMEOUT: 30.0,
        Event.PURCHASE_TIMEOUT: 30.0,
    }


class PurchasingAndValidationAbciApp(AbciApp[Event]):
    """
    Abci app to purchase a token and validate the outcome.

    Initial round: RandomnessEoaRound

    Initial states: {RandomnessEoaRound}

    Transition states:
        0. PurchaseTokenRound
            - done: 1.
            - round timeout: 1.
        1. ValidatePurchaseRound
            - done: FinishedPurchasingRound.
            - round timeout: 1.
            - no majority: 1.

    Final states: {FinishedEoaRound}

    Timeouts:
        round timeout: 30.0
    """

    initial_round_cls: Type[AbstractRound] = PurchaseTokenRound
    transition_function: AbciAppTransitionFunction = {
        PurchaseTokenRound: {
            Event.DONE: ValidatePurchaseRound,
            Event.ROUND_TIMEOUT: ValidatePurchaseRound,
        },
        ValidatePurchaseRound: {
            Event.DONE: FinishedPurchasingRound,
            Event.NEGATIVE: FinishedWithSlashTxRound,
            Event.VALIDATE_TIMEOUT: ValidatePurchaseRound,
            Event.FAILED: ValidatePurchaseRound,
            Event.NO_MAJORITY: ValidatePurchaseRound,
        },
        FinishedWithSlashTxRound: {},
        FinishedPurchasingRound: {},
    }
    final_states: Set[AppState] = {FinishedWithSlashTxRound, FinishedPurchasingRound}
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.VALIDATE_TIMEOUT: 30.0,
        Event.PURCHASE_TIMEOUT: 30.0,
    }
