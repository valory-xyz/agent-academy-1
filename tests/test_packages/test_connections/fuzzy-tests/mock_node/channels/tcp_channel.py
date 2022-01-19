import logging
import socket
from io import BytesIO
from typing import Generator

from aea.exceptions import enforce

from packages.valory.connections.abci.tendermint.abci import types_pb2 as abci_types
from packages.valory.connections.abci.connection import _TendermintABCISerializer
from base import BaseChannel

_default_logger = logging.getLogger(__name__)

logging.basicConfig()


class TcpChannel(BaseChannel):
    MAX_READ_IN_BYTES = 64 * 1024  # Max we'll consume on a read stream

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 26658)
        self.logger = _default_logger

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.connect((host, port))

    def _get_response(self) -> abci_types.Response:
        data = BytesIO()

        bits = self.tcp_socket.recv(self.MAX_READ_IN_BYTES)

        if len(bits) == 0:
            raise EOFError

        self.logger.debug(f"Received {len(bits)} bytes from abci")
        data.write(bits)
        data.seek(0)

        message_iterator: Generator[
            abci_types.Response, None, None
        ] = _TendermintABCISerializer.read_messages(data, abci_types.Response)
        sentinel = object()
        num_messages = 0
        response = None

        while True:
            message = next(message_iterator, sentinel)
            if response is None:
                response = message

            if message == sentinel:
                # we reached the end of the iterator
                break

            num_messages += 1

        enforce(
            num_messages == 1,
            "a single message was expected"
        )

        return response

    def send_info(self, request: abci_types.RequestInfo) -> abci_types.ResponseInfo:
        message = abci_types.Request()
        message.info.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "info",
            f"expected response of type info, {response_type} was received"
        )

        return response.info

    def send_echo(self, request: abci_types.RequestEcho) -> abci_types.ResponseEcho:
        message = abci_types.Request()
        message.echo.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "echo",
            f"expected response of type echo, {response_type} was received"
        )

        return response.echo

    def send_flush(self, request: abci_types.RequestFlush) -> abci_types.ResponseFlush:
        message = abci_types.Request()
        message.flush.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "flush",
            f"expected response of type flush, {response_type} was received"
        )

        return response.flush

    def send_set_option(self, request: abci_types.RequestSetOption) -> abci_types.ResponseSetOption:
        message = abci_types.Request()
        message.set_option.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "set_option",
            f"expected response of type set_option, {response_type} was received"
        )

        return response.set_option

    def send_deliver_tx(self, request: abci_types.RequestDeliverTx) -> abci_types.ResponseDeliverTx:
        message = abci_types.Request()
        message.deliver_tx.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "deliver_tx",
            f"expected response of type deliver_tx, {response_type} was received"
        )

        return response.deliver_tx

    def send_check_tx(self, request: abci_types.RequestCheckTx) -> abci_types.ResponseCheckTx:
        message = abci_types.Request()
        message.check_tx.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "check_tx",
            f"expected response of type check_tx, {response_type} was received"
        )

        return response.check_tx

    def send_query(self, request: abci_types.RequestQuery) -> abci_types.ResponseQuery:
        message = abci_types.Request()
        message.query.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "query",
            f"expected response of type query, {response_type} was received"
        )

        return response.query

    def send_commit(self, request: abci_types.RequestCommit) -> abci_types.ResponseCommit:
        message = abci_types.Request()
        message.commit.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "commit",
            f"expected response of type commit, {response_type} was received"
        )

        return response.commit

    def send_init_chain(self, request: abci_types.RequestInitChain) -> abci_types.ResponseInitChain:
        message = abci_types.Request()
        message.init_chain.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "init_chain",
            f"expected response of type init_chain, {response_type} was received"
        )

        return response.init_chain

    def send_begin_block(self, request: abci_types.RequestBeginBlock) -> abci_types.ResponseBeginBlock:
        message = abci_types.Request()
        message.begin_block.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "begin_block",
            f"expected response of type begin_block, {response_type} was received"
        )

        return response.begin_block

    def send_end_block(self, request: abci_types.RequestEndBlock) -> abci_types.ResponseEndBlock:
        message = abci_types.Request()
        message.end_block.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "end_block",
            f"expected response of type end_block, {response_type} was received"
        )

        return response.end_block

    def send_list_snapshots(self, request: abci_types.RequestListSnapshots) -> abci_types.ResponseListSnapshots:
        message = abci_types.Request()
        message.list_snapshots.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "list_snapshots",
            f"expected response of type list_snapshots, {response_type} was received"
        )

        return response.list_snapshots

    def send_offer_snapshot(self, request: abci_types.RequestOfferSnapshot) -> abci_types.ResponseOfferSnapshot:
        message = abci_types.Request()
        message.offer_snapshot.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "offer_snapshot",
            f"expected response of type offer_snapshot, {response_type} was received"
        )

        return response.offer_snapshot

    def send_load_snapshot_chunk(self,
                                 request: abci_types.RequestLoadSnapshotChunk) -> abci_types.ResponseLoadSnapshotChunk:
        message = abci_types.Request()
        message.load_snapshot_chunk.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "load_snapshot_chunk",
            f"expected response of type load_snapshot_chunk, {response_type} was received"
        )

        return response.load_snapshot_chunk

    def send_apply_snapshot_chunk(
            self,
            request: abci_types.RequestApplySnapshotChunk
    ) -> abci_types.ResponseApplySnapshotChunk:
        message = abci_types.Request()
        message.apply_snapshot_chunk.CopyFrom(request)

        data = _TendermintABCISerializer.write_message(message)

        self.tcp_socket.send(data)

        response = self._get_response()
        response_type = response.WhichOneof('value')

        enforce(
            response_type == "apply_snapshot_chunk",
            f"expected response of type apply_snapshot_chunk, {response_type} was received"
        )

        return response.apply_snapshot_chunk
