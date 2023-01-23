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

"""Test the payloads.py module of the skill."""

from packages.elcollectooorr.skills.fractionalize_deployment_abci.payloads import (
    BasketAddressesPayload,
    DeployBasketPayload,
    DeployDecisionPayload,
    DeployVaultPayload,
    PermissionVaultFactoryPayload,
    VaultAddressesPayload,
)


def test_deploy_decision_payload() -> None:
    """Test `DeployDecisionPayload`"""
    payload = DeployDecisionPayload(
        sender="sender", deploy_decision="deploy_full",
    )

    assert payload.deploy_decision is not None
    assert payload.data == dict(deploy_decision="deploy_full")


def test_deploy_basket_payload() -> None:
    """Test `DeployBasketPayload`"""
    deploy_basket = "0x0"

    payload = DeployBasketPayload(
        sender="sender", deploy_basket=deploy_basket,
    )

    assert payload.deploy_basket is not None
    assert payload.data == dict(deploy_basket=deploy_basket)


def test_basket_addresses_payload() -> None:
    """Test `BasketAddressesPayload`"""
    basket_addresses = "0x0"

    payload = BasketAddressesPayload(
        sender="sender", basket_addresses=basket_addresses,
    )

    assert payload.basket_addresses is not None
    assert payload.data == dict(basket_addresses=basket_addresses)


def test_permission_vault_factory_payload() -> None:
    """Test `PermissionVaultFactoryPayload`"""
    permission_factory = "0x0"

    payload = PermissionVaultFactoryPayload(
        sender="sender", permission_factory=permission_factory,
    )

    assert payload.permission_factory is not None
    assert payload.data == dict(permission_factory=permission_factory)


def test_vault_address_payload() -> None:
    """Test `VaultAddressesPayload`"""
    vault_addresses = (
        "0xefef39a10000000000000000000000000000000000000000000000000000000000000079"
    )

    payload = VaultAddressesPayload(
        sender="sender", vault_addresses=vault_addresses,
    )

    assert payload.vault_addresses is not None
    assert payload.data == dict(vault_addresses=vault_addresses)


def test_deploy_vault_payload() -> None:
    """Test `DeployVaultPayload`"""
    deploy_vault = "0x0"

    payload = DeployVaultPayload(sender="sender", deploy_vault=deploy_vault, )

    assert payload.deploy_vault is not None
    assert payload.data == dict(deploy_vault=deploy_vault)
