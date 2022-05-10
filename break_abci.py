#!/usr/bin/env python3
from tests.test_connections.fuzzy_tests.mock_node.node import (
    MockNode
)
from tests.test_connections.fuzzy_tests.mock_node.channels.tcp_channel import (
    TcpChannel,
)


if __name__ == '__main__':
    channel = TcpChannel()
    mock_tendermint = MockNode(channel)

    data = 'a' * 10
    mock_tendermint.connect()
    mock_tendermint.check_tx(data.encode(), False)
    mock_tendermint.disconnect()
