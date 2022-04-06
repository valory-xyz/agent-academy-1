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

"""Test the payloads.py module of the skill."""
import json

from packages.valory.skills.elcollectooor_abci.payloads import (
    DecisionPayload,
    DetailsPayload,
    ObservationPayload,
    TransactionPayload,
    TransactionType, FundingPayload,
)


def test_observation_payload() -> None:
    """Test `ObservationPayload`"""
    test_project_details = {
        "artist_address": "0x33C9371d25Ce44A408f8a6473fbAD86BF81E1A17",
        "price_per_token_in_wei": 1,
        "project_id": 121,
        "project_name": "Incomplete Control",
        "artist": "Tyler Hobbs",
        "description": "",
        "website": "tylerxhobbs.com",
        "script": "omitted due to its length",
        "ipfs_hash": "",
    }

    frozen_project_details = json.dumps(test_project_details)

    payload = ObservationPayload(
        sender="sender", project_details=frozen_project_details, id_="id"
    )

    assert payload.project_details is not None
    assert payload.id_ == "id"
    assert payload.data == dict(project_details=frozen_project_details)

    assert str(payload.transaction_type) == str(TransactionType.OBSERVATION)
    assert payload.transaction_type == TransactionType.OBSERVATION


def test_decision_payload() -> None:
    """Test `DecisionPayload`"""
    test_decision = 0

    payload = DecisionPayload(sender="sender", decision=test_decision, id_="id")

    assert payload.decision is not None
    assert payload.id_ == "id"
    assert payload.data == dict(decision=test_decision)
    assert hash(payload) == hash(tuple(sorted(payload.data.items())))

    assert str(payload.transaction_type) == str(TransactionType.DECISION)
    assert payload.transaction_type == TransactionType.DECISION


def test_details_payload() -> None:
    """Test `DetailsPayload`"""
    test_data = json.dumps([{"data": "more"}])

    payload = DetailsPayload(sender="sender", details=test_data, id_="id")

    assert payload.details is not None
    assert payload.id_ == "id"
    assert payload.data == dict(details=test_data)
    assert hash(payload) == hash(tuple(sorted(payload.data.items())))

    assert str(payload.transaction_type) == str(TransactionType.DETAILS)
    assert payload.transaction_type == TransactionType.DETAILS


def test_transaction_payload() -> None:
    """Test `TransactionPayload`"""
    test_purchase_data = (
        "0xefef39a10000000000000000000000000000000000000000000000000000000000000079"
    )

    payload = TransactionPayload(
        sender="sender", purchase_data=test_purchase_data, id_="id"
    )

    assert payload.purchase_data is not None
    assert payload.id_ == "id"
    assert payload.data == dict(purchase_data=test_purchase_data)
    assert hash(payload) == hash(tuple(sorted(payload.data.items())))

    assert str(payload.transaction_type) == str(TransactionType.TRANSACTION)
    assert payload.transaction_type == TransactionType.TRANSACTION


def test_funding_payload() -> None:
    """Test `FundingPayload`"""
    funds = 123
    payload = FundingPayload(
        sender="sender", funds=funds, id_="id"
    )

    assert payload.funds is not None
    assert payload.id_ == "id"
    assert payload.data == dict(funds=funds)
    assert hash(payload) == hash(tuple(sorted(payload.data.items())))

    assert str(payload.transaction_type) == str(TransactionType.FUNDING)
    assert payload.transaction_type == TransactionType.FUNDING
