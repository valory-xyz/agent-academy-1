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

"""This module contains the transaction payloads for the elcollectooor_abci app."""
from abc import ABC
from enum import Enum
from typing import Dict, Optional

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


class TransactionType(Enum):
    """Enumeration of transaction types."""

    REGISTRATION = "registration"
    RANDOMNESS = "randomness"
    SELECT_KEEPER = "select_keeper"
    RESET = "reset"
    OBSERVATION = "observation"
    DECISION = "decision"

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class BaseElCollectooorAbciPayload(BaseTxPayload, ABC):
    """Base class for the simple abci demo."""

    def __hash__(self) -> int:
        """Hash the payload."""
        return hash(tuple(sorted(self.data.items())))


class RegistrationPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'registration'."""

    transaction_type = TransactionType.REGISTRATION


class RandomnessPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'randomness'."""

    transaction_type = TransactionType.RANDOMNESS

    def __init__(
            self, sender: str, round_id: int, randomness: str, id_: Optional[str] = None
    ) -> None:
        """Initialize an 'select_keeper' transaction payload.

        :param sender: the sender (Ethereum) address
        :param round_id: the round id
        :param randomness: the randomness
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._round_id = round_id
        self._randomness = randomness

    @property
    def round_id(self) -> int:
        """Get the round id."""
        return self._round_id

    @property
    def randomness(self) -> str:
        """Get the randomness."""
        return self._randomness

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(round_id=self._round_id, randomness=self._randomness)


class SelectKeeperPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'select_keeper'."""

    transaction_type = TransactionType.SELECT_KEEPER

    def __init__(self, sender: str, keeper: str, id_: Optional[str] = None) -> None:
        """Initialize an 'select_keeper' transaction payload.

        :param sender: the sender (Ethereum) address
        :param keeper: the keeper selection
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._keeper = keeper

    @property
    def keeper(self) -> str:
        """Get the keeper."""
        return self._keeper

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(keeper=self.keeper)


class ResetPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'reset'."""

    transaction_type = TransactionType.RESET

    def __init__(
            self, sender: str, period_count: int, id_: Optional[str] = None
    ) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param period_count: the period count id
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._period_count = period_count

    @property
    def period_count(self) -> int:
        """Get the period_count."""
        return self._period_count

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(period_count=self.period_count)


class ObservationPayload(BaseElCollectooorAbciPayload):
    transaction_type = TransactionType.OBSERVATION

    """Represent a transaction payload of type 'observation'."""

    def __init__(
            self, sender: str, project_details: Dict, id_: Optional[str] = None
    ) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param project_id: the observed project id
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._project_details = project_details

    @property
    def project_details(self):
        return self._project_details

    @property
    def data(self) -> Dict:
        """Get the data."""
        return self.project_details


class DecisionPayload(BaseElCollectooorAbciPayload):
    transaction_type = TransactionType.DECISION

    """Represent a transaction payload of type 'observation'."""

    def __init__(
            self, sender: str, decision: int, id_: Optional[str] = None
    ) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param decision: the decision 0 for NO, any other value YES
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._decision = decision

    @property
    def decision(self) -> int:
        """Get the decision."""
        return self._decision

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(decision=self.decision)
