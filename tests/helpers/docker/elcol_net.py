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

"""ElCol Network Docker image."""
import logging
import time
from typing import List

import docker
import requests
from aea.exceptions import enforce
from autonomy.test_tools.docker.base import DockerImage
from docker.models.containers import Container

from tests.helpers.constants import THIRD_PARTY


DEFAULT_HARDHAT_ADDR = "http://127.0.0.1"
DEFAULT_HARDHAT_PORT = 8545
ELCOL_CONTRACTS_ROOT_DIR = THIRD_PARTY / "contracts-elcol"

_SLEEP_TIME = 1

# Note: addresses of deployment of master contracts are deterministic
PROXY_FACTORY_CONTRACT = "0x5FbDB2315678afecb367f032d93F642f64180aa3"
MULTISEND_CONTRACT = "0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6"
MULTISEND_CALL_ONLY_CONTRACT = "0x8A791620dd6260079BF849Dc5567aDC3F2FdC318"
SETTINGS_CONTRACT = "0xB7f8BC63BbcaD18155201308C8f3540b07f84F5e"
ERC721_VAULT_FACTORY_CONTRACT = "0xA51c1fc2f0D1a1b8494Ed1FE312d7C3a78Ed91C0"
BASKET_FACTORY_CONTRACT = "0x0DCd1Bf9A1b36cE34237eEaFef220932846BCD82"
ARTBLOCKS_CORE_CONTRACT = "0x0B306BF915C4d645ff596e518fAf3F9669b97016"
ARTBLOCKS_MINTER_FILTER = "0x959922bE3CAee4b8Cd9a407cc3ac1C251C2007B1"
ARTBLOCKS_DA_EXP_V0_CONTRACT = "0x3Aa5ebB10DC797CAC828524e59A333d0A371443c"
ARTBLOCKS_DA_LIN_V0_CONTRACT = "0x68B1D87F95878fE05B998F19b66F4baba5De1aed"
ARTBLOCKS_SET_PRICE_V0_CONTRACT = "0x9A9f2CCfdE556A7E9Ff0848998Aa4a0CFD8863AE"


class ElColNetDockerImage(DockerImage):
    """Spawn a local network with deployed Gnosis Safe Factory, Fracionalize and Artblocks contracts."""

    def __init__(
        self,
        client: docker.DockerClient,
        addr: str = DEFAULT_HARDHAT_ADDR,
        port: int = DEFAULT_HARDHAT_PORT,
    ):
        """Initialize."""
        super().__init__(client)
        self.addr = addr
        self.port = port

    def create_many(self, nb_containers: int) -> List[Container]:
        """Instantiate the image in many containers, parametrized."""
        raise NotImplementedError()

    @property
    def tag(self) -> str:
        """Get the tag."""
        return "node:16.7.0"

    def _build_command(self) -> List[str]:
        """Build command."""
        cmd = ["run", "hardhat", "extra-compile", "--port", str(self.port)]
        return cmd

    def create(self) -> Container:
        """Create the container."""
        cmd = self._build_command()
        working_dir = "/build"
        volumes = {
            str(ELCOL_CONTRACTS_ROOT_DIR): {
                "bind": working_dir,
                "mode": "rw",
            },
        }
        ports = {f"{self.port}/tcp": ("0.0.0.0", self.port)}  # nosec
        container = self._client.containers.run(
            self.tag,
            command=cmd,
            detach=True,
            ports=ports,
            volumes=volumes,
            working_dir=working_dir,
            entrypoint="yarn",
            extra_hosts={"host.docker.internal": "host-gateway"},
        )
        return container

    def wait(self, max_attempts: int = 15, sleep_rate: float = 1.0) -> bool:
        """
        Wait until the image is running.

        :param max_attempts: max number of attempts.
        :param sleep_rate: the amount of time to sleep between different requests.
        :return: True if the wait was successful, False otherwise.
        """
        for i in range(max_attempts):
            try:
                response = requests.get(f"{self.addr}:{self.port}")
                enforce(response.status_code == 200, "")
                return True
            except Exception as e:  # pylint: disable=broad-except
                logging.error("Exception: %s: %s", type(e).__name__, str(e))
                logging.info(
                    "Attempt %s failed. Retrying in %s seconds...", i, sleep_rate
                )
                time.sleep(sleep_rate)
        return False
