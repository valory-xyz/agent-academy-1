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
from dataclasses import dataclass

from packages.valory.skills.abstract_round_abci.base import BaseTxPayload


@dataclass(frozen=True)
class FundingPayload(BaseTxPayload):
    """Funds payload."""

    address_to_funds: str


@dataclass(frozen=True)
class PayoutFractionsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'payout_fractions'."""

    payout_fractions: str


@dataclass(frozen=True)
class PaidFractionsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'paid_fractions'."""

    paid_fractions: str


@dataclass(frozen=True)
class ResyncPayload(BaseTxPayload):
    """Represent a resync transaction."""

    resync_data: str


@dataclass(frozen=True)
class ResetPayload(BaseTxPayload):
    """Represent a transaction payload of type 'reset'."""

    period_count: int


@dataclass(frozen=True)
class ObservationPayload(BaseTxPayload):
    """Represent a transaction payload of type 'observation'."""

    project_details: str


@dataclass(frozen=True)
class DecisionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'decision'."""

    decision: str


@dataclass(frozen=True)
class DetailsPayload(BaseTxPayload):
    """Represent a transaction payload of type 'Details'"""

    details: str


@dataclass(frozen=True)
class TransactionPayload(BaseTxPayload):
    """Represent a transaction payload of type 'transaction'."""

    purchase_data: str


@dataclass(frozen=True)
class PurchasedNFTPayload(BaseTxPayload):
    """Represent a transaction payload of type 'purchased_nft'."""

    purchased_nft: int


@dataclass(frozen=True)
class TransferNFTPayload(BaseTxPayload):
    """Represent a transaction payload of type 'transfer_nft'."""

    transfer_data: str


@dataclass(frozen=True)
class PostTxPayload(BaseTxPayload):
    """Represent a transaction payload of type 'post_tx'."""

    post_tx_data: str
