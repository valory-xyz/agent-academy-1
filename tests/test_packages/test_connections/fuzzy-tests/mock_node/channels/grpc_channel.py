import logging

import grpc

from packages.valory.connections.abci.tendermint.abci import types_pb2_grpc as tendermint_grpc, types_pb2 as abci_types
from .base import BaseChannel

_default_logger = logging.getLogger(__name__)

logging.basicConfig()


class GrpcChannel(BaseChannel):

    def __init__(self, **kwargs) -> None:
        super().__init__()

        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 26658)
        self.logger = _default_logger

        grpc_channel = grpc.insecure_channel(f'{host}:{port}')
        self.grpc_client = tendermint_grpc.ABCIApplicationStub(grpc_channel)

    def send_info(self, request: abci_types.RequestInfo) -> abci_types.ResponseInfo:
        return self.grpc_client.Info(request)

    def send_echo(self, request: abci_types.RequestEcho) -> abci_types.ResponseEcho:
        return self.grpc_client.Echo(request)

    def send_flush(self, request: abci_types.RequestFlush) -> abci_types.ResponseFlush:
        return self.grpc_client.Flush(request)

    def send_set_option(self, request: abci_types.RequestSetOption) -> abci_types.ResponseSetOption:
        return self.grpc_client.SetOption(request)

    def send_deliver_tx(self, request: abci_types.RequestDeliverTx) -> abci_types.ResponseDeliverTx:
        return self.grpc_client.DeliverTx(request)

    def send_check_tx(self, request: abci_types.RequestCheckTx) -> abci_types.ResponseCheckTx:
        return self.grpc_client.CheckTx(request)

    def send_query(self, request: abci_types.RequestQuery) -> abci_types.ResponseQuery:
        return self.grpc_client.Query(request)

    def send_commit(self, request: abci_types.RequestCommit) -> abci_types.ResponseCommit:
        return self.grpc_client.Commit(request)

    def send_init_chain(self, request: abci_types.RequestInitChain) -> abci_types.ResponseInitChain:
        return self.grpc_client.InitChain(request)

    def send_begin_block(self, request: abci_types.RequestBeginBlock) -> abci_types.ResponseBeginBlock:
        return self.grpc_client.BeginBlock(request)

    def send_end_block(self, request: abci_types.RequestEndBlock) -> abci_types.ResponseEndBlock:
        return self.grpc_client.EndBlock(request)

    def send_list_snapshots(self, request: abci_types.RequestListSnapshots) -> abci_types.ResponseListSnapshots:
        return self.grpc_client.ListSnapshots(request)

    def send_offer_snapshot(self, request: abci_types.RequestOfferSnapshot) -> abci_types.ResponseOfferSnapshot:
        return self.grpc_client.OfferSnapshot(request)

    def send_load_snapshot_chunk(self,
                                 request: abci_types.RequestLoadSnapshotChunk) -> abci_types.ResponseLoadSnapshotChunk:
        return self.grpc_client.LoadSnapshotChunk(request)

    def send_apply_snapshot_chunk(self,
                                  request: abci_types.RequestApplySnapshotChunk) -> abci_types.ResponseApplySnapshotChunk:
        return self.grpc_client.ApplySnapshotChunk(request)
