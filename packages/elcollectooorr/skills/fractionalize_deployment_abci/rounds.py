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

"""This module contains the data classes for the Fractionalize Deployment ABCI application."""
import json
from abc import ABC
from enum import Enum
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple, Type, cast

from packages.elcollectooorr.skills.fractionalize_deployment_abci.payloads import (
    BasketAddressesPayload,
    DeployBasketPayload,
    DeployDecisionPayload,
    DeployVaultPayload,
    PermissionVaultFactoryPayload,
    VaultAddressesPayload,
)
from packages.valory.skills.abstract_round_abci.base import (
    AbciApp,
    AbciAppTransitionFunction,
    AbstractRound,
    AppState,
    BaseSynchronizedData,
    CollectSameUntilThresholdRound,
    DegenerateRound,
    get_name,
)


class Event(Enum):
    """Event enumeration for the Fractionalize Deploymenround_wrapper."""

    DONE = "done"
    ROUND_TIMEOUT = "round_timeout"
    NO_MAJORITY = "no_majority"
    RESET_TIMEOUT = "reset_timeout"
    DECIDED_YES = "decided_yes"
    DECIDED_NO = "decided_no"
    DECIDED_SKIP = "decided_skip"
    ERROR = "error"


class SynchronizedData(BaseSynchronizedData):  # pylint: disable=too-many-instance-attributes
    """
    Class to represent the synchronized data.

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

    @property
    def most_voted_tx_hash(self) -> str:
        """Get most voted tx hash"""
        return cast(str, self.db.get_strict("most_voted_tx_hash"))

    @property
    def final_tx_hash(self) -> str:
        """Get final tx hash"""
        return cast(str, self.db.get_strict("final_tx_hash"))

    @property
    def amount_spent(self) -> int:
        """Get amount spent"""
        return cast(int, self.db.get("amount_spent", 0))


class FractionalizeDeploymentABCIAbstractRound(
    AbstractRound, ABC
):
    """Abstract round for the FractionalizeDeployment skill."""

    @property
    def synchronized_data(self) -> SynchronizedData:
        """Return the period state."""
        return cast(SynchronizedData, super().synchronized_data)

    def _return_no_majority_event(self) -> Tuple[SynchronizedData, Event]:
        """
        Trigger the NO_MAJORITY evenround_wrapper.

        :return: a new period state and a NO_MAJORITY event
        """
        return self.synchronized_data, Event.NO_MAJORITY


class DeployDecisionRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """Round to check whether deployment is necessary"""

    payload_class = DeployDecisionPayload
    payload_attribute = "deploy_decision"
    synchronized_data_class = SynchronizedData
    DECIDE_DEPLOY_FULL = "deploy_full"
    DECIDE_SKIP_BASKET = "deploy_skip_basket"
    DECIDE_DONT_DEPLOY = "dont_deploy"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_deploy_decision=self.collection,
                most_voted_deploy_decision=self.most_voted_payload,
            )

            if self.most_voted_payload == self.DECIDE_DEPLOY_FULL:
                return state.update(amount_spent=0), Event.DECIDED_YES
            if self.most_voted_payload == self.DECIDE_SKIP_BASKET:
                return state, Event.DECIDED_SKIP

            return state, Event.DECIDED_NO

        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedWithoutDeploymentRound(DegenerateRound):
    """Degenerate round when no deployment should be made"""


class FinishedWithBasketDeploymentSkippedRound(DegenerateRound):
    """Degenerate round when a basket shouldn't be deployed."""


class DeployBasketTxRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """Defines the Deploy Basket Round"""

    payload_class = DeployBasketPayload
    payload_attribute = "deploy_basket"
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.synchronized_data, Event.ERROR

            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_voted_tx_hash=self.collection,
                most_voted_tx_hash=self.most_voted_payload,
                tx_submitter=self.round_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedDeployBasketTxRound(DegenerateRound):
    """This class represents the finished round during operation."""


class DeployVaultTxRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """Defines the Deploy Vault Round"""

    payload_class = DeployVaultPayload
    payload_attribute = "deploy_vault"
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.synchronized_data, Event.ERROR

            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_voted_tx_hash=self.collection,
                most_voted_tx_hash=self.most_voted_payload,
                tx_submitter=self.round_id,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedDeployVaultTxRound(DegenerateRound):
    """This class represents the finished round during operation."""


class BasketAddressRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the post basket deployment round"""

    payload_class = BasketAddressesPayload
    payload_attribute = "basket_addresses"
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.synchronized_data, Event.ERROR

            basket_addresses = json.loads(self.most_voted_payload)

            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_basket_addresses=self.collection,
                basket_addresses=basket_addresses,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class PermissionVaultFactoryRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the round where the vault factory is permission with the basket"""

    payload_class = PermissionVaultFactoryPayload
    payload_attribute = "permission_factory"
    synchronized_data_class = SynchronizedData

    SKIP_PERMISSION = "no_permissioning"

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.synchronized_data, Event.ERROR
            if self.most_voted_payload == self.SKIP_PERMISSION:
                return self.synchronized_data, Event.DECIDED_NO

            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_voted_tx_hash=self.collection,
                most_voted_tx_hash=self.most_voted_payload,
                tx_submitter=self.round_id,
            )

            return state, Event.DECIDED_YES
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedPostBasketRound(DegenerateRound):
    """This class represents the last round of the PostBasketDeploymentAbci"""


class FinishedPostBasketWithoutPermissionRound(DegenerateRound):
    """This class represents the last round of the PostBasketDeploymentAbci"""


class VaultAddressRound(
    CollectSameUntilThresholdRound, FractionalizeDeploymentABCIAbstractRound
):
    """This class represents the post vault deployment round"""

    payload_class = VaultAddressesPayload
    payload_attribute = "vault_addresses"
    synchronized_data_class = SynchronizedData

    def end_block(self) -> Optional[Tuple[BaseSynchronizedData, Event]]:
        """Process the end of the block."""
        if self.threshold_reached:
            if self.most_voted_payload == "":
                return self.synchronized_data, Event.ERROR

            vault_addresses = cast(Dict[str, int], json.loads(self.most_voted_payload))
            state = self.synchronized_data.update(
                synchronized_data_class=self.synchronized_data_class,
                participant_to_voted_tx_hash=self.collection,
                vault_addresses=vault_addresses,
            )

            return state, Event.DONE
        if not self.is_majority_possible(
            self.collection, self.synchronized_data.nb_participants
        ):
            return self._return_no_majority_event()
        return None


class FinishedPostVaultRound(DegenerateRound):
    """This class represents the last round of the PostVaultDeploymentAbci"""


class DeployBasketAbciApp(AbciApp[Event]):
    """The base logic of Deploying Basket Abci app."""

    initial_round_cls: Type[AbstractRound] = DeployDecisionRound
    transition_function: AbciAppTransitionFunction = {
        DeployDecisionRound: {
            Event.DECIDED_YES: DeployBasketTxRound,
            Event.DECIDED_SKIP: FinishedWithBasketDeploymentSkippedRound,
            Event.DECIDED_NO: FinishedWithoutDeploymentRound,
            Event.NO_MAJORITY: DeployDecisionRound,
        },
        DeployBasketTxRound: {
            Event.DONE: FinishedDeployBasketTxRound,
            Event.ERROR: FinishedWithoutDeploymentRound,
            Event.NO_MAJORITY: DeployBasketTxRound,
        },
        FinishedDeployBasketTxRound: {},
        FinishedWithoutDeploymentRound: {},
        FinishedWithBasketDeploymentSkippedRound: {},
    }
    final_states: Set[AppState] = {
        FinishedDeployBasketTxRound,
        FinishedWithoutDeploymentRound,
        FinishedWithBasketDeploymentSkippedRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }
    db_pre_conditions: Dict[AppState, List[str]] = {DeployDecisionRound: []}
    db_post_conditions: Dict[AppState, List[str]] = {
        FinishedDeployBasketTxRound: [get_name(SynchronizedData.most_voted_tx_hash)],
        FinishedWithoutDeploymentRound: [],
        FinishedWithBasketDeploymentSkippedRound: []
    }


class PostBasketDeploymentAbciApp(AbciApp[Event]):
    """The base logic of Post Deployment Basket Abci app."""

    initial_round_cls: Type[AbstractRound] = BasketAddressRound
    transition_function: AbciAppTransitionFunction = {
        BasketAddressRound: {
            Event.DONE: PermissionVaultFactoryRound,
            Event.ERROR: BasketAddressRound,
            Event.NO_MAJORITY: BasketAddressRound,
        },
        PermissionVaultFactoryRound: {
            Event.DECIDED_YES: FinishedPostBasketRound,
            Event.DECIDED_NO: FinishedPostBasketWithoutPermissionRound,
            Event.ERROR: PermissionVaultFactoryRound,
            Event.NO_MAJORITY: PermissionVaultFactoryRound,
        },
        FinishedPostBasketRound: {},
        FinishedPostBasketWithoutPermissionRound: {},
    }
    final_states: Set[AppState] = {
        FinishedPostBasketRound,
        FinishedPostBasketWithoutPermissionRound,
    }
    event_to_timeout: Dict[Event, float] = {
        Event.ROUND_TIMEOUT: 30.0,
        Event.RESET_TIMEOUT: 30.0,
    }
    cross_period_persisted_keys = [get_name(SynchronizedData.basket_addresses)]
    db_pre_conditions: Dict[AppState, List[str]] = {BasketAddressRound: []}
    db_post_conditions: Dict[AppState, List[str]] = {
        FinishedPostBasketRound: [get_name(SynchronizedData.most_voted_tx_hash), get_name(SynchronizedData.basket_addresses)],
        FinishedPostBasketWithoutPermissionRound: [get_name(SynchronizedData.basket_addresses)],
    }


class DeployVaultAbciApp(AbciApp[Event]):
    """The base logic of Deploying Vault Abci app."""

    initial_round_cls: Type[AbstractRound] = DeployVaultTxRound
    transition_function: AbciAppTransitionFunction = {
        DeployVaultTxRound: {
            Event.DONE: FinishedDeployVaultTxRound,
            Event.ERROR: DeployVaultTxRound,
            Event.NO_MAJORITY: DeployVaultTxRound,
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
    db_pre_conditions: Dict[AppState, List[str]] = {DeployVaultTxRound: []}
    db_post_conditions: Dict[AppState, List[str]] = {
        FinishedDeployVaultTxRound: [get_name(SynchronizedData.most_voted_tx_hash)],
    }


class PostVaultDeploymentAbciApp(AbciApp[Event]):
    """The base logic of Post Deployment Vault Abci app."""

    initial_round_cls: Type[AbstractRound] = VaultAddressRound
    transition_function: AbciAppTransitionFunction = {
        VaultAddressRound: {
            Event.DONE: FinishedPostVaultRound,
            Event.ERROR: VaultAddressRound,
            Event.NO_MAJORITY: VaultAddressRound,
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
    cross_period_persisted_keys = [get_name(SynchronizedData.vault_addresses)]
    db_pre_conditions: Dict[AppState, List[str]] = {VaultAddressRound: []}
    db_post_conditions: Dict[AppState, List[str]] = {
        FinishedPostVaultRound: [get_name(SynchronizedData.vault_addresses)],
    }
