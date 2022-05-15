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

"""This module contains the transaction payloads for the safe deployment app."""

from enum import Enum
from typing import Any, Dict

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


class TransactionType(Enum):
    """Enumeration of transaction types."""

    PURCHASE_TOKEN = "purchase_token"
    VALIDATE = "validate_safe"
    RANDOMNESS = "randomness_safe"
    SELECT_KEEPER = "select_keeper_safe"
    FUNDING_TX = "funding_tx"

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class RandomnessPayload(BaseTxPayload):
    """Represent a transaction payload of type 'randomness'."""

    transaction_type = TransactionType.RANDOMNESS

    def __init__(
        self, sender: str, round_id: int, randomness: str, **kwargs: Any
    ) -> None:
        """Initialize an 'select_keeper' transaction payload.

        :param sender: the sender (Ethereum) address
        :param round_id: the round id
        :param randomness: the randomness
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
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


class SelectKeeperPayload(BaseTxPayload):
    """Represent a transaction payload of type 'select_keeper'."""

    transaction_type = TransactionType.SELECT_KEEPER

    def __init__(self, sender: str, keeper: str, **kwargs: Any) -> None:
        """Initialize an 'select_keeper' transaction payload.

        :param sender: the sender (Ethereum) address
        :param keeper: the keeper selection
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._keeper = keeper

    @property
    def keeper(self) -> str:
        """Get the keeper."""
        return self._keeper

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(keeper=self.keeper)


class ValidatePayload(BaseTxPayload):
    """Represent a transaction payload of type 'validate'."""

    transaction_type = TransactionType.VALIDATE

    def __init__(self, sender: str, validation_data: str, **kwargs: Any) -> None:
        """Initialize an 'validate' transaction payload.

        :param sender: the sender (Ethereum) address
        :param validation_data: the vote
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._validation_data = validation_data

    @property
    def validation_data(self) -> str:
        """Get the vote."""
        return self._validation_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return (
            dict(validation_data=self.validation_data)
            if self.validation_data is not None
            else {}
        )


class PurchaseTokenPayload(BaseTxPayload):
    """Represent a transaction payload of type 'purchase_token'."""

    transaction_type = TransactionType.PURCHASE_TOKEN

    def __init__(self, sender: str, purchase_data: str, **kwargs: Any) -> None:
        """Initialize a 'deploy_safe' transaction payload.

        :param sender: the sender (Ethereum) address
        :param purchase_data: the Safe contract address
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._purchase_data = purchase_data

    @property
    def purchase_data(self) -> str:
        """Get the Safe contract address."""
        return self._purchase_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(purchase_data=self.purchase_data)


class FundingTransactionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'funding_tx'."""

    transaction_type = TransactionType.FUNDING_TX

    def __init__(self, sender: str, funding_tx_data: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param funding_tx_data: the necessary info to create a tx for funding the keeper
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._funding_tx_data = funding_tx_data

    @property
    def funding_tx_data(self) -> str:
        """Get the decision."""
        return self._funding_tx_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(funding_tx_data=self.funding_tx_data)
