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

"""Conftest module for Pytest."""
import json
import logging
from pathlib import Path
from typing import Any, Generator, List, Tuple

import docker
import pytest
import web3
from web3 import Web3

from autonomy.test_tools.docker.base import launch_image
from autonomy.test_tools.docker.ganache import (
    DEFAULT_GANACHE_ADDR,
    DEFAULT_GANACHE_PORT,
    GanacheForkDockerImage,
)
from autonomy.test_tools.docker.gnosis_safe_net import (
    DEFAULT_HARDHAT_ADDR,
    DEFAULT_HARDHAT_PORT,
    GnosisSafeNetDockerImage,
)

from tests.helpers.artblocks_utils import (
    add_approved_minter,
    add_mint_whitelisted,
    create_project,
    send_tx,
    set_minter_for_project,
    set_project_max_invitation,
    toggle_contract_mintable,
    toggle_project_is_active,
    toggle_project_is_paused,
    update_max_invocations,
    update_price,
)
from tests.helpers.constants import (
    ARTBLOCKS_ADDRESS,
    ARTBLOCKS_CORE_FILE,
    ARTBLOCKS_FILTER_ADDRESS,
    ARTBLOCKS_MINTER_FILTER_FILE,
    ARTBLOCKS_PERIPHERY_FILE,
    ARTBLOCKS_SET_PRICE_MINTER,
    GANACHE_KEY_PAIRS,
    HARDHAT_ELCOL_KEY_PAIRS,
    KEY_PAIRS,
)
from tests.helpers.constants import ROOT_DIR as _ROOT_DIR
from tests.helpers.constants import TARGET_PROJECT_ID
from tests.helpers.docker.elcol_net import ElColNetDockerImage
from tests.helpers.docker.mock_arblocks_api import (
    DEFAULT_JSON_SERVER_ADDR,
    DEFAULT_JSON_SERVER_PORT,
    MockArtblocksJsonServer,
)


ROOT_DIR = _ROOT_DIR
THIRD_PARTY_CONTRACTS = ROOT_DIR / "third_party"


@pytest.fixture()
def key_pairs() -> List[Tuple[str, str]]:
    """Get the default key paris for hardhat."""
    return KEY_PAIRS


@pytest.fixture()
def hardhat_addr() -> str:
    """Get the hardhat addr"""
    return DEFAULT_HARDHAT_ADDR


@pytest.fixture()
def hardhat_port() -> int:
    """Get the hardhat port"""
    return DEFAULT_HARDHAT_PORT


@pytest.fixture(scope="function")
def gnosis_safe_hardhat_scope_function(
    hardhat_addr: Any,
    hardhat_port: Any,
    timeout: float = 3.0,
    max_attempts: int = 40,
) -> Generator:
    """Launch the HardHat node with Gnosis Safe contracts deployed. This fixture is scoped to a function which means it will destroyed at the end of the test."""
    client = docker.from_env()
    logging.info(f"Launching Hardhat at port {hardhat_port}")
    image = GnosisSafeNetDockerImage(
        client, THIRD_PARTY_CONTRACTS, hardhat_addr, hardhat_port
    )
    yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)


@pytest.fixture()
def ganache_key_pairs() -> List[Tuple[str, str]]:
    """Get the default key paris for ganache."""
    return GANACHE_KEY_PAIRS


@pytest.fixture()
def ganache_addr() -> str:
    """Get the ganache addr"""
    return DEFAULT_GANACHE_ADDR


@pytest.fixture()
def ganache_port() -> int:
    """Get the ganache port"""
    return DEFAULT_GANACHE_PORT


@pytest.fixture(scope="function")
def ganache_fork_scope_function(
    ganache_addr: Any,
    ganache_port: Any,
    timeout: float = 3.0,
    max_attempts: int = 40,
) -> Generator:
    """Launch the Ganache Fork. This fixture is scoped to a function which means it will destroyed at the end of the test."""
    client = docker.from_env()
    logging.info(f"Launching Ganache at port {ganache_port}")
    image = GanacheForkDockerImage(client, ganache_addr, ganache_port)
    yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)


@pytest.fixture()
def ganache_fork_engine_warmer_function(
    ganache_fork_scope_function: Any,
    ganache_addr: Any,
    ganache_port: Any,
    timeout: float = 60.0,
) -> None:
    """The ganache fork is very slow on the first try. This function is used to go through the same steps as the agent would do later."""

    path_to_artblocks = Path(
        _ROOT_DIR,
        "packages",
        "valory",
        "contracts",
        "artblocks",
        "build",
        "artblocks.json",
    )

    with open(path_to_artblocks) as f:
        artblocks_abi = json.load(f)["abi"]

    w3 = Web3(
        Web3.HTTPProvider(
            f"{ganache_addr}:{ganache_port}", request_kwargs={"timeout": timeout}
        )
    )

    artblocks = w3.eth.contract(address=ARTBLOCKS_ADDRESS, abi=artblocks_abi)  # type: ignore
    project_info = artblocks.caller.projectTokenInfo(TARGET_PROJECT_ID)
    if project_info[4]:
        script_info = artblocks.caller.projectScriptInfo(TARGET_PROJECT_ID)
        artblocks.caller.projectScriptByIndex(TARGET_PROJECT_ID, script_info[1] - 1)
    artblocks.caller.projectDetails(TARGET_PROJECT_ID)


@pytest.fixture()
def mock_artblocks_api_addr() -> str:
    """Get the mock artblocks api addr"""
    return DEFAULT_JSON_SERVER_ADDR


@pytest.fixture()
def mock_artblocks_api_port() -> int:
    """Get the mock artblocks api port"""
    return DEFAULT_JSON_SERVER_PORT


@pytest.fixture(scope="function")
def mock_artblocks_api_function(
    mock_artblocks_api_addr: Any,
    mock_artblocks_api_port: Any,
    timeout: float = 3.0,
    max_attempts: int = 40,
) -> Generator:
    """Launch a mock artblocks api."""
    client = docker.from_env()
    logging.info(f"Launching mock artblocks api at port {mock_artblocks_api_port}")
    image = MockArtblocksJsonServer(
        client, mock_artblocks_api_addr, mock_artblocks_api_port
    )
    yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)


@pytest.fixture()
def hardhat_elcol_addr() -> str:
    """Get the ganache addr"""
    return DEFAULT_HARDHAT_ADDR


@pytest.fixture()
def hardhat_elcol_port() -> int:
    """Get the ganache port"""
    return DEFAULT_HARDHAT_PORT


@pytest.fixture()
def hardhat_elcol_key_pairs() -> List[Tuple[str, str]]:
    """Get the default key paris for ganache."""
    return HARDHAT_ELCOL_KEY_PAIRS


@pytest.fixture(scope="function")
def hardhat_elcol_scope_function(
    hardhat_elcol_addr: Any,
    hardhat_elcol_port: Any,
    mock_artblocks_api_function: Any,
    timeout: float = 3.0,
    max_attempts: int = 200,
) -> Generator:
    """Launch the ElCol Test Network. This fixture is scoped to a function which means it will destroyed at the end of the test."""
    client = docker.from_env()
    logging.info(f"Launching the ElCol network at port {ganache_port}")
    image = ElColNetDockerImage(client, hardhat_elcol_addr, hardhat_elcol_port)
    yield from launch_image(image, timeout=timeout, max_attempts=max_attempts)


@pytest.fixture()
def setup_artblocks_contract(
    hardhat_elcol_key_pairs: Any,
    hardhat_elcol_addr: Any,
    hardhat_elcol_port: Any,
) -> None:
    """Setup artblocks contracts by whitelisting minters and creating a project."""
    default_max_invocations = 5
    default_price_per_token_in_wei = 1
    sender_address, private_key = hardhat_elcol_key_pairs[0]
    instance = Web3(web3.HTTPProvider(f"{hardhat_elcol_addr}:{hardhat_elcol_port}"))

    with open(ARTBLOCKS_MINTER_FILTER_FILE) as minter_filter_file:
        minter_filter = json.load(minter_filter_file)
        artblocks_minter_filter = instance.eth.contract(
            address=instance.toChecksumAddress(ARTBLOCKS_FILTER_ADDRESS),
            abi=minter_filter["abi"],
        )

    with open(ARTBLOCKS_CORE_FILE) as artblocks_file:
        artblocks = json.load(artblocks_file)
        artblocks_core = instance.eth.contract(
            address=instance.toChecksumAddress(ARTBLOCKS_ADDRESS), abi=artblocks["abi"]
        )

    with open(ARTBLOCKS_PERIPHERY_FILE) as artblocks_periphery_file:
        artblocks_periphery = json.load(artblocks_periphery_file)
        artblocks_periphery = instance.eth.contract(
            address=instance.toChecksumAddress(ARTBLOCKS_SET_PRICE_MINTER),
            abi=artblocks_periphery["abi"],
        )

    raw_tx = add_mint_whitelisted(artblocks_core, instance, ARTBLOCKS_FILTER_ADDRESS)
    send_tx(instance, private_key, sender_address, raw_tx)

    project_id = artblocks_core.functions.nextProjectId().call()
    raw_tx = create_project(
        artblocks_core,
        instance,
        "test_project",
        sender_address,
        default_price_per_token_in_wei,
    )
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = update_max_invocations(artblocks_core, project_id, default_max_invocations)
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = toggle_project_is_active(artblocks_core, project_id)
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = toggle_project_is_paused(artblocks_core, project_id)
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = add_approved_minter(
        artblocks_minter_filter, instance, ARTBLOCKS_SET_PRICE_MINTER
    )
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = set_minter_for_project(
        artblocks_minter_filter, instance, project_id, ARTBLOCKS_SET_PRICE_MINTER
    )
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = toggle_contract_mintable(artblocks_periphery, project_id)
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = update_price(
        artblocks_periphery, project_id, default_price_per_token_in_wei
    )
    send_tx(instance, private_key, sender_address, raw_tx)

    raw_tx = set_project_max_invitation(artblocks_periphery, project_id)
    send_tx(instance, private_key, sender_address, raw_tx)
