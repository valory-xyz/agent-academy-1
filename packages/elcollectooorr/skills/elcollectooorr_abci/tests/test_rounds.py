# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------
#
#   Copyright 2021-2023 Valory AG
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
# pylint: skip-file; # noqa: B028

"""Test the base.py module of the skill."""
import json
import logging  # noqa: F401
from copy import deepcopy
from typing import Dict, Tuple, cast
from unittest import mock

from packages.elcollectooorr.skills.elcollectooorr_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    FundingPayload,
    ObservationPayload,
    PayoutFractionsPayload,
    PostTxPayload,
    PurchasedNFTPayload,
    ResyncPayload,
    TransactionPayload,
    TransferNFTPayload,
)
from packages.elcollectooorr.skills.elcollectooorr_abci.rounds import (
    DecisionRound,
    DetailsRound,
    Event,
    FundingRound,
    ObservationRound,
    PayoutFractionsRound,
    PostPayoutRound,
    PostTransactionSettlementEvent,
    PostTransactionSettlementRound,
    ProcessPurchaseRound,
    ResyncRound,
    SynchronizedData,
    TransactionRound,
    TransferNFTRound,
    rotate_list,
)
from packages.valory.skills.abstract_round_abci.base import AbciAppDB as StateDB
from packages.valory.skills.abstract_round_abci.base import CollectionRound
from packages.valory.skills.abstract_round_abci.test_tools.rounds import (
    BaseRoundTestClass as ExternalBaseRoundTestClass,
)
from packages.valory.skills.transaction_settlement_abci.payloads import (
    RandomnessPayload,
    SelectKeeperPayload,
)


WEI_TO_ETH = 10 ** 18


MAX_PARTICIPANTS: int = 4
RANDOMNESS: str = "d1c29dce46f979f9748210d24bce4eae8be91272f5ca1a6aea2832d3dd676f51"


def get_participants() -> Tuple[str]:
    """Participants"""
    participants = tuple([f"agent_{i}" for i in range(MAX_PARTICIPANTS)])
    return cast(Tuple[str], participants)


class BaseRoundTestClass(ExternalBaseRoundTestClass):
    """Base test class for Rounds."""

    _synchronized_data_class = SynchronizedData
    _event_class = Event


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
            },
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
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            ObservationPayload(
                participant, project_details=json.dumps(payload_data)
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

        actual_next_state = self.synchronized_data.update(
            participant_to_project=test_round.serialize_collection(test_round.collection),
            most_voted_project=test_round.most_voted_payload,
            most_recent_project=123,
            inactive_projects=inactive_projects,
            active_projects=active_projects,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_project
            == cast(SynchronizedData, actual_next_state).most_voted_project
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_project[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
                ).participant_to_project.items()
            ]
        )

        assert event == Event.DONE


class TestObservationNoActiveProjectsRound(BaseRoundTestClass):
    """Tests for ObservationRound, no active projects case."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        active_projects = []  # type: ignore
        inactive_projects = [1, 2, 3]
        finished_projects = [4, 5, 6]

        payload_data = {
            "active_projects": active_projects,
            "inactive_projects": inactive_projects,
            "newly_finished_projects": finished_projects,
            "most_recent_project": 123,
        }

        test_round = ObservationRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            ObservationPayload(
                participant, project_details=json.dumps(payload_data)
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

        actual_next_state = self.synchronized_data.update(
            participant_to_project=test_round.serialize_collection(test_round.collection),
            most_voted_project=test_round.most_voted_payload,
            most_recent_project=123,
            inactive_projects=inactive_projects,
            active_projects=active_projects,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_project
            == cast(SynchronizedData, actual_next_state).most_voted_project
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_project[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
                ).participant_to_project.items()
            ]
        )

        assert event == Event.NO_ACTIVE_PROJECTS


class TestPositiveDecisionRound(BaseRoundTestClass):
    """Tests for DecisionRound, when the decision is positive."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = {"project_id": 123}

        test_round = DecisionRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            DecisionPayload(participant, decision=json.dumps(payload_data))
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

        actual_next_state = self.synchronized_data.update(
            participant_to_decision=test_round.serialize_collection(test_round.collection),
            most_voted_decision=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_decision
            == cast(SynchronizedData, actual_next_state).most_voted_decision
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_decision[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
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
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        project_to_purchase: Dict = {}  # {} represents a NO decision for now

        first_payload, *payloads = [
            DecisionPayload(
                participant, decision=json.dumps(project_to_purchase)
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

        actual_next_state = self.synchronized_data.update(
            participant_to_decision=test_round.serialize_collection(test_round.collection),
            most_voted_decision=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_decision
            == cast(SynchronizedData, actual_next_state).most_voted_decision
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_decision[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
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
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            TransactionPayload(participant, purchase_data=test_purchase_data)
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

        actual_next_state = self.synchronized_data.update(
            participant_to_purchase_data=test_round.serialize_collection(test_round.collection),
            most_voted_purchase_data=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_purchase_data
            == cast(SynchronizedData, actual_next_state).most_voted_purchase_data
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_purchase_data[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
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
        test_details = json.dumps({"active_projects": [{"data": "more"}]})

        test_round = DetailsRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            DetailsPayload(participant, details=test_details)
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

        actual_next_state = self.synchronized_data.update(
            participant_to_details=test_round.serialize_collection(test_round.collection),
            active_projects=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert cast(SynchronizedData, state).db.get_strict("active_projects") == cast(
            SynchronizedData, actual_next_state
        ).db.get("active_projects")

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_details[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
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
        test_funds = {"0x0": WEI_TO_ETH}

        test_round = FundingRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            FundingPayload(participant, address_to_funds=json.dumps(test_funds))
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

        actual_next_state = self.synchronized_data.update(
            participant_to_funds=test_round.serialize_collection(test_round.collection),
            most_voted_funds=test_round.most_voted_payload,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert (
            cast(SynchronizedData, state).most_voted_funds
            == cast(SynchronizedData, actual_next_state).most_voted_funds
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(SynchronizedData, state).participant_to_funds[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    SynchronizedData, actual_next_state
                ).participant_to_funds.items()
            ]
        )

        assert event == Event.DONE


class TestProcessPurchaseRound(BaseRoundTestClass):
    """Tests for ProcessPurchaseRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        test_project = 123
        test_nft = 10000
        purchased_projects = [120, 121, 122]

        initial_state = deepcopy(
            self.synchronized_data.update(
                project_to_purchase=test_project,
                purchased_projects=purchased_projects,
            )
        )

        test_round = ProcessPurchaseRound(
            synchronized_data=initial_state, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            PurchasedNFTPayload(participant, purchased_nft=test_nft)
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

        actual_purchased_projects = purchased_projects.copy()
        actual_purchased_projects.append(test_nft)
        actual_next_state = initial_state.update(
            purchased_nft=test_nft,
            purchased_projects=actual_purchased_projects,
        )

        res = test_round.end_block()

        assert res is not None

        state, event = res

        assert cast(SynchronizedData, state).db.get_strict("purchased_nft") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("purchased_nft")
        assert cast(SynchronizedData, state).db.get_strict("purchased_projects") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("purchased_projects")

        assert event == Event.DONE


class TestTransferNFTRound(BaseRoundTestClass):
    """Tests for TransferNFTRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        initial_state = deepcopy(
            self.synchronized_data.update(
                purchased_nft=123,
            )
        )

        test_round = TransferNFTRound(
            synchronized_data=initial_state, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            TransferNFTPayload(participant, transfer_data="0x123")
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

        actual_next_state = initial_state.update(
            tx_submitter=TransferNFTRound.auto_round_id(),
        )

        res = test_round.end_block()

        assert res is not None

        state, event = res

        assert cast(SynchronizedData, state).db.get_strict("tx_submitter") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("tx_submitter")

        assert event == Event.DONE


class TestPayoutFractionsRound(BaseRoundTestClass):
    """Tests for PayoutFractionsRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        initial_state = deepcopy(self.synchronized_data)

        test_round = PayoutFractionsRound(
            synchronized_data=initial_state, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            PayoutFractionsPayload(
                participant,
                payout_fractions=json.dumps({"encoded": "0x0", "raw": {"0x0": 123}}),
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

        actual_next_state = initial_state.update(
            most_voted_tx_hash="0x0",
            users_being_paid={"0x0": 123},
            tx_submitter=PayoutFractionsRound.auto_round_id(),
        )

        res = test_round.end_block()

        assert res is not None

        state, event = res

        assert cast(SynchronizedData, state).db.get_strict("most_voted_tx_hash") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("most_voted_tx_hash")
        assert cast(SynchronizedData, state).db.get_strict("users_being_paid") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("users_being_paid")
        assert cast(SynchronizedData, state).db.get_strict("tx_submitter") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("tx_submitter")

        assert event == Event.DONE


class TestPostPayoutRound(BaseRoundTestClass):
    """Tests for PostPayoutRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""

        initial_state = deepcopy(
            self.synchronized_data.update(
                paid_users={"0x1": 1},
                users_being_paid={"0x1": 2, "0x2": 1},
            )
        )
        test_round = PostPayoutRound(
            synchronized_data=initial_state, context=mock.MagicMock()
        )

        # NOTE: No payload for this round.

        actual_next_state = initial_state.update(
            users_being_paid={},
            paid_users={"0x1": 3, "0x2": 1},
        )

        res = test_round.end_block()

        assert res is not None

        state, event = res

        assert cast(SynchronizedData, state).db.get_strict("users_being_paid") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("users_being_paid")
        assert cast(SynchronizedData, state).db.get_strict("paid_users") == cast(
            SynchronizedData, actual_next_state
        ).db.get_strict("paid_users")

        assert event == Event.DONE


class TestPostTransactionSettlementRound(BaseRoundTestClass):
    """Tests for PostTransactionSettlementRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        test_payload_data = {"amount_spent": 123}

        self.synchronized_data.update(tx_submitter=TransactionRound.auto_round_id())
        test_round = PostTransactionSettlementRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            PostTxPayload(
                participant, post_tx_data=json.dumps(test_payload_data)
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

        actual_next_state = self.synchronized_data.update(
            amount_spent=123,
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert cast(SynchronizedData, state).db.get("amount_spent") == cast(
            SynchronizedData, actual_next_state
        ).db.get("amount_spent")

        assert event == PostTransactionSettlementEvent.EL_COLLECTOOORR_DONE


class TestResyncRound(BaseRoundTestClass):
    """Tests for ResyncRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        test_payload_data = {
            "amount_spent": 1,
            "basket_addresses": ["0x0"],
            "vault_addresses": ["0x1"],
            "purchased_projects": [0],
            "paid_users": {"0x2": 1},
        }

        test_round = ResyncRound(
            synchronized_data=self.synchronized_data, context=mock.MagicMock()
        )

        first_payload, *payloads = [
            ResyncPayload(participant, resync_data=json.dumps(test_payload_data))
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

        actual_next_state = self.synchronized_data.update(
            amount_spent=1,
            basket_addresses=["0x0"],
            vault_addresses=["0x1"],
            purchased_projects=[0],
            paid_users={"0x2": 1},
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res

        # a new period has started
        # make sure the correct project is chosen
        assert cast(SynchronizedData, state).db.get("amount_spent") == cast(
            SynchronizedData, actual_next_state
        ).db.get("amount_spent")
        assert cast(SynchronizedData, state).db.get("basket_addresses") == cast(
            SynchronizedData, actual_next_state
        ).db.get("basket_addresses")
        assert cast(SynchronizedData, state).db.get("vault_addresses") == cast(
            SynchronizedData, actual_next_state
        ).db.get("vault_addresses")
        assert cast(SynchronizedData, state).db.get("purchased_projects") == cast(
            SynchronizedData, actual_next_state
        ).db.get("purchased_projects")
        assert cast(SynchronizedData, state).db.get("paid_users") == cast(
            SynchronizedData, actual_next_state
        ).db.get("paid_users")

        assert event == Event.DONE


def test_rotate_list_method() -> None:
    """Test `rotate_list` method."""

    ex_list = [1, 2, 3, 4, 5]
    assert rotate_list(ex_list, 2) == [3, 4, 5, 1, 2]


def test_synchronized_data() -> None:  # pylint: disable=too-many-locals
    """Test SynchronizedData."""

    participants = get_participants()
    period_count = 0
    period_setup_params = {}  # type: ignore
    participant_to_randomness = {
        participant: RandomnessPayload(
            participant, randomness=RANDOMNESS, round_id=0
        )
        for participant in participants
    }
    most_voted_randomness = "0xabcd"
    participant_to_selection = {
        participant: SelectKeeperPayload(participant, keepers="keeper")
        for participant in participants
    }
    most_voted_keeper_address = "keeper"

    synchronized_data = SynchronizedData(
        StateDB(
            setup_data=StateDB.data_to_lists(
                dict(
                    participants=participants,
                    period_count=period_count,
                    period_setup_params=period_setup_params,
                    participant_to_randomness=CollectionRound.serialize_collection(participant_to_randomness),
                    most_voted_randomness=most_voted_randomness,
                    participant_to_selection=CollectionRound.serialize_collection(participant_to_selection),
                    most_voted_keeper_address=most_voted_keeper_address,
                )
            ),
        )
    )

    assert synchronized_data.participants == frozenset(participants)
    assert synchronized_data.period_count == period_count
    assert synchronized_data.participant_to_randomness == participant_to_randomness
    assert synchronized_data.most_voted_randomness == most_voted_randomness
    assert synchronized_data.participant_to_selection == participant_to_selection
    assert synchronized_data.most_voted_keeper_address == most_voted_keeper_address
    assert synchronized_data.sorted_participants == sorted(participants)
    assert synchronized_data.keeper_randomness == cast(
        float, (int(most_voted_randomness, base=16) // 10 ** 0 % 10) / 10
    )
