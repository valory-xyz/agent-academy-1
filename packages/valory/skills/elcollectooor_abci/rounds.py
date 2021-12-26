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

"""This module contains the data classes for the simple ABCI application."""
import json
import struct
from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import (
    AbstractSet,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    cast,
)

from aea.exceptions import enforce

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    BasePeriodState,
    CollectDifferentUntilAllRound,
    CollectSameUntilThresholdRound,
    EventType,
)
from packages.valory.skills.elcollectooor_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    RandomnessPayload,
    RegistrationPayload,
    ResetPayload,
    SelectKeeperPayload,
    TransactionPayload,
    TransactionType,
)


class Event(Enum):
    """Event enumeration for the simple abci demo."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DECIDED_YES = "decided_yes"
    DECIDED_NO = "decided_no"
    GIB_DETAILS = "gib_details"  # TODO: consider renaming event


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

    def __init__(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        participants: Optional[AbstractSet[str]] = None,
        period_count: Optional[int] = None,
        period_setup_params: Optional[Dict] = None,
        participant_to_randomness: Optional[Mapping[str, RandomnessPayload]] = None,
        most_voted_randomness: Optional[str] = None,
        participant_to_selection: Optional[Mapping[str, SelectKeeperPayload]] = None,
        most_voted_keeper_address: Optional[str] = None,
        participant_to_project: Optional[Mapping[str, ObservationPayload]] = None,
        most_voted_project: Optional[str] = None,
        last_processed_project_id: Optional[int] = None,
        participant_to_decision: Optional[Mapping[str, DecisionPayload]] = None,
        most_voted_decision: Optional[int] = None,
        participant_to_purchase_data: Optional[Mapping[str, TransactionPayload]] = None,
        most_voted_purchase_data: Optional[str] = None,
        most_voted_details: Optional[str] = None,
        participant_to_details: Optional[Mapping[str, DetailsPayload]] = None,
    ) -> None:
        """Initialize a period state."""
        super().__init__(
            participants=participants,
            period_count=period_count,
            period_setup_params=period_setup_params,
        )
        self._participant_to_randomness = participant_to_randomness
        self._most_voted_randomness = most_voted_randomness
        self._most_voted_keeper_address = most_voted_keeper_address
        self._participant_to_selection = participant_to_selection

        # observation round
        self._most_voted_project = most_voted_project
        self._participant_to_project = participant_to_project
        self._last_processed_project_id = last_processed_project_id

        # decision round
        self._most_voted_decision = most_voted_decision
        self._participant_to_decision = participant_to_decision

        # transaction round
        self._participant_to_purchase_data = participant_to_purchase_data
        self._most_voted_purchase_data = most_voted_purchase_data

        # details round
        self._most_voted_details = most_voted_details
        self._participant_to_details = participant_to_details

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
    def participant_to_randomness(self) -> Mapping[str, RandomnessPayload]:
        """Get the participant_to_randomness."""
        enforce(
            self._participant_to_randomness is not None,
            "'participant_to_randomness' field is None",
        )
        return cast(Mapping[str, RandomnessPayload], self._participant_to_randomness)

    @property
    def most_voted_randomness(self) -> str:
        """Get the most_voted_randomness."""
        enforce(
            self._most_voted_randomness is not None,
            "'most_voted_randomness' field is None",
        )
        return cast(str, self._most_voted_randomness)

    @property
    def most_voted_keeper_address(self) -> str:
        """Get the most_voted_keeper_address."""
        enforce(
            self._most_voted_keeper_address is not None,
            "'most_voted_keeper_address' field is None",
        )
        return cast(str, self._most_voted_keeper_address)

    @property
    def participant_to_selection(self) -> Mapping[str, SelectKeeperPayload]:
        """Get the participant_to_selection."""
        enforce(
            self._participant_to_selection is not None,
            "'participant_to_selection' field is None",
        )
        return cast(Mapping[str, SelectKeeperPayload], self._participant_to_selection)

    @property
    def participant_to_project(self) -> Mapping[str, ObservationPayload]:
        """Get the participant_to_project."""
        enforce(
            self._participant_to_project is not None,
            "'participant_to_project' field is None",
        )
        return cast(Mapping[str, ObservationPayload], self._participant_to_project)

    @property
    def most_voted_project(self) -> str:
        """Get the participant_to_project."""
        enforce(
            self._most_voted_project is not None
            and type(self._most_voted_project) == str,
            "'most_voted_project' field is None, or is not a FrozenSet",
        )
        return self._most_voted_project

    @property
    def participant_to_decision(self):
        """Get the participant_to_decision."""
        enforce(
            self._participant_to_decision is not None,
            "'participant_to_decision' field is None",
        )
        return self._participant_to_decision

    @property
    def most_voted_decision(self):
        """Get the most_voted_decision."""
        enforce(
            self._most_voted_decision is not None,
            "'most_voted_decision' field is None",
        )
        return self._most_voted_decision

    @property
    def participant_to_purchase_data(self):
        """Get the participant_to_decision."""
        enforce(
            self._participant_to_purchase_data is not None,
            "'participant_to_decision' field is None",
        )
        return self._participant_to_purchase_data

    @property
    def most_voted_purchase_data(self):
        """Get the purchase data tx response."""
        enforce(
            self._most_voted_purchase_data is not None,
            "'purchase_data_tx' field is None",
        )
        return self._most_voted_purchase_data

    @property
    def most_voted_details(self):
        """Get the details"""
        enforce(self._most_voted_details is not None, "'details' field is None")

        return self._most_voted_details

    @property
    def participant_to_details(self):
        """Get participant to details map"""

        enforce(
            self._participant_to_details is not None, "'participant_to_details' is None"
        )

        return self._participant_to_details


class ElCollectooorABCIAbstractRound(AbstractRound[Event, TransactionType], ABC):
    """Abstract round for the simple abci skill."""

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


class RegistrationRound(CollectDifferentUntilAllRound, ElCollectooorABCIAbstractRound):
    """
    This class represents the registration round.

    Input: None
    Output: a period state with the set of participants.

    It schedules the SelectKeeperARound.
    """

    round_id = "registration"
    allowed_tx_type = RegistrationPayload.transaction_type
    payload_attribute = "sender"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.collection_threshold_reached:
            state = PeriodState(
                participants=self.collection,
                period_count=self.period_state.period_count,
            )
            return state, Event.DONE
        return None


class BaseRandomnessRound(
    CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound
):
    """
    This class represents the randomness round.

    Input: a set of participants (addresses)
    Output: a set of participants (addresses) and randomness

    It schedules the SelectKeeperARound.
    """

    allowed_tx_type = RandomnessPayload.transaction_type
    payload_attribute = "randomness"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                participant_to_randomness=MappingProxyType(self.collection),
                most_voted_randomness=self.most_voted_payload,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class SelectKeeperRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """
    This class represents the select keeper round.

    Input: a set of participants (addresses)
    Output: the selected keeper.
    """

    allowed_tx_type = SelectKeeperPayload.transaction_type
    payload_attribute = "keeper"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                participant_to_selection=MappingProxyType(self.collection),
                most_voted_keeper_address=self.most_voted_payload,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class RandomnessStartupRound(BaseRandomnessRound):
    """Randomness round for startup."""

    round_id = "randomness_startup"


class SelectKeeperAStartupRound(SelectKeeperRound):
    """SelectKeeperA round for startup."""

    round_id = "select_keeper_a_startup"


class BaseResetRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    """This class represents the base reset round."""

    allowed_tx_type = ResetPayload.transaction_type
    payload_attribute = "period_count"

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            # notice that we are not resetting the last_processed_id
            state = self.period_state.update(
                period_count=self.most_voted_payload,
                participant_to_randomness=None,
                most_voted_randomness=None,
                participant_to_selection=None,
                most_voted_keeper_address=None,
                participant_to_project=None,
                most_voted_project=None,
                participant_to_decision=None,
                most_voted_decision=None,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class ObservationRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    allowed_tx_type = ObservationPayload.transaction_type
    round_id = "observation"
    payload_attribute = "project_details"

    def end_block(self) -> Optional[Tuple[BasePeriodState, EventType]]:
        """Process the end of the block."""
        if self.threshold_reached:
            project_id = json.loads(self.most_voted_payload)["project_id"]

            state = self.period_state.update(
                participant_to_project=MappingProxyType(self.collection),
                most_voted_project=self.most_voted_payload,  # TODO: define a "no new project found" payload
                last_processed_project_id=project_id,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class DetailsRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    allowed_tx_type = DecisionPayload.transaction_type
    round_id = "details"
    payload_attribute = "details"

    def end_block(self) -> Optional[Tuple[BasePeriodState, EventType]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
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
    allowed_tx_type = DecisionPayload.transaction_type
    round_id = "decision"
    payload_attribute = "decision"

    def end_block(self) -> Optional[Tuple[BasePeriodState, EventType]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                participant_to_decision=MappingProxyType(self.collection),
                most_voted_decision=self.most_voted_payload,  # it can be binary at this point
            )

            if self.most_voted_payload == 0:
                return state, Event.DECIDED_NO
            elif self.most_voted_payload == -1:
                return state, Event.GIB_DETAILS
            return state, Event.DECIDED_YES

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class TransactionRound(CollectSameUntilThresholdRound, ElCollectooorABCIAbstractRound):
    allowed_tx_type = TransactionPayload.transaction_type
    round_id = "transaction_collection"
    payload_attribute = "purchase_data"

    def end_block(self) -> Optional[Tuple[BasePeriodState, EventType]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                participant_to_purchase_data=MappingProxyType(self.collection),
                most_voted_purchase_data=self.most_voted_payload,
            )
            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class ResetFromRegistrationRound(BaseResetRound):
    round_id = "reset_from_registration"


class ResetFromObservationRound(BaseResetRound):
    round_id = "reset_from_observation"


class ElCollectooorAbciApp(AbciApp[Event]):
    """El Collectooor is getting a fresh haircut."""

    initial_round_cls: Type[AbstractRound] = RegistrationRound
    transition_function: AbciAppTransitionFunction = {
        RegistrationRound: {Event.DONE: RandomnessStartupRound},
        RandomnessStartupRound: {
            Event.DONE: SelectKeeperAStartupRound,
            Event.ROUND_TIMEOUT: RandomnessStartupRound,  # if the round times out we restart
            Event.NO_MAJORITY: RandomnessStartupRound,
            # we can have some agents on either side of an epoch, so we retry
        },
        SelectKeeperAStartupRound: {
            Event.DONE: ObservationRound,
            Event.ROUND_TIMEOUT: ResetFromRegistrationRound,  # if the round times out we restart
            Event.NO_MAJORITY: ResetFromRegistrationRound,  # if the round has no majority we restart
        },
        ResetFromRegistrationRound: {
            Event.DONE: RegistrationRound,
            Event.ROUND_TIMEOUT: RegistrationRound,
            Event.NO_MAJORITY: RegistrationRound,
        },
        ObservationRound: {
            Event.DONE: DecisionRound,
            Event.ROUND_TIMEOUT: ResetFromObservationRound,  # if the round times out we restart
            Event.NO_MAJORITY: ResetFromObservationRound,
        },
        DetailsRound: {
            Event.DONE: DecisionRound,
            Event.ROUND_TIMEOUT: DecisionRound,
            Event.NO_MAJORITY: DecisionRound,
        },
        DecisionRound: {
            Event.DECIDED_YES: TransactionRound,
            Event.DECIDED_NO: ResetFromObservationRound,  # decided to not purchase
            Event.GIB_DETAILS: DetailsRound,  # TODO: consider renaming event
            Event.ROUND_TIMEOUT: ResetFromObservationRound,  # if the round times out we restart
            Event.NO_MAJORITY: ResetFromObservationRound,  # if the round has no majority we start from registration
        },
        TransactionRound: {
            Event.DONE: ResetFromObservationRound,  # TODO: add next round when it becomes available
            Event.ROUND_TIMEOUT: ResetFromObservationRound,
            Event.NO_MAJORITY: ResetFromObservationRound,
        },
        ResetFromObservationRound: {
            Event.DONE: ObservationRound,
            Event.ROUND_TIMEOUT: ResetFromRegistrationRound,
            Event.NO_MAJORITY: ResetFromRegistrationRound,
        },
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }