"""GrpcChannel for MockNode"""

import logging
from typing import Dict

import grpc  # type: ignore

import packages.valory.connections.abci.tendermint.abci.types_pb2 as abci_types  # type: ignore
import packages.valory.connections.abci.tendermint.abci.types_pb2_grpc as tendermint_grpc  # type: ignore

from .base import BaseChannel


_default_logger = logging.getLogger(__name__)

logging.basicConfig()


class GrpcChannel(BaseChannel):
    """Implements BaseChannel to use gRPC"""

    def __init__(self, **kwargs: Dict) -> None:
        """
        Initializes a GrpcChannel

        :param: host: the host of the ABCI app (localhost by default)
        :param: port: the port of the ABCI app (26658 by default)
        """
        super().__init__()

        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 26658)
        self.logger = _default_logger

        grpc_channel = grpc.insecure_channel(f"{host}:{port}")
        self.grpc_client = tendermint_grpc.ABCIApplicationStub(grpc_channel)

    def send_info(self, request: abci_types.RequestInfo) -> abci_types.ResponseInfo:
        """
        Sends an info request.

        :param: request: RequestInfo pb object
        :return: ResponseInfo pb object
        """
        return self.grpc_client.Info(request)

    def send_echo(self, request: abci_types.RequestEcho) -> abci_types.ResponseEcho:
        """
        Sends an echo request.

        :param: request: RequestEcho pb object
        :return: ResponseEcho pb object
        """
        return self.grpc_client.Echo(request)

    def send_flush(self, request: abci_types.RequestFlush) -> abci_types.ResponseFlush:
        """
        Sends an flush request.

        :param: request: RequestFlush pb object
        :return: ResponseFlush pb object
        """
        return self.grpc_client.Flush(request)

    def send_set_option(
        self, request: abci_types.RequestSetOption
    ) -> abci_types.ResponseSetOption:
        """
        Sends an setOption request.

        :param: request: RequestSetOption pb object
        :return: ResponseSetOption pb object
        """
        return self.grpc_client.SetOption(request)

    def send_deliver_tx(
        self, request: abci_types.RequestDeliverTx
    ) -> abci_types.ResponseDeliverTx:
        """
        Sends an deliverTx request.

        :param: request: RequestDeliverTx pb object
        :return: ResponseDeliverTx pb object
        """
        return self.grpc_client.DeliverTx(request)

    def send_check_tx(
        self, request: abci_types.RequestCheckTx
    ) -> abci_types.ResponseCheckTx:
        """
        Sends an checkTx request.

        :param: request: RequestCheckTx pb object
        :return: ResponseCheckTx pb object
        """
        return self.grpc_client.CheckTx(request)

    def send_query(self, request: abci_types.RequestQuery) -> abci_types.ResponseQuery:
        """
        Sends an query request.

        :param: request: RequestQuery pb object
        :return: ResponseQuery pb object
        """
        return self.grpc_client.Query(request)

    def send_commit(
        self, request: abci_types.RequestCommit
    ) -> abci_types.ResponseCommit:
        """
        Sends an commit request.

        :param: request: RequestCommit pb object
        :return: ResponseCommit pb object
        """
        return self.grpc_client.Commit(request)

    def send_init_chain(
        self, request: abci_types.RequestInitChain
    ) -> abci_types.ResponseInitChain:
        """
        Sends an initChain request.

        :param: request: RequestInitChain pb object
        :return: ResponseInitChain pb object
        """
        return self.grpc_client.InitChain(request)

    def send_begin_block(
        self, request: abci_types.RequestBeginBlock
    ) -> abci_types.ResponseBeginBlock:
        """
        Sends an beginBlock request.

        :param: request: RequestBeginBlock pb object
        :return: ResponseBeginBlock pb object
        """
        return self.grpc_client.BeginBlock(request)

    def send_end_block(
        self, request: abci_types.RequestEndBlock
    ) -> abci_types.ResponseEndBlock:
        """
        Sends an endBlock request.

        :param: request: RequestEndBlock pb object
        :return: ResponseEndBlock pb object
        """
        return self.grpc_client.EndBlock(request)

    def send_list_snapshots(
        self, request: abci_types.RequestListSnapshots
    ) -> abci_types.ResponseListSnapshots:
        """
        Sends an listSnapshots request.

        :param: request: RequestListSnapshots pb object
        :return: ResponseListSnapshots pb object
        """
        return self.grpc_client.ListSnapshots(request)

    def send_offer_snapshot(
        self, request: abci_types.RequestOfferSnapshot
    ) -> abci_types.ResponseOfferSnapshot:
        """
        Sends an offerSnapshot request.

        :param: request: RequestOfferSnapshot pb object
        :return: ResponseOfferSnapshot pb object
        """
        return self.grpc_client.OfferSnapshot(request)

    def send_load_snapshot_chunk(
        self, request: abci_types.RequestLoadSnapshotChunk
    ) -> abci_types.ResponseLoadSnapshotChunk:
        """
        Sends an loadSnapshotChunk request.

        :param: request: RequestLoadSnapshotChunk pb object
        :return: ResponseLoadSnapshotChunk pb object
        """
        return self.grpc_client.LoadSnapshotChunk(request)

    def send_apply_snapshot_chunk(
        self, request: abci_types.RequestApplySnapshotChunk
    ) -> abci_types.ResponseApplySnapshotChunk:
        """
        Sends an applySnapshotChunk request.

        :param: request: RequestApplySnapshotChunk pb object
        :return: ResponseApplySnapshotChunk pb object
        """
        return self.grpc_client.ApplySnapshotChunk(request)
