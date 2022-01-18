from base import BaseFuzzyTests
from mock_node.grpc_client import GrpcClient


class GrpcFuzzyTests(BaseFuzzyTests):
    CHANNEL_TYPE = GrpcClient
    USE_GRPC = True
    AGENT_TIMEOUT = 3  # 3 seconds
