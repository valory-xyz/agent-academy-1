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

"""Utils functions setting up the artblocks contracts."""

from typing import Any

from tests.helpers.constants import ELCOL_NET_CHAIN_ID


def toggle_project_is_active(
    artblocks_core_contract: Any,
    project_id: int,
) -> Any:
    """Toggle an artblock's project active status."""
    return artblocks_core_contract.functions.toggleProjectIsActive(project_id)


def toggle_project_is_locked(
    artblocks_core_contract: Any,
    project_id: int,
) -> Any:
    """Toggle an artblock's project locked status."""
    return artblocks_core_contract.functions.toggleProjectIsLocked(project_id)


def toggle_project_is_paused(
    artblocks_core_contract: Any,
    project_id: int,
) -> Any:
    """Toggle an artblock's project paused status."""
    return artblocks_core_contract.functions.toggleProjectIsPaused(project_id)


def create_project(
    artblocks_core_contract: Any,
    instance: Any,
    project_name: str,
    artist_address: str,
    price_in_wei: int,
    dyanmic: bool = False,
) -> Any:
    """Create an artblocks project."""
    return artblocks_core_contract.functions.addProject(
        project_name, instance.toChecksumAddress(artist_address), price_in_wei, dyanmic
    )


def add_mint_whitelisted(
    artblocks_core_contract: Any,
    instance: Any,
    address: str,
) -> Any:
    """Whitelist a mint in the core arblocks contract."""
    return artblocks_core_contract.functions.addMintWhitelisted(
        instance.toChecksumAddress(address),
    )


def update_max_invocations(
    artblocks_core_contract: Any,
    project_id: int,
    max_invocations: int,
) -> Any:
    """Update the max invocations (purchases) of a project."""

    return artblocks_core_contract.functions.updateProjectMaxInvocations(
        project_id,
        max_invocations,
    )


def add_approved_minter(
    artblocks_minter_filter: Any, instance: Any, minter_address: str
) -> Any:
    """Whitelist a minter on the MinterFilter contract."""

    return artblocks_minter_filter.functions.addApprovedMinter(
        instance.toChecksumAddress(minter_address),
    )


def set_minter_for_project(
    artblocks_minter_filter: Any, instance: Any, project_id: int, minter_address: str
) -> Any:
    """Set the minter for a project."""

    return artblocks_minter_filter.functions.setMinterForProject(
        project_id,
        instance.toChecksumAddress(minter_address),
    )


def set_project_max_invitation(
    artblocks_minter_periphery: Any,
    project_id: int,
) -> Any:
    """Set the max invocations (purchases) for a project at the minter."""
    return artblocks_minter_periphery.functions.setProjectMaxInvocations(
        project_id,
    )


def update_price(
    artblocks_minter_periphery: Any,
    project_id: int,
    price: int,
) -> Any:
    """Update the price of a project."""

    return artblocks_minter_periphery.functions.updatePricePerTokenInWei(
        project_id,
        price,
    )


def toggle_contract_mintable(
    artblocks_minter_periphery: Any,
    project_id: int,
) -> Any:
    """Toggle whether if a project is mintable via smart contracts. Applies to V0 contracts only."""

    return artblocks_minter_periphery.functions.toggleContractMintable(
        project_id,
    )


def send_tx(instance: Any, private_key: str, sender_address: str, tx: Any) -> None:
    """Send the provided tx."""

    raw_tx = tx.buildTransaction(
        {
            "from": sender_address,
            "chainId": ELCOL_NET_CHAIN_ID,
            "gasPrice": instance.eth.gas_price,
            "nonce": instance.eth.getTransactionCount(
                instance.toChecksumAddress(sender_address)
            ),
        }
    )
    signed_tx = instance.eth.account.signTransaction(raw_tx, private_key=private_key)
    instance.eth.sendRawTransaction(signed_tx.rawTransaction)
