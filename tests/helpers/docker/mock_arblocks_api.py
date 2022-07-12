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
from pathlib import Path

import docker
import requests
from aea.exceptions import enforce
from docker.models.containers import Container

from tests.helpers.constants import TEST_DATA_DIR
from tests.helpers.docker.base import DockerImage


DEFAULT_JSON_SERVER_ADDR = "http://127.0.0.1"
DEFAULT_JSON_SERVER_PORT = 3000
DEFAULT_JSON_DATA_DIR = TEST_DATA_DIR / "json_server" / "data.json"


class MockArtblocksJsonServer(DockerImage):
    """Spawn a JSON server."""

    def __init__(
        self,
        client: docker.DockerClient,
        addr: str = DEFAULT_JSON_SERVER_ADDR,
        port: int = DEFAULT_JSON_SERVER_PORT,
        json_data: Path = DEFAULT_JSON_DATA_DIR,
    ):
        """Initialize."""
        super().__init__(client)
        self.addr = addr
        self.port = port
        self.json_data = json_data

    @property
    def tag(self) -> str:
        """Get the tag."""
        return "ajoelpod/mock-json-server:latest"

    def create(self) -> Container:
        """Create the container."""
        data = "/usr/src/app/data.json"
        volumes = {
            str(self.json_data): {
                "bind": data,
                "mode": "rw",
            },
        }
        ports = {"8000/tcp": ("0.0.0.0", self.port)}  # nosec
        container = self._client.containers.run(
            self.tag,
            detach=True,
            ports=ports,
            volumes=volumes,
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
