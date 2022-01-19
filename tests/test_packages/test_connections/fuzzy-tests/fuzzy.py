from base import BaseFuzzyTests
from mock_node.channels.grpc_channel import GrpcChannel
from mock_node.channels.tcp_channel import TcpChannel


class GrpcFuzzyTests(BaseFuzzyTests):
    CHANNEL_TYPE = GrpcChannel
    USE_GRPC = True
    AGENT_TIMEOUT = 3  # 3 seconds


class TcpFuzzyTests(BaseFuzzyTests):
    CHANNEL_TYPE = TcpChannel
    USE_GRPC = False
    AGENT_TIMEOUT = 3  # 3 seconds
