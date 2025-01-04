# tests/unit/test_move_to_thread.py

import asyncio
import pytest
import threading
import logging
from pynnex import nx_signal, nx_slot, nx_with_signals
from pynnex import nx_with_worker

logger = logging.getLogger(__name__)


@nx_with_worker
class WorkerA:
    """첫 번째 워커 스레드."""

    async def run(self, *args, **kwargs):
        logger.info("[WorkerA] run() started")
        await self.start_queue()


@nx_with_worker
class WorkerB:
    """두 번째 워커 스레드."""

    async def run(self, *args, **kwargs):
        logger.info("[WorkerB] run() started")
        await self.start_queue()


@nx_with_signals
class Mover:
    """
    move_to_thread 테스트용 객체.
    메인 스레드에서 생성 후,
    WorkerA -> WorkerB 순서로 옮겨가며 시그널 동작을 확인한다.
    """

    @nx_signal
    def data_ready(self, value):
        """데이터가 준비되었음을 알리는 시그널."""

    def __init__(self):
        super().__init__()
        self.emitted_values = []

    def do_work(self, value):
        """
        별도 스레드(또는 메인 스레드)에서
        어떤 작업을 수행하고 시그널을 emit한다고 가정.
        """
        logger.info("[Mover][do_work] value=%s (thread=%s)", value, threading.current_thread().name)
        self.data_ready.emit(value)

    @nx_slot
    def on_data_ready(self, value):
        """
        data_ready 시그널을 수신하는 슬롯.
        """
        logger.info("[Mover][on_data_ready] value=%s (thread=%s)", value, threading.current_thread().name)
        self.emitted_values.append(value)


@pytest.mark.asyncio
async def test_move_to_thread():
    """
    1) Mover 객체를 메인 스레드에서 생성
    2) WorkerA 스레드로 move_to_thread
    3) WorkerB 스레드로 move_to_thread
    각각의 단계에서 시그널이 잘 emit/receive 되는지 확인
    """

    logger.info("=== test_move_to_thread START ===")

    # 1) 메인 스레드에서 Mover 생성
    mover = Mover()

    # 시그널 자체를 mover 내부 on_data_ready와 연결
    mover.data_ready.connect(mover, mover.on_data_ready)

    # 2) WorkerA 준비
    worker_a = WorkerA()
    worker_a.start()  # 스레드 + 이벤트 루프 시작
    await asyncio.sleep(0.2)  # worker_a run() 시작 대기

    # move_to_thread
    mover.move_to_thread(worker_a)
    logger.info("Mover moved to WorkerA thread")

    # do_work 호출 -> WorkerA 스레드에서 emit 발생
    mover.do_work("from WorkerA")
    await asyncio.sleep(0.3)  # 시그널 처리 대기

    assert "from WorkerA" in mover.emitted_values, "WorkerA에서 emit된 데이터가 수신되어야 함"

    # 3) WorkerB 준비
    worker_b = WorkerB()
    worker_b.start()
    await asyncio.sleep(0.2)

    mover.move_to_thread(worker_b)
    logger.info("Mover moved to WorkerB thread")

    # do_work -> 이제 WorkerB에서 emit
    mover.do_work("from WorkerB")
    await asyncio.sleep(0.3)

    assert "from WorkerB" in mover.emitted_values, "WorkerB에서 emit된 데이터가 수신되어야 함"

    # 정리
    worker_a.stop()
    worker_b.stop()

    logger.info("=== test_move_to_thread DONE ===")
