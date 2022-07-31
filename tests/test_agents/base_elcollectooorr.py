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

"""End2end tests base classes for this repo."""
import subprocess  # nosec
import threading
import time

import web3
from aea.configurations.base import PublicId
from click.testing import Result
from web3.types import Wei

from tests.helpers.constants import ARTBLOCKS_ADDRESS as _DEFAULT_ARTBLOCKS_ADDRESS
from tests.helpers.constants import (
    ARTBLOCKS_FILTER_ADDRESS as _DEFAULT_ARTBLOCKS_FILTER_ADDRESS,
)
from tests.helpers.constants import (
    BASKET_FACTORY_ADDRESS as _DEFAULT_BASKET_FACTORY_ADDRESS,
)
from tests.helpers.constants import ELCOL_NET_CHAIN_ID as _DEFAULT_ELCOL_NET_CHAIN_ID
from tests.helpers.constants import ELCOL_NET_HOST as _DEFAULT_ELCOL_NET_HOST
from tests.helpers.constants import (
    HARDHAT_ELCOL_KEY_PAIRS as _DEFAULT_HARDHAT_ELCOL_KEY_PAIRS,
)
from tests.helpers.constants import HTTP_LOCALHOST as _DEFAULT_HTTP_LOCALHOST
from tests.helpers.constants import (
    MOCK_ARTBLOCKS_API_PORT as _DEFAULT_MOCK_ARTBLOCKS_API_PORT,
)
from tests.helpers.constants import MULTISEND_ADDRESS as _DEFAULT_MULTISEND_ADDRESS
from tests.helpers.constants import (
    SAFE_CALLBACK_HANDLER as _DEFAULT_SAFE_CALLBACK_HANDLER,
)
from tests.helpers.constants import (
    SAFE_CONTRACT_ADDRESS as _DEFAULT_SAFE_CONTRACT_ADDRESS,
)
from tests.helpers.constants import (
    SAFE_FACTORY_ADDRESS as _DEFAULT_SAFE_FACTORY_ADDRESS,
)
from tests.helpers.constants import SETTINGS_ADRESS as _DEFAULT_SETTINGS_ADDRESS
from tests.helpers.constants import (
    TOKEN_VAULT_FACTORY_ADDRESS as _DEFAULT_TOKEN_VAULT_FACTORY_ADDRESS,
)
from tests.test_agents.base import BaseTestEnd2End


ONE_ETH = 10 ** 18


class BaseTestElCollectooorrEnd2End(BaseTestEnd2End):
    """
    Extended base class for conducting E2E tests with the El Collectooorr.

    Test subclasses must set NB_AGENTS, agent_package, wait_to_finish and check_strings.
    """

    cli_log_options = ["-v", "INFO"]  # no need for debug
    skill_package = "valory/elcollectooorr_abci:0.1.0"
    SAFE_CONTRACT_ADDRESS = _DEFAULT_SAFE_CONTRACT_ADDRESS
    SAFE_CALLBACK_HANDLER = _DEFAULT_SAFE_CALLBACK_HANDLER
    SAFE_FACTORY_ADDRESS = _DEFAULT_SAFE_FACTORY_ADDRESS
    MOCK_ARTBLOCKS_API_PORT = _DEFAULT_MOCK_ARTBLOCKS_API_PORT
    HTTP_LOCALHOST = _DEFAULT_HTTP_LOCALHOST
    HARDHAT_ELCOL_KEY_PAIRS = _DEFAULT_HARDHAT_ELCOL_KEY_PAIRS
    ELCOL_NET_HOST = _DEFAULT_ELCOL_NET_HOST
    ELCOL_NET_CHAIN_ID = _DEFAULT_ELCOL_NET_CHAIN_ID
    __args_prefix = f"vendor.valory.skills.{PublicId.from_str(skill_package).name}.models.params.args"
    extra_configs = [
        {
            "dotted_path": f"{__args_prefix}.artblocks_contract",
            "value": _DEFAULT_ARTBLOCKS_ADDRESS,
        },
        {
            "dotted_path": f"{__args_prefix}.artblocks_minter_filter",
            "value": _DEFAULT_ARTBLOCKS_FILTER_ADDRESS,
        },
        {
            "dotted_path": f"{__args_prefix}.basket_factory_address",
            "value": _DEFAULT_BASKET_FACTORY_ADDRESS,
        },
        {
            "dotted_path": f"{__args_prefix}.token_vault_factory_address",
            "value": _DEFAULT_TOKEN_VAULT_FACTORY_ADDRESS,
        },
        {
            "dotted_path": f"{__args_prefix}.settings_address",
            "value": _DEFAULT_SETTINGS_ADDRESS,
        },
        {
            "dotted_path": f"{__args_prefix}.multisend_address",
            "value": _DEFAULT_MULTISEND_ADDRESS,
        },
    ]

    def test_run(self, nb_nodes: int) -> None:
        """Run the test."""
        self.prepare_and_launch(nb_nodes)
        self.health_check(
            max_retries=self.HEALTH_CHECK_MAX_RETRIES,
            sleep_interval=self.HEALTH_CHECK_SLEEP_INTERVAL,
        )
        thread = threading.Thread(target=self._deposit_to_safe_contract)
        thread.start()
        self.check_aea_messages()
        self.terminate_processes()

    def _BaseTestEnd2End__prepare_agent_i(self, i: int, nb_agents: int) -> None:
        """Prepare the i-th agent."""
        super()._BaseTestEnd2End__prepare_agent_i(i, nb_agents)  # type: ignore
        self._replace_default_addresses(i)

    def _replace_default_addresses(self, i: int) -> None:
        """Update the gnosis safe contract default addresses."""
        agent_name = self._get_agent_name(i)
        try:  # nosec
            with open(
                self.t.joinpath(agent_name).joinpath(
                    "vendor/valory/contracts/gnosis_safe/contract.py"
                ),
                "r",
            ) as f:
                org = f.read()
        except Exception:
            # happens when the agent is not yet fetched
            return

        dst = (
            org.replace(
                'SAFE_CONTRACT = "0xd9Db270c1B5E3Bd161E8c8503c55cEABeE709552"',
                f'SAFE_CONTRACT = "{self.SAFE_CONTRACT_ADDRESS}"',
            )
            .replace(
                'DEFAULT_CALLBACK_HANDLER = "0xf48f2B2d2a534e402487b3ee7C18c33Aec0Fe5e4"',
                f'DEFAULT_CALLBACK_HANDLER = "{self.SAFE_CALLBACK_HANDLER}"',
            )
            .replace(
                'PROXY_FACTORY_CONTRACT = "0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2"',
                f'PROXY_FACTORY_CONTRACT = "{self.SAFE_FACTORY_ADDRESS}"',
            )
            .replace(
                "return dict(verified=verified)",
                "return dict(verified=True)",
            )
            .replace(
                '"gas": configured_gas,',
                "",
            )
        )

        with open(
            self.t.joinpath(agent_name).joinpath(
                "vendor/valory/contracts/gnosis_safe/contract.py"
            ),
            "w",
        ) as f:
            f.write(dst)
            f.flush()

    @classmethod
    def run_install(cls) -> Result:
        """
        Execute AEA CLI install command.

        Run from agent's directory.

        :return: Result
        """
        return cls.run_cli_command(*("-s", "install"), cwd=cls._get_cwd())

    @classmethod
    def run_agent(cls, *args: str) -> subprocess.Popen:
        """
        Run agent as subprocess.

        Run from agent's directory.

        :param args: CLI args

        :return: subprocess object.
        """
        return cls._start_cli_process(*("-s", "run"), *args)

    def _deposit_to_safe_contract(self, timeout: int = 200) -> None:
        """This method simulates a user depositing funds into the safe contract."""
        start = time.time()
        while True:
            for output in self.stdout.values():
                safe_contract_address_parts = output.split("Safe contract address: ", 1)
                if len(safe_contract_address_parts) > 1:
                    target_address = (
                        safe_contract_address_parts[1]
                        .split(" ", 1)[0]
                        .split("\n")[0]
                        .strip()
                    )
                    instance = web3.Web3(web3.HTTPProvider(self.ELCOL_NET_HOST))
                    sender_address, private_key = self.HARDHAT_ELCOL_KEY_PAIRS[0]
                    raw_tx = instance.eth.send_transaction(
                        {
                            "to": target_address,
                            "from": sender_address,
                            "value": Wei(ONE_ETH),
                            "chainId": self.ELCOL_NET_CHAIN_ID,
                            "gasPrice": instance.eth.gas_price,
                            "nonce": instance.eth.getTransactionCount(
                                instance.toChecksumAddress(sender_address)
                            ),
                        }
                    )
                    signed_tx = instance.eth.account.signTransaction(
                        raw_tx, private_key=private_key
                    )
                    instance.eth.sendRawTransaction(signed_tx.rawTransaction)
                    return

            if time.time() - start > timeout:
                return

            time.sleep(5)  # wait 5 sec before checking again
