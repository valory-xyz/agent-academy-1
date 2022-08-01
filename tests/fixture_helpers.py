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

"""This module contains helper classes/functions for fixtures."""
from typing import Any, List, Tuple

import docker
import pytest

from tests.helpers.constants import HARDHAT_ELCOL_KEY_PAIRS
from autonomy.test_tools.docker.base import DockerImage
from tests.helpers.docker.elcol_net import ElColNetDockerImage


@pytest.mark.integration
class UseHardHatElColBaseTest:
    """Inherit from this class to use HardHat local net with the El Collectooorrr contracts deployed."""

    key_pairs: List[Tuple[str, str]] = HARDHAT_ELCOL_KEY_PAIRS

    @classmethod
    @pytest.fixture(autouse=True)
    def _start_hardhat_elcol(
        cls,
        hardhat_elcol_scope_function: Any,
        hardhat_elcol_addr: Any,
        hardhat_elcol_key_pairs: Any,
        setup_artblocks_contract: Any,
    ) -> None:
        """Start a HardHat ElCol instance."""
        cls.key_pairs = hardhat_elcol_key_pairs


class HardHatElColBaseTest(HardHatBaseTest):
    """Base pytest class for HardHat with Gnosis Factory, Fractionalize and Artblocks contracts deployed."""

    @classmethod
    def _build_image(cls) -> DockerImage:
        """Build the image."""
        client = docker.from_env()
        return ElColNetDockerImage(client, cls.addr, cls.port)
