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

"""Test the base.py module of the skill."""
import json
import logging  # noqa: F401
from typing import Dict, FrozenSet, cast
from unittest import mock

from packages.elcollectooorr.skills.elcollectooorr_abci.rounds import PeriodState
from packages.elcollectooorr.skills.fractionalize_deployment_abci.payloads import (
    BasketAddressesPayload,
    DeployBasketPayload,
    DeployDecisionPayload,
    DeployVaultPayload,
    PermissionVaultFactoryPayload,
    VaultAddressesPayload,
)
from packages.elcollectooorr.skills.fractionalize_deployment_abci.rounds import (
    BasketAddressRound,
    DeployBasketTxRound,
    DeployDecisionRound,
    DeployVaultTxRound,
    Event,
    PermissionVaultFactoryRound,
    VaultAddressRound,
)
from packages.valory.skills.abstract_round_abci.base import AbciAppDB as StateDB
from packages.valory.skills.abstract_round_abci.base import (
    AbstractRound,
    ConsensusParams,
)


WEI_TO_ETH = 10 ** 18
MAX_PARTICIPANTS: int = 4
RANDOMNESS: str = "d1c29dce46f979f9748210d24bce4eae8be91272f5ca1a6aea2832d3dd676f51"


def get_participants() -> FrozenSet[str]:
    """Participants"""
    return frozenset([f"agent_{i}" for i in range(MAX_PARTICIPANTS)])


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
            StateDB(
                setup_data=StateDB.data_to_lists(dict(participants=cls.participants))
            )
        )
        cls.consensus_params = ConsensusParams(max_participants=MAX_PARTICIPANTS)

    def _test_no_majority_event(self, round_obj: AbstractRound) -> None:
        """Test the NO_MAJORITY event."""
        with mock.patch.object(round_obj, "is_majority_possible", return_value=False):
            result = round_obj.end_block()
            assert result is not None
            state, event = result
            assert event == Event.NO_MAJORITY


class TestDeployDecisionRound(BaseRoundTestClass):
    """Tests for DeployDecisionRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        self.period_state.update(amount_spent=WEI_TO_ETH)

        payload_data = "deploy_full"

        test_round = DeployDecisionRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DeployDecisionPayload(sender=participant, deploy_decision=payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_deploy_decision=test_round.collection,
                most_voted_deploy_decision=payload_data,
                amount_spent=0,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("most_voted_deploy_decision") == actual_next_state.db.get(
            "most_voted_deploy_decision"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_deploy_decision"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_deploy_decision")
                ).items()
            ]
        )

        assert event == Event.DECIDED_YES


class TestNoDeployDecisionRound(BaseRoundTestClass):
    """Tests for DeployDecisionRound when there is no deployment."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        self.period_state.update(amount_spent=WEI_TO_ETH)

        payload_data = "dont_deploy"

        test_round = DeployDecisionRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DeployDecisionPayload(sender=participant, deploy_decision=payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_deploy_decision=test_round.collection,
                most_voted_deploy_decision=payload_data,
                amount_spent=WEI_TO_ETH,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        assert state.db.get("most_voted_deploy_decision") == actual_next_state.db.get(
            "most_voted_deploy_decision"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_deploy_decision"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_deploy_decision")
                ).items()
            ]
        )

        assert event == Event.DECIDED_NO


class TestSkipDeployDecisionRound(BaseRoundTestClass):
    """Tests for DeployDecisionRound when there is no vault deployment."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        self.period_state.update(amount_spent=WEI_TO_ETH)

        payload_data = "deploy_skip_basket"

        test_round = DeployDecisionRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DeployDecisionPayload(sender=participant, deploy_decision=payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_deploy_decision=test_round.collection,
                most_voted_deploy_decision=payload_data,
                amount_spent=WEI_TO_ETH,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        assert state.db.get("most_voted_deploy_decision") == actual_next_state.db.get(
            "most_voted_deploy_decision"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_deploy_decision"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_deploy_decision")
                ).items()
            ]
        )

        assert event == Event.DECIDED_SKIP


class TestDeployBasketTxRound(BaseRoundTestClass):
    """Tests for DeployBasketTxRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = "0x0"

        test_round = DeployBasketTxRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DeployBasketPayload(sender=participant, deploy_basket=payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_voted_tx_hash=test_round.collection,
                most_voted_tx_hash=payload_data,
                tx_submitter=DeployBasketTxRound.round_id,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("most_voted_tx_hash") == actual_next_state.db.get(
            "most_voted_tx_hash"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_voted_tx_hash"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_voted_tx_hash")
                ).items()
            ]
        )

        assert event == Event.DONE


class TestDeployVaultTxRound(BaseRoundTestClass):
    """Tests for DeployVaultTxRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = "0x0"

        test_round = DeployVaultTxRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            DeployVaultPayload(sender=participant, deploy_vault=payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_voted_tx_hash=test_round.collection,
                most_voted_tx_hash=payload_data,
                tx_submitter=DeployVaultTxRound.round_id,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("most_voted_tx_hash") == actual_next_state.db.get(
            "most_voted_tx_hash"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_voted_tx_hash"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_voted_tx_hash")
                ).items()
            ]
        )

        assert event == Event.DONE


class TestBasketAddressRound(BaseRoundTestClass):
    """Tests for BasketAddressRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = [0x0, 0x1, 0x2]

        test_round = BasketAddressRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            BasketAddressesPayload(
                sender=participant, basket_addresses=json.dumps(payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_basket_addresses=test_round.collection,
                basket_addresses=payload_data,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("basket_addresses") == actual_next_state.db.get(
            "basket_addresses"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_basket_addresses"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_basket_addresses")
                ).items()
            ]
        )

        assert event == Event.DONE


class TestPermissionVaultFactoryRound(BaseRoundTestClass):
    """Tests for PermissionVaultFactoryRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = 0x0

        test_round = PermissionVaultFactoryRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            PermissionVaultFactoryPayload(
                sender=participant, permission_factory=str(payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_voted_tx_hash=test_round.collection,
                most_voted_tx_hash=payload_data,
                tx_submitter=PermissionVaultFactoryRound.round_id,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("most_voted_tx_hash") == actual_next_state.db.get(
            "most_voted_tx_hash"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_voted_tx_hash"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_voted_tx_hash")
                ).items()
            ]
        )

        assert event == Event.DECIDED_YES


class TestSkipPermissionVaultFactoryRound(BaseRoundTestClass):
    """Tests for PermissionVaultFactoryRound when no permissioning is needed."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = "no_permissioning"

        test_round = PermissionVaultFactoryRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            PermissionVaultFactoryPayload(
                sender=participant, permission_factory=str(payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_voted_tx_hash=test_round.collection,
                most_voted_tx_hash=payload_data,
                tx_submitter=PermissionVaultFactoryRound.round_id,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("most_voted_tx_hash") == actual_next_state.db.get(
            "most_voted_tx_hash"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_voted_tx_hash"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_voted_tx_hash")
                ).items()
            ]
        )

        assert event == Event.DECIDED_NO


class TestVaultAddressRound(BaseRoundTestClass):
    """Tests for VaultAddressRound."""

    def test_run(
        self,
    ) -> None:
        """Run tests."""
        payload_data = [0x0, 0x1, 0x2]

        test_round = VaultAddressRound(
            synchronized_data=self.period_state, consensus_params=self.consensus_params
        )

        first_payload, *payloads = [
            VaultAddressesPayload(
                sender=participant, vault_addresses=json.dumps(payload_data)
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

        actual_next_state = cast(
            PeriodState,
            self.period_state.update(
                participant_to_vault_addresses=test_round.collection,
                vault_addresses=payload_data,
            ),
        )

        res = test_round.end_block()
        assert res is not None
        state, event = res
        state = cast(PeriodState, state)

        # a new period has started
        # make sure the correct project is chosen
        assert state.db.get("vault_addresses") == actual_next_state.db.get(
            "vault_addresses"
        )

        # make sure all the votes are as expected
        assert all(
            [
                cast(Dict, state.db.get("participant_to_vault_addresses"))[participant]
                == actual_vote
                for (participant, actual_vote) in cast(
                    Dict, actual_next_state.db.get("participant_to_vault_addresses")
                ).items()
            ]
        )

        assert event == Event.DONE
