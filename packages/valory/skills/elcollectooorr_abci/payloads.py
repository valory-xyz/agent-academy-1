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

"""This module contains the transaction payloads for the elcollectooorr_abci app."""
from enum import Enum
from typing import Any, Dict

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


class ResetPayload(BaseTxPayload):
    """Represent a transaction payload of type 'reset'."""

    transaction_type = TransactionType.RESET

    def __init__(self, sender: str, period_count: int, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param period_count: the period count id
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._period_count = period_count

    @property
    def period_count(self) -> int:
        """Get the period_count."""
        return self._period_count

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(period_count=self.period_count)


class ObservationPayload(BaseTxPayload):
    """Represent a transaction payload of type 'observation'."""

    transaction_type = TransactionType.OBSERVATION

    def __init__(self, sender: str, project_details: str, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param project_details: the observed project id
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._project_details = project_details

    @property
    def project_details(self) -> str:
        """Get project details"""
        return self._project_details

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(project_details=self.project_details)


class DecisionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'decision'."""

    transaction_type = TransactionType.DECISION

    def __init__(self, sender: str, decision: int, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param decision: the decision 0 for NO, any other value YES
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._decision = decision

    @property
    def decision(self) -> int:
        """Get the decision."""
        return self._decision

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(decision=self.decision)


class DetailsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'Details'"""

    transaction_type = TransactionType.DETAILS

    def __init__(self, sender: str, details: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param details: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._details = details

    @property
    def details(self) -> str:
        """Get the details"""
        return self._details

    @property
    def data(self) -> Dict:
        """Get the data"""
        return dict(details=self.details)


class TransactionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'transaction'."""

    transaction_type = TransactionType.TRANSACTION

    def __init__(self, sender: str, purchase_data: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param purchase_data: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._purchase_data = purchase_data

    @property
    def purchase_data(self) -> str:
        """Get the decision."""
        return self._purchase_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(purchase_data=self.purchase_data)
