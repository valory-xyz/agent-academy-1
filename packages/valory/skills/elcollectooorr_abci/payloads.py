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
    TRANSFER_NFT = "transfer_nft"
    PURCHASED_NFT = "purchased_nft"
    FUNDING = "funding"
    PAYOUT_FRACTIONS = "payout_fractions"
    PAID_FRACTIONS = "paid_fractions"
    POST_TX = "post_tx"

    def __str__(self) -> str:
        """Get the string value of the transaction type."""
        return self.value


class FundingPayload(BaseTxPayload):
    """Funds payload."""

    transaction_type = TransactionType.FUNDING

    def __init__(
            self, sender: str, address_to_funds: str, **kwargs: Any
    ) -> None:
        """Initialize an 'FundsInPeriod' transaction payload.

        :param sender: the sender (Ethereum) address
        :param address_to_funds: stringified json, maps addresses to the funds they provided and their block no.
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._address_to_funds = address_to_funds

    @property
    def address_to_funds(self) -> str:
        """Get the funds."""
        return self._address_to_funds

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(address_to_funds=self.address_to_funds)


class PayoutFractionsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'payout_fractions'."""

    transaction_type = TransactionType.PAYOUT_FRACTIONS

    def __init__(self, sender: str, payout_fractions: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param payout_fractions: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._payout_fractions = payout_fractions

    @property
    def payout_fractions(self) -> str:
        """Get the decision."""
        return self._payout_fractions

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(payout_fractions=self.payout_fractions)


class PaidFractionsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'paid_fractions'."""

    transaction_type = TransactionType.PAID_FRACTIONS

    def __init__(self, sender: str, paid_fractions: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param paid_fractions: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._paid_fractions = paid_fractions

    @property
    def paid_fractions(self) -> str:
        """Get the decision."""
        return self._paid_fractions

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(paid_fractions=self.paid_fractions)


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

    def __init__(self, sender: str, decision: str, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param decision: the chosen project to be purchased.
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._decision = decision

    @property
    def decision(self) -> str:
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


class PurchasedNFTPayload(BaseTxPayload):
    """Represent a transaction payload of type 'purchased_nft'."""

    transaction_type = TransactionType.PURCHASED_NFT

    def __init__(self, sender: str, purchased_nft: int, **kwargs: Any) -> None:
        """Initialize an 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param purchased_nft: the purchased_nft 0 for NO, any other value YES
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._purchased_nft = purchased_nft

    @property
    def purchased_nft(self) -> int:
        """Get the purchased_nft."""
        return self._purchased_nft

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(purchased_nft=self.purchased_nft)


class TransferNFTPayload(BaseTxPayload):
    """Represent a transaction payload of type 'transfer_nft'."""

    transaction_type = TransactionType.TRANSFER_NFT

    def __init__(self, sender: str, transfer_data: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param transfer_data: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._transfer_data = transfer_data

    @property
    def transfer_data(self) -> str:
        """Get the decision."""
        return self._transfer_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(transfer_data=self.transfer_data)


class PostTxPayload(BaseTxPayload):
    """Represent a transaction payload of type 'post_tx'."""

    transaction_type = TransactionType.POST_TX

    def __init__(self, sender: str, post_tx_data: str, **kwargs: Any) -> None:
        """Initialize a 'rest' transaction payload.

        :param sender: the sender (Ethereum) address
        :param post_tx_data: the necessary info to create a tx for
        :param kwargs: the keyword arguments
        """
        super().__init__(sender, **kwargs)
        self._post_tx_data = post_tx_data

    @property
    def post_tx_data(self) -> str:
        """Get the decision."""
        return self._post_tx_data

    @property
    def data(self) -> Dict:
        """Get the data."""
        return dict(post_tx_data=self.post_tx_data)
