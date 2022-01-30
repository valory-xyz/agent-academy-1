"""Fuzzy tests for valory/abci connection"""
from unittest import TestCase

from tests.test_packages.test_connections.fuzzy_tests.base import BaseFuzzyTests
from tests.test_packages.test_connections.fuzzy_tests.mock_node.channels.grpc_channel import (
    GrpcChannel,
)
from tests.test_packages.test_connections.fuzzy_tests.mock_node.channels.tcp_channel import (
    TcpChannel,
)


class GrpcFuzzyTests(BaseFuzzyTests, TestCase):
    """Test the connection when gRPC is used"""

    CHANNEL_TYPE = GrpcChannel
    USE_GRPC = True
    AGENT_TIMEOUT = 3  # 3 seconds


class TcpFuzzyTests(BaseFuzzyTests, TestCase):
    """Test the connection when TCP is used"""

    CHANNEL_TYPE = TcpChannel
    USE_GRPC = False
    AGENT_TIMEOUT = 3  # 3 seconds
