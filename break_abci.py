from tests.test_packages.test_connections.fuzzy_tests.mock_node.node import (
    MockNode
)
from tests.test_packages.test_connections.fuzzy_tests.mock_node.channels.tcp_channel import (
    TcpChannel,
)

mock_tendermint = MockNode(TcpChannel())

data = 'a' * 100000
mock_tendermint.check_tx(data.encode(), False)