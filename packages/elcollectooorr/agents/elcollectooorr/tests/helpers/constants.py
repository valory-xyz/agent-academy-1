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
"""Constants for tests."""
from typing import List, Tuple

from packages.elcollectooorr.agents.elcollectooorr.tests import PACKAGE_DIR
from packages.elcollectooorr.contracts.artblocks import PACKAGE_DIR as ARTBLOCKS_DIR
from packages.elcollectooorr.contracts.artblocks_minter_filter import (
    PACKAGE_DIR as ARTBLOCKS_MINTER_FILTER_DIR,
)
from packages.elcollectooorr.contracts.artblocks_periphery import (
    PACKAGE_DIR as ARTBLOCKS_PERIPHERY_DIR,
)


TEST_DATA_DIR = PACKAGE_DIR / "tests" / "data"
DEFAULT_ASYNC_TIMEOUT = 5.0
DEFAULT_REQUESTS_TIMEOUT = 5.0
MAX_RETRIES = 30
LOCALHOST = "localhost"
HTTP_LOCALHOST = f"http://{LOCALHOST}"
WEI_TO_ETH = 10 ** 18
SAFE_CONTRACT_ADDRESS = "0x32Cf1f3a98aeAF57b88b3740875D19912A522c1A"
SAFE_FACTORY_ADDRESS = "0xD3aA556287Afe63102e5797BFDDd2A1E8DbB3eA5"
SAFE_CALLBACK_HANDLER = "0x5Cca2cF3f8a0e5a5aF6A1E9A54A0c98510D92081"
DEPLOYED_SAFE_CONTRACT = "0xfe8E74C5453fE73A1c927A4B95251DFF66D46Fac"  # this is the contract that get deployed once the test is run
ARTBLOCKS_CORE_FILE = ARTBLOCKS_DIR / "build" / "artblocks.json"
ARTBLOCKS_PERIPHERY_FILE = (
    ARTBLOCKS_PERIPHERY_DIR / "build" / "Minter.json"
)
ARTBLOCKS_MINTER_FILTER_FILE = (
    ARTBLOCKS_MINTER_FILTER_DIR / "build" / "MinterFilter.json"
)
ARTBLOCKS_ADDRESS = "0xE0F8cEe346A702CCA192a6Ec807ff89B4c6bC70E"
ARTBLOCKS_FILTER_ADDRESS = "0x3A78BF1783a0187c1C8000e41C2a008897D0a35f"
ARTBLOCKS_SET_PRICE_MINTER = "0xfe46A8F577d3367848bdd127173B7d5F14a6088C"
BASKET_FACTORY_ADDRESS = "0x9623B3C78e77Ea8c1A544cB73108B04787f96b08"
TOKEN_VAULT_FACTORY_ADDRESS = "0x2C03ca9fb5a7b5B26996c00F7c419C5E9C706196"  # nosec
SETTINGS_ADRESS = "0xb2443146EC9F5a1a5Fd5c1C9C0fe5f5cC459A31A"
MULTISEND_ADDRESS = "0x9e2C43153aa0007E6172af3733021A227480f008"
MOCK_ARTBLOCKS_API_PORT = 3000
ELCOL_NET_HOST = f"{HTTP_LOCALHOST}:8545"
ELCOL_NET_CHAIN_ID = 31337
TARGET_PROJECT_ID = (
    56  # id of project that we want to test the behaviour of the El Collectooorr
)
CONFIGURED_SAFE_CONTRACT = "0xce7AEd90271f69F863d72A3B372288DEA3443bF6"
MULTICALL2_ADDRESS = "0x10aCcaADfB6aCEa7d02417260101642dEE173dA5"
DEFAULT_WHITELISTED_ADDRESSES = ["0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0"]
# default hardhat key pairs (public key, private key)
KEY_PAIRS: List[Tuple[str, str]] = [
    (
        "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266",
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
    ),
    (
        "0x70997970c51812dc3a010c7d01b50e0d17dc79c8",
        "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d",
    ),
    (
        "0x3c44cdddb6a900fa2b585dd299e03d12fa4293bc",
        "0x5de4111afa1a4b94908f83103eb1f1706367c2e68ca870fc3fb9a804cdab365a",
    ),
    (
        "0x90f79bf6eb2c4f870365e785982e1f101e93b906",
        "0x7c852118294e51e653712a81e05800f419141751be58f605c371e15141b007a6",
    ),
    (
        "0x15d34aaf54267db7d7c367839aaf71a00a2c6a65",
        "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a",
    ),
    (
        "0x9965507d1a55bcc2695c58ba16fb37d819b0a4dc",
        "0x8b3a350cf5c34c9194ca85829a2df0ec3153be0318b5e2d3348e872092edffba",
    ),
    (
        "0x976ea74026e726554db657fa54763abd0c3a0aa9",
        "0x92db14e403b83dfe3df233f83dfa3a0d7096f21ca9b0d6d6b8d88b2b4ec1564e",
    ),
    (
        "0x14dc79964da2c08b23698b3d3cc7ca32193d9955",
        "0x4bbbf85ce3377467afe5d46f804f221813b2bb87f24d81f60f1fcdbf7cbf4356",
    ),
    (
        "0x23618e81e3f5cdf7f54c3d65f7fbc0abf5b21e8f",
        "0xdbda1821b80551c9d65939329250298aa3472ba22feea921c0cf5d620ea67b97",
    ),
    (
        "0xa0ee7a142d267c1f36714e4a8f75612f20a79720",
        "0x2a871d0798f97d79848a013d4936a73bf4cc922c825d33c1cf7073dff6d409c6",
    ),
    (
        "0xbcd4042de499d14e55001ccbb24a551f3b954096",
        "0xf214f2b2cd398c806f84e317254e0f0b801d0643303237d97a22a48e01628897",
    ),
    (
        "0x71be63f3384f5fb98995898a86b02fb2426c5788",
        "0x701b615bbdfb9de65240bc28bd21bbc0d996645a3dd57e7b12bc2bdf6f192c82",
    ),
    (
        "0xfabb0ac9d68b0b445fb7357272ff202c5651694a",
        "0xa267530f49f8280200edf313ee7af6b827f2a8bce2897751d06a843f644967b1",
    ),
    (
        "0x1cbd3b2770909d4e10f157cabc84c7264073c9ec",
        "0x47c99abed3324a2707c28affff1267e45918ec8c3f20b8aa892e8b065d2942dd",
    ),
    (
        "0xdf3e18d64bc6a983f673ab319ccae4f1a57c7097",
        "0xc526ee95bf44d8fc405a158bb884d9d1238d99f0612e9f33d006bb0789009aaa",
    ),
    (
        "0xcd3b766ccdd6ae721141f452c550ca635964ce71",
        "0x8166f546bab6da521a8369cab06c5d2b9e46670292d85c875ee9ec20e84ffb61",
    ),
    (
        "0x2546bcd3c84621e976d8185a91a922ae77ecec30",
        "0xea6c44ac03bff858b476bba40716402b03e41b8e97e276d1baec7c37d42484a0",
    ),
    (
        "0xbda5747bfd65f08deb54cb465eb87d40e51b197e",
        "0x689af8efa8c651a91ad287602527f3af2fe9f6501a7ac4b061667b5a93e037fd",
    ),
    (
        "0xdd2fd4581271e230360230f9337d5c0430bf44c0",
        "0xde9be858da4a475276426320d5e9262ecfc3ba460bfac56360bfa6c4c28b4ee0",
    ),
    (
        "0x8626f6940e2eb28930efb4cef49b2d1f2c9c1199",
        "0xdf57089febbacf7ba0bc227dafbffa9fc08a93fdc68e1e42411a14efcf23656e",
    ),
]

# ganache key pairs (public, private)
GANACHE_KEY_PAIRS: List[Tuple[str, str]] = [
    (
        "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
        "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",
    ),
    (
        "0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0",
        "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1",
    ),
    (
        "0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b",
        "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c",
    ),
    (
        "0xE11BA2b4D45Eaed5996Cd0823791E0C93114882d",
        "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913",
    ),
    (
        "0xd03ea8624C8C5987235048901fB614fDcA89b117",
        "0xadd53f9a7e588d003326d1cbf9e4a43c061aadd9bc938c843a79e7b4fd2ad743",
    ),
]

# hardhat elcol key pairs (public, private)
HARDHAT_ELCOL_KEY_PAIRS: List[Tuple[str, str]] = [
    (
        "0xFFcf8FDEE72ac11b5c542428B35EEF5769C409f0",
        "0x6cbed15c793ce57650b9877cf6fa156fbef513c4e6134f022a85b1ffdd59b2a1",
    ),
    (
        "0x90F8bf6A479f320ead074411a4B0e7944Ea8c9C1",
        "0x4f3edf983ac636a65a842ce7c78d9aa706d3b113bce9c46f30d7d21715b23b1d",
    ),
    (
        "0x22d491Bde2303f2f43325b2108D26f1eAbA1e32b",
        "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c",
    ),
    (
        "0xE11BA2b4D45Eaed5996Cd0823791E0C93114882d",
        "0x646f1ce2fdad0e6deeeb5c7e8e5543bdde65e86029e2fd9fc169899c440a7913",
    ),
]
