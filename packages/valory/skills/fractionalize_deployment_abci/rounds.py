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
import json
import struct
from abc import ABC
from enum import Enum
from types import MappingProxyType
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple, Type, cast

from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData as BasePeriodState,
    CollectSameUntilThresholdRound,
    DegenerateRound,
)
from packages.valory.skills.fractionalize_deployment_abci.payloads import (
    BasketAddressesPayload,
    DeployBasketPayload,
    DeployDecisionPayload,
    DeployVaultPayload,
    PermissionVaultFactoryPayload,
    TransactionType,
    VaultAddressesPayload,
)


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


class FractionalizeDeploymentABCIAbstractRound(
    AbstractRound[Event, TransactionType], ABC
):
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


class DeployDecisionRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """Round to check whether deployment is necessary"""

    allowed_tx_type = DeployDecisionPayload.transaction_type
    round_id = "deploy_decision_round"
    payload_attribute = "deploy_decision"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_deploy_decision=MappingProxyType(self.collection),
                most_voted_deploy_decision=self.most_voted_payload,
            )

            if self.most_voted_payload:
                return state.update(amount_spent=0), Event.DECIDED_YES

            return state, Event.DECIDED_NO

        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedWithoutDeploymentRound(DegenerateRound):
    """Degenerate round when no deployment should be made"""

    round_id = "finished_without_deployment"


class DeployBasketTxRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
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
                tx_submitter=self.round_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedDeployBasketTxRound(DegenerateRound):
    """This class represents the finished round during operation."""

    round_id = "finished_basket_tx_deployment"


class DeployVaultTxRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
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
                tx_submitter=self.round_id,
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


class BasketAddressRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the post basket deployment round"""

    allowed_tx_type = BasketAddressesPayload.transaction_type
    round_id = "post_deploy_basket_round"
    payload_attribute = "basket_addresses"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.period_state, Event.ERROR

            basket_addresses = json.loads(self.most_voted_payload)

            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_basket_addresses=MappingProxyType(self.collection),
                basket_addresses=basket_addresses,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class PermissionVaultFactoryRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the round where the vault factory is permission with the basket"""

    allowed_tx_type = PermissionVaultFactoryPayload.transaction_type
    round_id = "permission_factory_round"
    payload_attribute = "permission_factory"
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


class FinishedPostBasketRound(DegenerateRound):
    """This class represents the last round of the PostBasketDeploymentAbci"""

    round_id = "finished_post_basket_deployment_round"


class VaultAddressRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the post vault deployment round"""

    allowed_tx_type = VaultAddressesPayload.transaction_type
    round_id = "post_deploy_vault_round"
    payload_attribute = "vault_addresses"
    period_state_class = PeriodState

    def end_block(self) -> Optional[Tuple[BasePeriodState, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.period_state, Event.ERROR

            vault_addresses = cast(Dict[str, int], json.loads(self.most_voted_payload))
            state = self.period_state.update(
                period_state_class=self.period_state_class,
                participant_to_voted_tx_hash=MappingProxyType(self.collection),
                vault_addresses=vault_addresses,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.period_state.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedPostVaultRound(DegenerateRound):
    """This class represents the last round of the PostVaultDeploymentAbci"""

    round_id = "finished_post_vault_deployment_round"


class DeployBasketAbciApp(AbciApp[Event]):
    """The base logic of Deploying Basket Abci app."""

    initial_round_cls: Type[AbstractRound] = DeployDecisionRound
    transition_function: AbciAppTransitionFunction = {
        DeployDecisionRound: {
            Event.DECIDED_YES: DeployBasketTxRound,
            Event.DECIDED_NO: FinishedWithoutDeploymentRound,
        },
        DeployBasketTxRound: {
            Event.DONE: FinishedDeployBasketTxRound,
            Event.ERROR: FinishedWithoutDeploymentRound,
        },
        FinishedDeployBasketTxRound: {},
        FinishedWithoutDeploymentRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDeployBasketTxRound,
        FinishedWithoutDeploymentRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }


class PostBasketDeploymentAbciApp(AbciApp[Event]):
    """The base logic of Post Deployment Basket Abci app."""

    initial_round_cls: Type[AbstractRound] = BasketAddressRound
    transition_function: AbciAppTransitionFunction = {
        BasketAddressRound: {
            Event.DONE: PermissionVaultFactoryRound,
            Event.ERROR: BasketAddressRound,
        },
        PermissionVaultFactoryRound: {
            Event.DONE: FinishedPostBasketRound,
            Event.ERROR: PermissionVaultFactoryRound,
        },
        FinishedPostBasketRound: {},
    }
    final_states: Set[AppState] = {
        FinishedPostBasketRound,
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
            Event.DONE: FinishedDeployVaultTxRound,
            Event.ERROR: DeployVaultTxRound,
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


class PostVaultDeploymentAbciApp(AbciApp[Event]):
    """The base logic of Post Deployment Vault Abci app."""

    initial_round_cls: Type[AbstractRound] = VaultAddressRound
    transition_function: AbciAppTransitionFunction = {
        VaultAddressRound: {
            Event.DONE: FinishedPostVaultRound,
            Event.ERROR: VaultAddressRound,
        },
        FinishedPostVaultRound: {},
    }
    final_states: Set[AppState] = {
        FinishedPostVaultRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }
