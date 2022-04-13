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

"""This module contains the data classes for the Fractionalize Deployment ABCI application."""
import struct
from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import List, Mapping, Optional, Sequence, Tuple, cast, Type, Dict, Set

from packages.valory.skills.abstract_round_abci.abci_app_chain import chain, AbciAppTransitionMapping
from packages.valory.skills.abstract_round_abci.base import (
    AbstractRound,
    BasePeriodState,
    CollectSameUntilThresholdRound,
    DegenerateRound, AbciApp, AbciAppTransitionFunction, AppState,
)
from packages.valory.skills.fractionalize_deployment_abci.payloads import (

    TransactionType, DeployBasketPayload, DeployVaultPayload)
from packages.valory.skills.registration_abci.rounds import FinishedRegistrationRound, FinishedRegistrationFFWRound, \
    RegistrationRound, AgentRegistrationAbciApp
from packages.valory.skills.safe_deployment_abci.rounds import FinishedSafeRound, SafeDeploymentAbciApp
from packages.valory.skills.transaction_settlement_abci.rounds import TransactionRounds, TransactionSubmissionAbciApp


class Event(Enum):
    """Event enumeration for the Fractionalize Deploymenround_wrapper."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DECIDED_YES = "decided_yes"
    DECIDED_NO = "decided_no"
    GIB_DETAILS = "gib_details"
    ERROR = "error"


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

        This property is useful when interacting with the Safe contracround_wrapper.

        :return: the sorted participants' addresses
        """
        return sorted(self.participants, key=str.lower)

    @property
    def most_voted_decision(self) -> int:
        """Get the most_voted_decision."""
        return cast(int, self.db.get_strict("most_voted_decision"))

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


class FractionalizeDeploymentABCIAbstractRound(AbstractRound[Event, TransactionType], ABC):
    """Abstract round for the FractionalizeDeployment skill."""

    @property
    def period_state(self) -> PeriodState:
        """Return the period state."""
        return cast(PeriodState, self._state)

    def _return_no_majority_event(self) -> Tuple[PeriodState, Event]:
        """
        Trigger the NO_MAJORITY evenround_wrapper.

        :return: a new period state and a NO_MAJORITY event
        """
        return self.period_state, Event.NO_MAJORITY


class DeployBasketTxRound(CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound):
    """Defines the Deploy Basket Round"""

    allowed_tx_type = DeployBasketPayload.transaction_type
    round_id = "deploy_basket_round"
    payload_attribute = "deploy_basket"
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
            )

            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedDeployBasketTxRound(DegenerateRound, ABC):
    """This class represents the finished round during operation."""

    round_id = "finished_basket_tx_deployment"


class DeployVaultTxRound(CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound):
    """Defines the Deploy Vault Round"""

    allowed_tx_type = DeployVaultPayload.transaction_type
    round_id = "deploy_vault_round"
    payload_attribute = "deploy_vault"
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
            )

            return state, Event.DONE
        if not self.is_majority_possible(
                self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedDeployVaultTxRound(DegenerateRound):
    """This class represents the finished round during operation."""

    round_id = "finished_vault_tx_deployment"


class VaultTransactionRounds(TransactionRounds):
    """Wrapper around transaction rounds"""


class BasketTransactionRounds(TransactionRounds):
    """Wrapper around transaction rounds"""


class VaultTransactionSubmissionAbciApp(TransactionSubmissionAbciApp):
    """Wrapper around transaction rounds"""
    round_wrapper = VaultTransactionRounds


class BasketTransactionSubmissionAbciApp(TransactionSubmissionAbciApp):
    """Wrapper around transaction rounds"""
    round_wrapper = BasketTransactionRounds


class DeployBasketAbciApp(AbciApp[Event]):
    """The base logic of Deploying Basket Abci app."""

    initial_round_cls: Type[AbstractRound] = DeployBasketTxRound
    transition_function: AbciAppTransitionFunction = {
        DeployBasketTxRound: {
            Event.DONE: FinishedDeployBasketTxRound
        },
        FinishedDeployBasketTxRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDeployBasketTxRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class DeployVaultAbciApp(AbciApp[Event]):
    """The base logic of Deploying Vault Abci app."""

    initial_round_cls: Type[AbstractRound] = DeployVaultTxRound
    transition_function: AbciAppTransitionFunction = {
        DeployVaultTxRound: {
            Event.DONE: FinishedDeployVaultTxRound
        },
        FinishedDeployVaultTxRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDeployVaultTxRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


fracionalize_deployment_app_transition_mapping: AbciAppTransitionMapping = {
    FinishedRegistrationRound: SafeDeploymentAbciApp.initial_round_cls,
    FinishedSafeRound: DeployBasketAbciApp.initial_round_cls,
    FinishedRegistrationFFWRound: DeployBasketAbciApp.initial_round_cls,
    FinishedDeployBasketTxRound: BasketTransactionSubmissionAbciApp.initial_round_cls,
    BasketTransactionRounds.FinishedTransactionSubmissionRound: DeployVaultAbciApp.initial_round_cls,
    FinishedDeployVaultTxRound: VaultTransactionSubmissionAbciApp.initial_round_cls,
    VaultTransactionRounds.FinishedTransactionSubmissionRound: DeployVaultAbciApp.initial_round_cls,
    BasketTransactionRounds.FailedRound: RegistrationRound,
    VaultTransactionRounds.FailedRound: RegistrationRound,
}

FractionalizeDeploymentAbciApp = chain(
    (
        AgentRegistrationAbciApp,
        SafeDeploymentAbciApp,
        DeployBasketAbciApp,
        BasketTransactionSubmissionAbciApp,
        DeployVaultAbciApp,
        VaultTransactionSubmissionAbciApp,
    ),
    fracionalize_deployment_app_transition_mapping,
)
