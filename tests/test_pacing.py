from __future__ import annotations

import random

from zakupki_crawler.models import PacingConfig
from zakupki_crawler.pacing import HumanPacer


class FakeMouse:
    def __init__(self) -> None:
        self.moves: list[tuple[float, float, int]] = []

    def move(self, x: float, y: float, steps: int) -> None:
        self.moves.append((x, y, steps))


class FakePage:
    def __init__(self) -> None:
        self.mouse = FakeMouse()


class FakeHandle:
    def bounding_box(self) -> dict[str, float]:
        return {"x": 10.0, "y": 20.0, "width": 200.0, "height": 40.0}


class FakeLocator:
    def __init__(self) -> None:
        self.scrolled = False
        self.clicked = False

    def scroll_into_view_if_needed(self, timeout: int) -> None:
        self.scrolled = True

    def element_handle(self, timeout: int) -> FakeHandle:
        return FakeHandle()

    def click(self, timeout: int) -> None:
        self.clicked = True


def test_pause_respects_bounds_without_long_pause() -> None:
    calls: list[float] = []
    pacer = HumanPacer(
        PacingConfig(
            min_delay_ms=100,
            max_delay_ms=100,
            long_pause_chance=0,
            long_pause_min_ms=200,
            long_pause_max_ms=200,
        ),
        rng=random.Random(1),
        sleep_func=calls.append,
    )

    total = pacer.pause()

    assert total == 100
    assert calls == [0.1]


def test_click_uses_delay_wrapper_and_mouse_jitter() -> None:
    calls: list[float] = []
    pacer = HumanPacer(
        PacingConfig(
            min_delay_ms=100,
            max_delay_ms=100,
            long_pause_chance=0,
            long_pause_min_ms=200,
            long_pause_max_ms=200,
        ),
        rng=random.Random(2),
        sleep_func=calls.append,
    )
    page = FakePage()
    locator = FakeLocator()

    pacer.click(page, locator)

    assert locator.scrolled is True
    assert locator.clicked is True
    assert len(page.mouse.moves) == 1
    assert calls == [0.1, 0.114]


def test_pause_can_add_long_pause() -> None:
    calls: list[float] = []
    pacer = HumanPacer(
        PacingConfig(
            min_delay_ms=100,
            max_delay_ms=100,
            long_pause_chance=1,
            long_pause_min_ms=200,
            long_pause_max_ms=200,
        ),
        rng=random.Random(3),
        sleep_func=calls.append,
    )

    total = pacer.pause()

    assert total == 300
    assert calls == [0.1, 0.2]
