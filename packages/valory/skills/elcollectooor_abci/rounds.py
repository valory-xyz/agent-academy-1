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

"""This module contains the data classes for the El Collectooor ABCI application."""
import json
import struct
from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple, Type, cast

from packages.valory.skills.abstract_round_abci.abci_app_chain import (
    AbciAppTransitionMapping,
    chain,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BasePeriodState,
    CollectSameUntilThresholdRound,
    DegenerateRound,
)
from packages.valory.skills.elcollectooor_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    ResetPayload,
    TransactionPayload,
    TransactionType, FundingPayload, PayoutFractionsPayload, PaidFractionsPayload, TransferNFTPayload,
    PurchasedNFTPayload,
)
from packages.valory.skills.fractionalize_deployment_abci.rounds import DeployVaultTxRound, DeployBasketTxRound, \
    DeployVaultAbciApp, DeployBasketAbciApp, FinishedDeployBasketTxRound, FinishedDeployVaultTxRound, \
    PostVaultDeploymentAbciApp, PostBasketDeploymentAbciApp, FinishedPostBasketRound, FinishedPostVaultRound, \
    PermissionVaultFactoryRound, FinishedWithoutDeploymentRound
from packages.valory.skills.registration_abci.rounds import (
    AgentRegistrationAbciApp,
    FinishedRegistrationFFWRound,
    FinishedRegistrationRound, RegistrationRound,
)
from packages.valory.skills.safe_deployment_abci.rounds import (
    FinishedSafeRound,
    SafeDeploymentAbciApp,
)
from packages.valory.skills.transaction_settlement_abci.rounds import (
    FailedRound,
    FinishedTransactionSubmissionRound,
    TransactionSubmissionAbciApp,
)


class Event(Enum):
    """Event enumeration for the El Collectooor."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DECIDED_YES = "decided_yes"
    DECIDED_NO = "decided_no"
    GIB_DETAILS = "gib_details"
    NO_PAYOUTS = "no_payouts"
    NO_TRANSFER = "no_transfer"
    ERROR = "error"


class PostTransactionSettlementEvent(Enum):
    """Event enumeration after the transaction has been settled."""

    EL_COLLECTOOORR_DONE = "elcollectooorr_done"
    VAULT_DONE = "vault_done"
    BASKET_DONE = "basket_done"
    BASKET_PERMISSION = "basket_permission"
    FRACTION_PAYOUT = "fraction_payout"
    TRANSFER_NFT_DONE = "transfer_nft_done"


def encode_float(value: float) -> bytes:
    """Encode a float value."""
    return struct.pack("d", value)


def rotate_list(my_list: list, positions: int) -> List[str]:
    """Rotate a list n positions."""
    return my_list[positions:] + my_list[:positions]


class PeriodState(BasePeriodState):  # pylint: disable=too-many-instance-attributes
    """
    Class to represent a period state.

    This state is replicated by the tendermint application.
    """

    @property
    def keeper_randomness(self) -> float:
        """Get the keeper's random number [0-1]."""
        res = int(self.most_voted_randomness, base=16) // 10 ** 0 % 10
        return cast(float, res / 10)

    @property
    def sorted_participants(self) -> Sequence[str]:
        """
        Get the sorted participants' addresses.

        The addresses are sorted according to their hexadecimal value;
        this is the reason we use key=str.lower as comparator.

        This property is useful when interacting with the Safe contract.

        :return: the sorted participants' addresses
        """
        return sorted(self.participants, key=str.lower)

    @property
    def most_voted_randomness(self) -> str:
        """Get the most_voted_randomness."""
        return cast(str, self.db.get_strict("most_voted_randomness"))

    @property
    def most_voted_keeper_address(self) -> str:
        """Get the most_voted_keeper_address."""
        return cast(str, self.db.get_strict("most_voted_keeper_address"))

    @property
    def participant_to_project(self) -> Mapping[str, ObservationPayload]:
        """Get the participant_to_project."""
        return cast(
            Mapping[str, ObservationPayload],
            self.db.get_strict("participant_to_project"),
        )

    @property
    def most_voted_project(self) -> str:
        """Get the participant_to_project."""
        return cast(str, self.db.get_strict("most_voted_project"))

    @property
    def participant_to_decision(self) -> Mapping[str, DecisionPayload]:
        """Get the participant_to_decision."""
        return cast(
            Mapping[str, DecisionPayload], self.db.get_strict("participant_to_decision")
        )

    @property
    def most_voted_decision(self) -> int:
        """Get the most_voted_decision."""
        return cast(int, self.db.get_strict("most_voted_decision"))

    @property
    def participant_to_purchase_data(self) -> Mapping[str, TransactionPayload]:
        """Get the participant_to_decision."""
        return cast(
            Mapping[str, TransactionPayload],
            self.db.get_strict("participant_to_purchase_data"),
        )

    @property
    def most_voted_purchase_data(self) -> str:
        """Get the purchase data tx response."""
        return cast(str, self.db.get_strict("most_voted_purchase_data"))

    @property
    def most_voted_details(self) -> str:
        """Get the details"""
        return cast(str, self.db.get_strict("most_voted_details"))

    @property
    def participant_to_details(self) -> Mapping[str, DetailsPayload]:
        """Get participant to details map"""
        return cast(
            Mapping[str, DetailsPayload], self.db.get_strict("participant_to_details")
        )

    @property
    def safe_contract_address(self) -> str:
        """Get the safe contract address."""
        return cast(str, self.db.get_strict("safe_contract_address"))

    @property
    def most_voted_funds(self) -> int:
        """
        Returns the most voted funds

        :return: most voted funds amount (in wei)
        """
        return cast(int, self.db.get_strict("most_voted_funds"))

    @property
    def participant_to_funds(self) -> Mapping[str, FundingPayload]:
        """Get the participant_to_funds."""
        return cast(
            Mapping[str, FundingPayload],
            self.db.get_strict("participant_to_funds"),
        )

    @property
    def most_voted_epoch_start_block(self) -> int:
        """Get most_voted_epoch_start_block"""
        return self.db.get("most_voted_epoch_start_block", 0)

    @property
    def participant_to_epoch_start_block(self) -> Mapping[str, int]:
        """Get participant_to_epoch_start_block"""
        return cast(
            Mapping[str, int],
            self.db.get("participant_to_epoch_start_block", 0),
        )

    @property
    def participant_to_basket_addresses(self) -> Mapping[str, List[str]]:
        """Get basket addresses"""
        return cast(
            Mapping[str, List[str]],
            self.db.get_strict("participant_to_basket_addresses"),
        )

    @property
    def basket_addresses(self) -> List[str]:
        """Get basket addresses"""
        return self.db.get("basket_addresses", [])

    @property
    def participant_to_vault_addresses(self) -> Mapping[str, List[str]]:
        """Get vault addresses"""
        return cast(
            Mapping[str, List[str]],
            self.db.get_strict("participant_to_vault_addresses"),
        )

    @property
    def vault_addresses(self) -> List[str]:
        """Get vault addresses"""
        return self.db.get("vault_addresses", [])


class ElCollectooorABCIAbstractRound(AbstractRound[Event, TransactionType], ABC):
    """Abstract round for the El Collectooor skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, self._state)

    def _return_no_majority_event(self) -> Tuple[PeriodState, Event]:
        """
        Trigger the NO_MAJORITY event.

        :return: a new period state and a NO_MAJORITY event
        """
        return self.period_state, Event.NO_MAJORITY


class BaseResetRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """This class represents the base reset round."""

    allowed_tx_type = ResetPayload.transaction_type
    payload_attribute = "period_count"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            # notice that we are not resetting the last_processed_id
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                period_count=self.most_voted_payload,
                participant_to_randomness=None,
                most_voted_randomness=None,
                participant_to_selection=None,
                most_voted_keeper_address=None,
                participant_to_project=None,
                most_voted_project=None,
                participant_to_decision=None,
                most_voted_decision=None,
                participant_to_details=None,
                most_voted_details=None,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class ObservationRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """Defines the Observation Round"""

    allowed_tx_type = ObservationPayload.transaction_type
    round_id = "observation"
    payload_attribute = "project_details"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            most_voted_payload = json.loads(self.most_voted_payload)

            if (
                    "project_id" not in most_voted_payload.keys()
                    or not most_voted_payload["project_id"]
            ):
                return self.period_state, Event.ERROR

            project_id = most_voted_payload["project_id"]
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_project=MappingProxyType(self.collection),
                most_voted_project=self.most_voted_payload,
                last_processed_project_id=project_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class DetailsRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """Defines the Details Round"""

    allowed_tx_type = DetailsPayload.transaction_type
    round_id = "details"
    payload_attribute = "details"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_details=MappingProxyType(self.collection),
                most_voted_details=self.most_voted_payload,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class DecisionRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """Defines the Decision Round"""

    allowed_tx_type = DecisionPayload.transaction_type
    round_id = "decision"
    payload_attribute = "decision"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_decision=MappingProxyType(self.collection),
                most_voted_decision=self.most_voted_payload,  # it can be binary at this point
            )

            if self.most_voted_payload == 0:
                return state, Event.DECIDED_NO
            if self.most_voted_payload == -1:
                return state, Event.GIB_DETAILS
            return state, Event.DECIDED_YES

        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class TransactionRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """Defines the Transaction Round"""

    allowed_tx_type = TransactionPayload.transaction_type
    round_id = "elcollectooorr_transaction_collection"
    payload_attribute = "purchase_data"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.period_state, Event.ERROR

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_voted_tx_hash=MappingProxyType(self.collection),
                most_voted_tx_hash=self.most_voted_payload,
                tx_submitter=self.round_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class ResetFromFundingRound(BaseResetRound):
    """This class acts as a transit round to Observation."""

    round_id = "reset_from_observation"


class FinishedElCollectoorBaseRound(DegenerateRound):
    """This class represents the finished round during operation."""

    round_id = "finished_base_elcollectooor"


class ElCollectooorBaseAbciApp(AbciApp[Event]):
    """The base logic of El Collectooor."""

    initial_round_cls: Type[AbstractRound] = ObservationRound
    transition_function: AbciAppTransitionFunction = {
        ObservationRound: {
            Event.DONE: DetailsRound,
            Event.ROUND_TIMEOUT: ResetFromFundingRound,
            Event.NO_MAJORITY: ResetFromFundingRound,
            Event.ERROR: ResetFromFundingRound,
        },
        DetailsRound: {
            Event.DONE: DecisionRound,
            Event.ROUND_TIMEOUT: DecisionRound,
            Event.NO_MAJORITY: DecisionRound,
        },
        DecisionRound: {
            Event.DECIDED_YES: TransactionRound,
            Event.DECIDED_NO: ResetFromFundingRound,
            Event.GIB_DETAILS: DetailsRound,
            Event.ROUND_TIMEOUT: ResetFromFundingRound,
            Event.NO_MAJORITY: ResetFromFundingRound,
        },
        TransactionRound: {
            Event.DONE: FinishedElCollectoorBaseRound,
            Event.ROUND_TIMEOUT: ResetFromFundingRound,
            Event.NO_MAJORITY: ResetFromFundingRound,
            Event.ERROR: ResetFromFundingRound,
        },
        ResetFromFundingRound: {
            Event.DONE: ObservationRound,
            Event.ROUND_TIMEOUT: ResetFromFundingRound,
            Event.NO_MAJORITY: ResetFromFundingRound,
        },
        FinishedElCollectoorBaseRound: {},
    }
    final_states: Set[AppState] = {
        FinishedElCollectoorBaseRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class ProcessPurchaseRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """Round to process the purchase of the token on artblocks"""

    round_id = "process_purchase_round"
    allowed_tx_type = PurchasedNFTPayload.transaction_type
    payload_attribute = "purchased_nft"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == -1:
                return self.period_state, Event.ERROR

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                purchased_nft=self.most_voted_payload,
            )
            return state, Event.DONE

        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


class TransferNFTRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """A round in which the NFT is transferred from the safe to the basket"""

    round_id = "transfer_nft_round"
    allowed_tx_type = TransferNFTPayload.transaction_type
    payload_attribute = "transfer_data"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.period_state, Event.NO_TRANSFER

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                most_voted_tx_hash=self.most_voted_payload,
                purchased_nft=None,  # optimistic assumption that the tx will be settled correctly
                tx_submitter=self.round_id,
            )
            return state, Event.DONE

        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


class FinishedWithoutTransferRound(DegenerateRound):
    """Degenrate round."""

    round_id = "finished_without_transfer_round"


class FinishedWithTransferRound(DegenerateRound):
    """Degenrate round."""

    round_id = "finished_with_transfer_round"


class FailedPurchaseProcessingRound(DegenerateRound):
    """Degenrate round."""

    round_id = "failed_purchase_process_round"


class TransferNFTAbciApp(AbciApp[Event]):
    """ABCI App to handle NFT transfers."""

    initial_round_cls: Type[AbstractRound] = ProcessPurchaseRound
    transition_function: AbciAppTransitionFunction = {
        ProcessPurchaseRound: {
            Event.DONE: TransferNFTRound,
            Event.ERROR: FailedPurchaseProcessingRound,
            Event.NO_MAJORITY: ProcessPurchaseRound,
            Event.RESET_TIMEOUT: ProcessPurchaseRound,
        },
        TransferNFTRound: {
            Event.DONE: FinishedWithTransferRound,
            Event.NO_TRANSFER: FinishedWithoutTransferRound,
            Event.ROUND_TIMEOUT: TransferNFTRound,
            Event.NO_MAJORITY: TransferNFTRound,
        },
        FailedPurchaseProcessingRound: {},
        FinishedWithTransferRound: {},
        FinishedWithoutTransferRound: {},
    }
    final_states: Set[AppState] = {
        FailedPurchaseProcessingRound,
        FinishedWithTransferRound,
        FinishedWithoutTransferRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class FundingRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """A round in which the funding logic gets exceuted"""

    round_id = "funding_round"
    allowed_tx_type = FundingPayload.transaction_type
    payload_attribute = "address_to_funds"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                most_voted_funds=self.most_voted_payload,
                participant_to_funding_round=MappingProxyType(self.collection)
            )
            return state, Event.DONE

        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


class PayoutFractionsRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """This class represents the post vault deployment round"""

    allowed_tx_type = PayoutFractionsPayload.transaction_type
    round_id = "payout_fractions_round"
    payload_attribute = "payout_fractions"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == '{}':
                return self.period_state, Event.NO_PAYOUTS

            payload = json.loads(self.most_voted_payload)
            users_being_paid = payload['raw']
            tx_hash = payload['encoded']

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_voted_tx_hash=MappingProxyType(self.collection),
                most_voted_tx_hash=tx_hash,
                users_being_paid=json.dumps(users_being_paid),
                tx_submitter=self.round_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedBankWithoutPayoutsRounds(DegenerateRound):
    """Degnerate round"""

    round_id = "finished_bank_without_payouts"


class FinishedBankWithPayoutsRounds(DegenerateRound):
    """Degnerate round"""

    round_id = "finished_bank_with_payouts"


class BankAbciApp(AbciApp[Event]):
    """ABCI App to handle the deposits and payouts."""

    initial_round_cls: Type[AbstractRound] = FundingRound
    transition_function: AbciAppTransitionFunction = {
        FundingRound: {
            Event.DONE: PayoutFractionsRound,
            Event.ROUND_TIMEOUT: FundingRound,
            Event.NO_MAJORITY: FundingRound,
        },
        PayoutFractionsRound: {
            Event.DONE: FinishedBankWithPayoutsRounds,
            Event.NO_PAYOUTS: FinishedBankWithoutPayoutsRounds,
            Event.ROUND_TIMEOUT: FundingRound,
            Event.NO_MAJORITY: FundingRound,
        },
        FinishedBankWithoutPayoutsRounds: {},
        FinishedBankWithPayoutsRounds: {},
    }
    final_states: Set[AppState] = {
        FinishedBankWithPayoutsRounds,
        FinishedBankWithoutPayoutsRounds,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class PostPayoutRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """This class represents the post payout round"""

    allowed_tx_type = PaidFractionsPayload.transaction_type
    round_id = "post_payout_fractions_round"
    payload_attribute = "paid_fractions"
    period_state_class = PeriodState

    @staticmethod
    def _merge_paid_users(old: Dict[str, int], new: Dict[str, int]) -> Dict[str, int]:
        merged = {}

        for address, amount in new.items():
            if address in old.keys():
                merged[address] = old[address] + amount
            else:
                merged[address] = amount

        return merged

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        already_paid = json.loads(self.period_state.db.get("paid_users", '{}'))
        newly_paid = json.loads(self.period_state.db.get("users_being_paid", '{}'))
        all_paid_users = self._merge_paid_users(already_paid, newly_paid)
        state = self.period_state.update(
            period_state_class=self.period_state_class,
            users_being_paid='{}',
            paid_users=json.dumps(all_paid_users),
        )

        return state, Event.DONE


class FinishedPostPayoutRound(DegenerateRound):
    """This class represents the finished post payout ABCI"""

    round_id = "finished_post_payout_round"


class PostFractionPayoutAbciApp(AbciApp[Event]):
    """ABCI to handle Post Bank tasks"""
    initial_round_cls: Type[AbstractRound] = PostPayoutRound
    transition_function: AbciAppTransitionFunction = {
        PostPayoutRound: {
            Event.DONE: FinishedPostPayoutRound,
            Event.ROUND_TIMEOUT: PostPayoutRound,
        },
        FinishedPostPayoutRound: {},
    }
    final_states: Set[AppState] = {
        FinishedPostPayoutRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class PostTransactionSettlementRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "post_transaction_settlement_round"

    round_id_to_event = {
        TransactionRound.round_id: PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE,
        DeployBasketTxRound.round_id: PostTransactionSettlementEvent.BASKET_DONE,
        DeployVaultTxRound.round_id: PostTransactionSettlementEvent.VAULT_DONE,
        PermissionVaultFactoryRound.round_id: PostTransactionSettlementEvent.BASKET_PERMISSION,
        PayoutFractionsRound.round_id: PostTransactionSettlementEvent.FRACTION_PAYOUT,
        TransferNFTRound.round_id: PostTransactionSettlementEvent.TRANSFER_NFT_DONE,
    }

    def end_block(self) -> Optional[Tuple[BasePeriodState, Enum]]:
        tx_submitter = self.period_state.db.get("tx_submitter", None)
        if tx_submitter is None or tx_submitter not in self.round_id_to_event.keys():
            return self.period_state, Event.ERROR

        return self.period_state, self.round_id_to_event[tx_submitter]


class FinishedElcollectooorrTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_elcollectooorr_round"


class FinishedBasketTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_basket_round"


class FinishedVaultTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_vault_round"


class FinishedBasketPermissionTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_vault_round"


class FinishedPayoutTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_payout_tx_round"


class FinishedTransferNftTxRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "finished_nft_tx_round"


class ErrorneousRound(DegenerateRound):
    """Initial round for settling the transactions."""

    round_id = "err_round"


class TransactionSettlementAbciMultiplexer(AbciApp[Event]):
    """ABCI app to multiplex the transaction settlement"""
    initial_round_cls: Type[AbstractRound] = PostTransactionSettlementRound
    transition_function: AbciAppTransitionFunction = {
        PostTransactionSettlementRound: {
            PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE: FinishedElcollectooorrTxRound,
            PostTransactionSettlementEvent.VAULT_DONE: FinishedVaultTxRound,
            PostTransactionSettlementEvent.BASKET_DONE: FinishedBasketTxRound,
            PostTransactionSettlementEvent.BASKET_PERMISSION: FinishedBasketPermissionTxRound,
            PostTransactionSettlementEvent.FRACTION_PAYOUT: FinishedPayoutTxRound,
            PostTransactionSettlementEvent.TRANSFER_NFT_DONE: FinishedTransferNftTxRound,
            Event.ERROR: ErrorneousRound,
        },
        FinishedVaultTxRound: {},
        FinishedBasketTxRound: {},
        FinishedElcollectooorrTxRound: {},
        FinishedBasketPermissionTxRound: {},
        FinishedPayoutTxRound: {},
        FinishedTransferNftTxRound: {},
        ErrorneousRound: {},
    }
    final_states: Set[AppState] = {
        ErrorneousRound,
        FinishedVaultTxRound,
        FinishedBasketTxRound,
        FinishedElcollectooorrTxRound,
        FinishedBasketPermissionTxRound,
        FinishedPayoutTxRound,
        FinishedTransferNftTxRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


el_collectooor_app_transition_mapping: AbciAppTransitionMapping = {
    FinishedRegistrationRound: SafeDeploymentAbciApp.initial_round_cls,
    FinishedSafeRound: DeployBasketAbciApp.initial_round_cls,
    FinishedElCollectoorBaseRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedRegistrationFFWRound: DeployBasketAbciApp.initial_round_cls,
    FinishedTransactionSubmissionRound: PostTransactionSettlementRound,
    FinishedDeployVaultTxRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedDeployBasketTxRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedBasketTxRound: PostBasketDeploymentAbciApp.initial_round_cls,
    FinishedPostBasketRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedBasketPermissionTxRound: DeployVaultAbciApp.initial_round_cls,
    FinishedElcollectooorrTxRound: TransferNFTAbciApp.initial_round_cls,
    FinishedVaultTxRound: PostVaultDeploymentAbciApp.initial_round_cls,
    FinishedPostVaultRound: BankAbciApp.initial_round_cls,
    FinishedBankWithoutPayoutsRounds: ElCollectooorBaseAbciApp.initial_round_cls,
    FinishedPayoutTxRound: PostFractionPayoutAbciApp.initial_round_cls,
    FinishedPostPayoutRound: ElCollectooorBaseAbciApp.initial_round_cls,
    FinishedBankWithPayoutsRounds: TransactionSubmissionAbciApp.initial_round_cls,
    FailedRound: RegistrationRound,
    FinishedWithoutDeploymentRound: BankAbciApp.initial_round_cls,
    FinishedWithoutTransferRound: DeployBasketAbciApp.initial_round_cls,
    FinishedWithTransferRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedTransferNftTxRound: DeployBasketAbciApp.initial_round_cls,
    FailedPurchaseProcessingRound: ElCollectooorBaseAbciApp.initial_round_cls,
    ErrorneousRound: TransactionSubmissionAbciApp.initial_round_cls,
}

ElCollectooorAbciApp = chain(
    (
        AgentRegistrationAbciApp,
        SafeDeploymentAbciApp,
        ElCollectooorBaseAbciApp,
        TransactionSubmissionAbciApp,
        TransactionSettlementAbciMultiplexer,
        DeployVaultAbciApp,
        PostVaultDeploymentAbciApp,
        DeployBasketAbciApp,
        PostBasketDeploymentAbciApp,
        TransferNFTAbciApp,
        BankAbciApp,
        PostFractionPayoutAbciApp,
    ),
    el_collectooor_app_transition_mapping,
)
