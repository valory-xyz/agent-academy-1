from base import BaseFuzzyTests
from mock_node.channels.grpc_channel import GrpcChannel


class GrpcFuzzyTests(BaseFuzzyTests):
    CHANNEL_TYPE = GrpcChannel
    USE_GRPC = True
    AGENT_TIMEOUT = 3  # 3 seconds
