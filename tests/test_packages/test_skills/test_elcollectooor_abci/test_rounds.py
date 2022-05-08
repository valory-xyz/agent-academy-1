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

"""Test the base.py module of the skill."""
import json
import logging  # noqa: F401
from types import MappingProxyType
from typing import Dict, FrozenSet, cast
from unittest import mock

from packages.valory.skills.abstract_round_abci.base import (
    AbstractRound,
    ConsensusParams,
    StateDB,
)
from packages.valory.skills.elcollectooor_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    TransactionPayload, FundingPayload,
)
from packages.valory.skills.elcollectooor_abci.rounds import (
    DecisionRound,
    DetailsRound,
    Event,
    ObservationRound,
    PeriodState,
    TransactionRound,
    rotate_list, FundingRound,
)
from packages.valory.skills.simple_abci.payloads import (
    RandomnessPayload,
    ResetPayload,
    SelectKeeperPayload,
)

MAX_PARTICIPANTS: int = 4
RANDOMNESS: str = "d1c29dce46f979f9748210d24bce4eae8be91272f5ca1a6aea2832d3dd676f51"


def get_participants() -> FrozenSet[str]:
    """Participants"""
    return frozenset([f"agent_{i}" for i in range(MAX_PARTICIPANTS)])


def get_participant_to_randomness(
        participants: FrozenSet[str], round_id: int
) -> Dict[str, RandomnessPayload]:
    """participant_to_randomness"""
    return {
        participant: RandomnessPayload(
            sender=participant,
            round_id=round_id,
            randomness=RANDOMNESS,
        )
        for participant in participants
    }


def get_participant_to_selection(
        participants: FrozenSet[str],
) -> Dict[str, SelectKeeperPayload]:
    """participant_to_selection"""
    return {
        participant: SelectKeeperPayload(sender=participant, keeper="keeper")
        for participant in participants
    }


def get_participant_to_period_count(
        participants: FrozenSet[str], period_count: int
) -> Dict[str, ResetPayload]:
    """participant_to_selection"""
    return {
        participant: ResetPayload(sender=participant, period_count=period_count)
        for participant in participants
    }


class BaseRoundTestClass:
    """Base test class for Rounds."""

    period_state: PeriodState
    consensus_params: ConsensusParams
    participants: FrozenSet[str]

    @classmethod
    def setup(
            cls,
    ) -> None:
        """Setup the test class."""

        cls.participants = get_participants()
        cls.period_state = PeriodState(
            StateDB(initial_period=0, initial_data=dict(participants=cls.participants))
        )
        cls.consensus_params = ConsensusParams(max_participants=MAX_PARTICIPANTS)

    def _test_no_majority_event(self, round_obj: AbstractRound) -> None:
        """Test the NO_MAJORITY event."""
        with mock.patch.object(round_obj, "is_majority_possible", return_value=False):
            result = round_obj.end_block()
            assert result is not None
            state, event = result
            assert event == Event.NO_MAJORITY


class TestObservationRound(BaseRoundTestClass):
    """Tests for ObservationRound."""

    def test_run(
            self,
    ) -> None:
        """Run tests."""
        active_projects = [
            {
                "project_id": 121,
            },
            {
                "project_id": 122,
            },
            {
                "project_id": 123,
            }
        ]
        inactive_projects = [1, 2, 3]
        finished_projects = [4, 5, 6]

        payload_data = {
            "active_projects": active_projects,
            "inactive_projects": inactive_projects,
            "newly_finished_projects": finished_projects,
            "most_recent_project": 123,
        }

        test_round = ObservationRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            ObservationPayload(
                sender=participant, project_details=json.dumps(payload_data)
            )
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_project=MappingProxyType(test_round.collection),
            most_voted_project=test_round.most_voted_payload,
            most_recent_project=123,
            inactive_projects=inactive_projects,
            active_projects=active_projects
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_project
                == cast(PeriodState, actual_next_state).most_voted_project
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_project[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_project.items()
            ]
        )

        assert event == Event.DONE


class TestPositiveDecisionRound(BaseRoundTestClass):
    """Tests for DecisionRound, when the decision is positive."""

    def test_run(
            self,
    ) -> None:
        """Run tests."""
        payload_data = {
            "project_id": 123
        }

        test_round = DecisionRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DecisionPayload(sender=participant, decision=json.dumps(payload_data))
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_decision=MappingProxyType(test_round.collection),
            most_voted_decision=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_decision
                == cast(PeriodState, actual_next_state).most_voted_decision
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_decision[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_decision.items()
            ]
        )

        assert event == Event.DECIDED_YES


class TestNegativeDecisionRound(BaseRoundTestClass):
    """Tests for DecisionRound, when the decision is negative."""

    def test_run(
            self,
    ) -> None:
        """Run tests."""

        test_round = DecisionRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        project_to_purchase = {}  # {} represents a NO decision for now

        first_payload, *payloads = [
            DecisionPayload(sender=participant, decision=json.dumps(project_to_purchase))
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_decision=MappingProxyType(test_round.collection),
            most_voted_decision=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_decision
                == cast(PeriodState, actual_next_state).most_voted_decision
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_decision[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_decision.items()
            ]
        )

        assert event == Event.DECIDED_NO


class TestTransactionRound(BaseRoundTestClass):
    """Tests for TransactionRound."""

    def test_run(
            self,
    ) -> None:
        """Run tests."""
        test_purchase_data = "test_data"

        test_round = TransactionRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            TransactionPayload(sender=participant, purchase_data=test_purchase_data)
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_purchase_data=MappingProxyType(test_round.collection),
            most_voted_purchase_data=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_purchase_data
                == cast(PeriodState, actual_next_state).most_voted_purchase_data
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_purchase_data[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_purchase_data.items()
            ]
        )

        assert event == Event.DONE


class TestDetailsRound(BaseRoundTestClass):
    """Tests for DetailsRound"""

    def test_run(
            self,
    ) -> None:
        """Run tests."""
        test_details = json.dumps([{"data": "more"}])

        test_round = DetailsRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DetailsPayload(sender=participant, details=test_details)
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_details=MappingProxyType(test_round.collection),
            most_voted_details=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_details
                == cast(PeriodState, actual_next_state).most_voted_details
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_details[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_details.items()
            ]
        )

        assert event == Event.DONE


class TestFundingDecisionRound(BaseRoundTestClass):
    """Tests for FundingRound."""

    def test_run(
            self,
    ) -> None:
        """Run tests."""
        test_funds = {"0x0": 10 ** 18}

        test_round = FundingRound(
            state=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            FundingPayload(sender=participant, address_to_funds=json.dumps(test_funds))
            for participant in self.participants
        ]

        # only one participant has voted
        # no event should be returned
        test_round.process_payload(first_payload)
        assert test_round.collection[first_payload.sender] == first_payload
        assert test_round.end_block() is None

        # enough members have voted
        # but no majority is reached
        self._test_no_majority_event(test_round)

        # all members voted in the same way
        # Event DONE should be returned
        for payload in payloads:
            test_round.process_payload(payload)

        actual_next_state = self.period_state.update(
            participant_to_funds=MappingProxyType(test_round.collection),
            most_voted_funds=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
                cast(PeriodState, state).most_voted_funds
                == cast(PeriodState, actual_next_state).most_voted_funds
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(PeriodState, state).participant_to_funds[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                PeriodState, actual_next_state
            ).participant_to_funds.items()
            ]
        )

        assert event == Event.DONE


def test_rotate_list_method() -> None:
    """Test `rotate_list` method."""

    ex_list = [1, 2, 3, 4, 5]
    assert rotate_list(ex_list, 2) == [3, 4, 5, 1, 2]


def test_period_state() -> None:  # pylint:too-many-locals
    """Test PeriodState."""

    participants = get_participants()
    period_count = 10
    period_setup_params = {}  # type: ignore
    participant_to_randomness = {
        participant: RandomnessPayload(
            sender=participant, randomness=RANDOMNESS, round_id=0
        )
        for participant in participants
    }
    most_voted_randomness = "0xabcd"
    participant_to_selection = {
        participant: SelectKeeperPayload(sender=participant, keeper="keeper")
        for participant in participants
    }
    most_voted_keeper_address = "keeper"

    period_state = PeriodState(
        StateDB(
            initial_period=period_count,
            initial_data=dict(
                participants=participants,
                period_count=period_count,
                period_setup_params=period_setup_params,
                participant_to_randomness=participant_to_randomness,
                most_voted_randomness=most_voted_randomness,
                participant_to_selection=participant_to_selection,
                most_voted_keeper_address=most_voted_keeper_address,
            ),
        )
    )

    assert period_state.participants == participants
    assert period_state.period_count == period_count
    assert period_state.participant_to_randomness == participant_to_randomness
    assert period_state.most_voted_randomness == most_voted_randomness
    assert period_state.participant_to_selection == participant_to_selection
    assert period_state.most_voted_keeper_address == most_voted_keeper_address
    assert period_state.sorted_participants == sorted(participants)
    assert period_state.keeper_randomness == cast(
        float, (int(most_voted_randomness, base=16) // 10 ** 0 % 10) / 10
    )
