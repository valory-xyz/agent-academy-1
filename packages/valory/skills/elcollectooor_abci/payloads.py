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
import json
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
    DETAILS = "details"
    DECISION = "decision"
    TRANSACTION = "transaction"

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
    """Represent a transaction payload of type 'observation'."""

    transaction_type = TransactionType.OBSERVATION

    def __init__(
        self, sender: str, project_details: Dict, id_: Optional[str] = None
    ) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param project_details: the observed project id
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._project_details = json.dumps(project_details)

    @property
    def project_details(self) -> str:
        return self._project_details

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(project_details=self.project_details)


class DecisionPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'decision'."""

    transaction_type = TransactionType.DECISION

    def __init__(self, sender: str, decision: int, id_: Optional[str] = None) -> None:
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


class DetailsPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'Details'"""

    transaction_type = TransactionType.DETAILS

    def __init__(self, sender: str, details: str, id_: Optional[str] = None) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param details: the necessary info to create a tx for
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._details = details

    @property
    def details(self):
        """Get the details"""
        return self._details

    @property
    def data(self):
        """Get the data"""
        return dict(details=self.details)


class TransactionPayload(BaseElCollectooorAbciPayload):
    """Represent a transaction payload of type 'transaction'."""

    transaction_type = TransactionType.TRANSACTION

    def __init__(
        self, sender: str, purchase_data: str, id_: Optional[str] = None
    ) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param purchase_data: the necessary info to create a tx for
        :param id_: the id of the transaction
        """
        super().__init__(sender, id_)
        self._purchase_data = purchase_data

    @property
    def purchase_data(self) -> str:
        """Get the decision."""
        return self._purchase_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(purchase_data=self.purchase_data)
