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

"""This module contains the data classes for the El Collectooorr ABCI application."""
import json
import struct
from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple, Type, cast

from packages.elcollectooorr.skills.elcollectooorr_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    FundingPayload,
    ObservationPayload,
    PaidFractionsPayload,
    PayoutFractionsPayload,
    PostTxPayload,
    PurchasedNFTPayload,
    ResetPayload,
    ResyncPayload,
    TransactionPayload,
    TransactionType,
    TransferNFTPayload,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.rounds import (
    DeployBasketAbciApp,
    DeployBasketTxRound,
    DeployVaultAbciApp,
    DeployVaultTxRound,
    FinishedDeployBasketTxRound,
    FinishedDeployVaultTxRound,
    FinishedPostBasketRound,
    FinishedPostBasketWithoutPermissionRound,
    FinishedPostVaultRound,
    FinishedWithBasketDeploymentSkippedRound,
    FinishedWithoutDeploymentRound,
    PermissionVaultFactoryRound,
    PostBasketDeploymentAbciApp,
    PostVaultDeploymentAbciApp,
)
from packages.valory.skills.abstract_round_abci.abci_app_chain import (
    AbciAppTransitionMapping,
    chain,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
)
from packages.valory.skills.abstract_round_abci.base import (
    BaseSynchronizedData as BasePeriodState,
)
from packages.valory.skills.abstract_round_abci.base import (
    CollectSameUntilThresholdRound,
    DegenerateRound,
)
from packages.valory.skills.registration_abci.rounds import (
    AgentRegistrationAbciApp,
    FinishedRegistrationFFWRound,
    FinishedRegistrationRound,
    RegistrationRound,
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
    """Event enumeration for the El Collectooorr."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DECIDED_YES = "decided_yes"
    DECIDED_NO = "decided_no"
    GIB_DETAILS = "gib_details"
    NO_PAYOUTS = "no_payouts"
    NO_TRANSFER = "no_transfer"
    NO_ACTIVE_PROJECTS = "no_active_projects"
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
        return cast(int, self.db.get("most_voted_epoch_start_block", 0))

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
        return cast(List[str], self.db.get("basket_addresses", []))

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
        return cast(List[str], self.db.get("vault_addresses", []))


class ElcollectooorrABCIAbstractRound(AbstractRound[Event, TransactionType], ABC):
    """Abstract round for the El Collectooorr skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, self.synchronized_data)

    def _return_no_majority_event(self) -> Tuple[PeriodState, Event]:
        """
        Trigger the NO_MAJORITY event.

        :return: a new period state and a NO_MAJORITY event
        """
        return self.period_state, Event.NO_MAJORITY


class BaseResetRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
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


class ObservationRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
    """Defines the Observation Round"""

    allowed_tx_type = ObservationPayload.transaction_type
    round_id = "observation"
    payload_attribute = "project_details"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            most_voted_payload = json.loads(self.most_voted_payload)

            if most_voted_payload == {}:
                return self.period_state, Event.ERROR

            most_recent_project = most_voted_payload["most_recent_project"]
            finished_projects = (
                self.period_state.db.get("finished_projects", [])
                + most_voted_payload["newly_finished_projects"]
            )
            active_projects = most_voted_payload["active_projects"]
            inactive_projects = most_voted_payload["inactive_projects"]

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_project=MappingProxyType(self.collection),
                finished_projects=finished_projects,
                active_projects=active_projects,
                inactive_projects=inactive_projects,
                most_recent_project=most_recent_project,
            )

            if len(active_projects) > 0:
                return state, Event.DONE

            return state, Event.NO_ACTIVE_PROJECTS

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class DetailsRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
    """Defines the Details Round"""

    allowed_tx_type = DetailsPayload.transaction_type
    round_id = "details"
    payload_attribute = "details"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            payload = json.loads(self.most_voted_payload)
            if payload == {}:
                return self.period_state, Event.ERROR

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_details=MappingProxyType(self.collection),
                active_projects=payload["active_projects"],
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class DecisionRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
    """Defines the Decision Round"""

    allowed_tx_type = DecisionPayload.transaction_type
    round_id = "decision"
    payload_attribute = "decision"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""

        if self.threshold_reached:
            project_to_purchase = json.loads(self.most_voted_payload)

            if project_to_purchase == {}:
                # no project needs to be purchased
                return self.period_state, Event.DECIDED_NO

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_decision=MappingProxyType(self.collection),
                project_to_purchase=project_to_purchase,
            )

            return state, Event.DECIDED_YES

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class TransactionRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
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


class ResetFromObservationRound(BaseResetRound):
    """This class acts as a transit round to Observation."""

    round_id = "reset_from_observation"


class FinishedElCollectoorBaseRound(DegenerateRound):
    """This class represents the finished round during operation."""

    round_id = "finished_base_elcollectooorr"


class FinishedElCollectooorrWithoutPurchase(DegenerateRound):
    """This class represents the end of the Elcollectooorr Base ABCI App when there is no purchase to be made."""

    round_id = "finished_base_elcollectooorr_no_purchase"


class ElcollectooorrBaseAbciApp(AbciApp[Event]):
    """The base logic of El Collectooorr."""

    initial_round_cls: Type[AbstractRound] = ObservationRound
    transition_function: AbciAppTransitionFunction = {
        ObservationRound: {
            Event.DONE: DetailsRound,
            Event.NO_ACTIVE_PROJECTS: FinishedElCollectooorrWithoutPurchase,
            Event.ROUND_TIMEOUT: ObservationRound,
            Event.NO_MAJORITY: ObservationRound,
            Event.ERROR: ObservationRound,
        },
        DetailsRound: {
            Event.DONE: DecisionRound,
            Event.ROUND_TIMEOUT: DecisionRound,
            Event.NO_MAJORITY: DecisionRound,
            Event.ERROR: FinishedElCollectooorrWithoutPurchase,
        },
        DecisionRound: {
            Event.DECIDED_YES: TransactionRound,
            Event.DECIDED_NO: FinishedElCollectooorrWithoutPurchase,
            Event.GIB_DETAILS: DetailsRound,
            Event.ROUND_TIMEOUT: FinishedElCollectooorrWithoutPurchase,
            Event.NO_MAJORITY: FinishedElCollectooorrWithoutPurchase,
        },
        TransactionRound: {
            Event.DONE: FinishedElCollectoorBaseRound,
            Event.ROUND_TIMEOUT: ObservationRound,
            Event.NO_MAJORITY: ObservationRound,
            Event.ERROR: ObservationRound,
        },
        FinishedElCollectoorBaseRound: {},
        FinishedElCollectooorrWithoutPurchase: {},
    }
    final_states: Set[AppState] = {
        FinishedElCollectoorBaseRound,
        FinishedElCollectooorrWithoutPurchase,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class ProcessPurchaseRound(
    CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound
):
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

            purchased_project = self.period_state.db.get_strict(
                "project_to_purchase"
            )  # the project that got purchased
            all_purchased_projects = cast(
                List[Dict], self.period_state.db.get("purchased_projects", [])
            )
            all_purchased_projects.append(purchased_project)

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                purchased_nft=self.most_voted_payload,
                project_to_purchase=None,
                purchased_projects=all_purchased_projects,
            )
            return state, Event.DONE

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


class TransferNFTRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
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


class FundingRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
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
                most_voted_funds=json.loads(self.most_voted_payload),
                participant_to_funding_round=MappingProxyType(self.collection),
            )
            return state, Event.DONE

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


class PayoutFractionsRound(
    CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound
):
    """This class represents the post vault deployment round"""

    allowed_tx_type = PayoutFractionsPayload.transaction_type
    round_id = "payout_fractions_round"
    payload_attribute = "payout_fractions"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "{}":
                return self.period_state, Event.NO_PAYOUTS

            payload = json.loads(self.most_voted_payload)
            users_being_paid = payload["raw"]
            tx_hash = payload["encoded"]

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_voted_tx_hash=MappingProxyType(self.collection),
                most_voted_tx_hash=tx_hash,
                users_being_paid=users_being_paid,
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


class PostPayoutRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
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
        already_paid = cast(Dict[str, int], self.period_state.db.get("paid_users", {}))
        newly_paid = cast(
            Dict[str, int], self.period_state.db.get("users_being_paid", {})
        )
        all_paid_users = self._merge_paid_users(already_paid, newly_paid)
        state = self.period_state.update(
            period_state_class=self.period_state_class,
            users_being_paid={},
            paid_users=all_paid_users,
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


class PostTransactionSettlementRound(
    CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound
):
    """After tx settlement via the safe contract."""

    allowed_tx_type = PostTxPayload.transaction_type
    round_id = "post_transaction_settlement_round"
    payload_attribute = "post_tx_data"
    period_state_class = PeriodState

    round_id_to_event = {
        TransactionRound.round_id: PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE,
        DeployBasketTxRound.round_id: PostTransactionSettlementEvent.BASKET_DONE,
        DeployVaultTxRound.round_id: PostTransactionSettlementEvent.VAULT_DONE,
        PermissionVaultFactoryRound.round_id: PostTransactionSettlementEvent.BASKET_PERMISSION,
        PayoutFractionsRound.round_id: PostTransactionSettlementEvent.FRACTION_PAYOUT,
        TransferNFTRound.round_id: PostTransactionSettlementEvent.TRANSFER_NFT_DONE,
    }

    def end_block(self) -> Optional[Tuple[BasePeriodState, Enum]]:
        """The end block."""
        tx_submitter = self.period_state.db.get("tx_submitter", None)

        if tx_submitter is None or tx_submitter not in self.round_id_to_event.keys():
            return self.period_state, Event.ERROR

        if self.threshold_reached:
            if self.most_voted_payload == "{}":
                return self.period_state, Event.ERROR

            payload = json.loads(self.most_voted_payload)
            amount_spent = payload["amount_spent"]
            total_amount_spent = (
                self.period_state.db.get("amount_spent", 0) + amount_spent
            )

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                amount_spent=total_amount_spent,
            )

            return state, self.round_id_to_event[tx_submitter]

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self.period_state, Event.NO_MAJORITY

        return None


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
            Event.NO_MAJORITY: ErrorneousRound,
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


class ResyncRound(CollectSameUntilThresholdRound, ElcollectooorrABCIAbstractRound):
    """This class represents the round used to sync the agent upon reset."""

    allowed_tx_type = ResyncPayload.transaction_type
    round_id = "resync"
    payload_attribute = "resync_data"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            # notice that we are not resetting the last_processed_id
            if self.most_voted_payload == "{}":
                return self.period_state, Event.ERROR

            payload = json.loads(self.most_voted_payload)

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                period_count=self.most_voted_payload,
                **payload,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedResyncRound(DegenerateRound):
    """A degen round for finished resyncing."""

    round_id = "finished_resync"


class ResyncAbciApp(AbciApp[Event]):
    """ABCI to handle resyncing"""

    initial_round_cls: Type[AbstractRound] = ResyncRound
    transition_function: AbciAppTransitionFunction = {
        ResyncRound: {
            Event.DONE: FinishedResyncRound,
            Event.ERROR: ResyncRound,
            Event.ROUND_TIMEOUT: ResyncRound,
        },
        FinishedResyncRound: {},
    }
    final_states: Set[AppState] = {
        FinishedResyncRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


el_collectooorr_app_transition_mapping: AbciAppTransitionMapping = {
    FinishedRegistrationRound: SafeDeploymentAbciApp.initial_round_cls,
    FinishedSafeRound: DeployBasketAbciApp.initial_round_cls,
    FinishedElCollectoorBaseRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedElCollectooorrWithoutPurchase: DeployBasketAbciApp.initial_round_cls,
    FinishedRegistrationFFWRound: ResyncAbciApp.initial_round_cls,
    FinishedResyncRound: DeployBasketAbciApp.initial_round_cls,
    FinishedTransactionSubmissionRound: PostTransactionSettlementRound,
    FinishedDeployVaultTxRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedDeployBasketTxRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedWithBasketDeploymentSkippedRound: PostBasketDeploymentAbciApp.initial_round_cls,
    FinishedBasketTxRound: PostBasketDeploymentAbciApp.initial_round_cls,
    FinishedPostBasketRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedPostBasketWithoutPermissionRound: DeployVaultAbciApp.initial_round_cls,
    FinishedBasketPermissionTxRound: DeployVaultAbciApp.initial_round_cls,
    FinishedElcollectooorrTxRound: TransferNFTAbciApp.initial_round_cls,
    FinishedVaultTxRound: PostVaultDeploymentAbciApp.initial_round_cls,
    FinishedPostVaultRound: BankAbciApp.initial_round_cls,
    FinishedBankWithoutPayoutsRounds: ElcollectooorrBaseAbciApp.initial_round_cls,
    FinishedPayoutTxRound: PostFractionPayoutAbciApp.initial_round_cls,
    FinishedPostPayoutRound: ElcollectooorrBaseAbciApp.initial_round_cls,
    FinishedBankWithPayoutsRounds: TransactionSubmissionAbciApp.initial_round_cls,
    FailedRound: RegistrationRound,
    FinishedWithoutDeploymentRound: BankAbciApp.initial_round_cls,
    FinishedWithoutTransferRound: DeployBasketAbciApp.initial_round_cls,
    FinishedWithTransferRound: TransactionSubmissionAbciApp.initial_round_cls,
    FinishedTransferNftTxRound: DeployBasketAbciApp.initial_round_cls,
    FailedPurchaseProcessingRound: ElcollectooorrBaseAbciApp.initial_round_cls,
    ErrorneousRound: TransactionSubmissionAbciApp.initial_round_cls,
}

ElCollectooorrAbciApp = chain(
    (
        AgentRegistrationAbciApp,
        SafeDeploymentAbciApp,
        ElcollectooorrBaseAbciApp,
        TransactionSubmissionAbciApp,
        TransactionSettlementAbciMultiplexer,
        DeployVaultAbciApp,
        PostVaultDeploymentAbciApp,
        DeployBasketAbciApp,
        PostBasketDeploymentAbciApp,
        TransferNFTAbciApp,
        BankAbciApp,
        PostFractionPayoutAbciApp,
        ResyncAbciApp,
    ),
    el_collectooorr_app_transition_mapping,
)
