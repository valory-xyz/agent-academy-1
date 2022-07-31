#!/usr/bin/env python3
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

"""To test abci connection message sizes."""

from tests.test_connections.test_fuzz.mock_node.channels.tcp_channel import TcpChannel
from tests.test_connections.test_fuzz.mock_node.node import MockNode


if __name__ == "__main__":
    channel = TcpChannel()
    mock_tendermint = MockNode(channel)

    data = "a" * 10
    mock_tendermint.connect()
    mock_tendermint.check_tx(data.encode(), False)
    mock_tendermint.disconnect()
