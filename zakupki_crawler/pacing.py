from __future__ import annotations

import random
import time
from collections.abc import Callable

from playwright.sync_api import Locator, Page

from zakupki_crawler.models import PacingConfig


class HumanPacer:
    def __init__(
        self,
        config: PacingConfig,
        rng: random.Random | None = None,
        sleep_func: Callable[[float], None] | None = None,
    ) -> None:
        self.config = config
        self.rng = rng or random.Random()
        self.sleep_func = sleep_func or time.sleep

    def normal_delay_ms(self) -> int:
        return self.rng.randint(self.config.min_delay_ms, self.config.max_delay_ms)

    def long_delay_ms(self) -> int:
        return self.rng.randint(self.config.long_pause_min_ms, self.config.long_pause_max_ms)

    def pause(self, *, extra_long_allowed: bool = True, multiplier: float = 1.0) -> int:
        delay_ms = int(self.normal_delay_ms() * multiplier)
        self.sleep_func(delay_ms / 1000)
        if extra_long_allowed and self.rng.random() < self.config.long_pause_chance:
            extra_ms = self.long_delay_ms()
            self.sleep_func(extra_ms / 1000)
            delay_ms += extra_ms
        return delay_ms

    def post_navigation_pause(self) -> int:
        return self.pause(multiplier=1.15)

    def between_purchase_pause(self) -> int:
        return self.pause(multiplier=1.35)

    def between_page_pause(self) -> int:
        return self.pause(multiplier=1.6)

    def prepare_locator_click(self, page: Page, locator: Locator) -> None:
        locator.scroll_into_view_if_needed(timeout=10_000)
        handle = locator.element_handle(timeout=10_000)
        if handle is None:
            return

        box = handle.bounding_box()
        if not box:
            return

        target_x = box["x"] + box["width"] * self.rng.uniform(0.2, 0.8)
        target_y = box["y"] + box["height"] * self.rng.uniform(0.2, 0.8)
        steps = self.rng.randint(6, 18)
        page.mouse.move(target_x, target_y, steps=steps)

    def click(self, page: Page, locator: Locator, *, post_navigation: bool = True) -> None:
        self.pause()
        self.prepare_locator_click(page, locator)
        locator.click(timeout=20_000)
        if post_navigation:
            self.post_navigation_pause()
