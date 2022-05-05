#!/usr/bin/env python3
from tests.test_connections.fuzzy_tests.mock_node.node import (
    MockNode
)
from tests.test_connections.fuzzy_tests.mock_node.channels.tcp_channel import (
    TcpChannel,
)

channel = TcpChannel()
channel.connect()
mock_tendermint = MockNode(channel)

data = 'a' * 100000
mock_tendermint.check_tx(data.encode(), False)