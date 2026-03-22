"""Curses-based persistent TUI application for weathertype."""

import curses
import locale
import threading
import time

from weathertype.api.open_meteo import OpenMeteoClient
from weathertype.api.regional import RegionalGridClient
from weathertype.api.rainviewer import RainViewerClient
from weathertype.api.models import WeatherProfile, ForecastData, RegionalGrid, RadarData
from weathertype.tui.ansi_parser import init_color_pairs
from weathertype.tui.views import (
    View,
    SkewTView,
    HodogramView,
    MeteographView,
    ForecastView,
    SummaryView,
    RegionalTempView,
    RegionalPressureView,
    RadarView,
)

MIN_LINES = 20
MIN_COLS = 50
HEADER_LINES = 2
FOOTER_LINES = 2


class WeathertypeTUI:
    """Persistent full-screen weather visualization."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        location_name: str,
        refresh_interval: int = 3600,
    ):
        self._lat = latitude
        self._lon = longitude
        self._location = location_name
        self._refresh_interval = refresh_interval

        self._client = OpenMeteoClient()
        self._regional_client = RegionalGridClient()
        self._radar_client = RainViewerClient()
        self._profile: WeatherProfile | None = None
        self._forecast: ForecastData | None = None
        self._regional_temp: RegionalGrid | None = None
        self._regional_pressure: RegionalGrid | None = None
        self._radar: RadarData | None = None
        self._data_lock = threading.Lock()

        self._fetching = False
        self._fetch_complete = False
        self._fetch_error: str | None = None
        self._last_fetch: float = 0.0
        self._last_fetch_time_str = ""

        self._views: list[View] = [
            SkewTView(),
            HodogramView(),
            MeteographView(),
            ForecastView(),
            SummaryView(),
            RegionalTempView(),
            RegionalPressureView(),
            RadarView(),
        ]
        self._current_view = 0
        self._scroll_offset = 0
        self._content_height = 0
        self._needs_redraw = True

        self._stdscr: curses.window | None = None
        self._pad: curses.window | None = None

    def start(self) -> int:
        locale.setlocale(locale.LC_ALL, "")
        try:
            curses.wrapper(self._run)
        except KeyboardInterrupt:
            pass
        return 0

    def _run(self, stdscr: curses.window) -> None:
        self._stdscr = stdscr
        stdscr.timeout(200)
        curses.curs_set(0)

        if curses.has_colors():
            init_color_pairs()

        # Initial fetch
        self._request_data_fetch()

        while True:
            # Check for completed fetch
            if self._fetch_complete:
                self._fetch_complete = False
                self._needs_redraw = True

            # Auto-refresh check
            if (
                not self._fetching
                and self._last_fetch > 0
                and time.monotonic() - self._last_fetch > self._refresh_interval
            ):
                self._request_data_fetch()

            # Draw
            if self._needs_redraw:
                self._redraw()
                self._needs_redraw = False

            # Handle input
            key = stdscr.getch()
            if key == -1:
                continue

            if key == ord("q"):
                break
            elif key == curses.KEY_RESIZE:
                self._handle_resize()
            elif key == ord("\t"):
                self._current_view = (self._current_view + 1) % len(self._views)
                self._scroll_offset = 0
                self._needs_redraw = True
            elif key == curses.KEY_BTAB:
                self._current_view = (self._current_view - 1) % len(self._views)
                self._scroll_offset = 0
                self._needs_redraw = True
            elif ord("1") <= key <= ord("8"):
                idx = key - ord("1")
                if idx < len(self._views):
                    self._current_view = idx
                    self._scroll_offset = 0
                    self._needs_redraw = True
            elif key == ord("r"):
                self._client.clear_cache()
                self._regional_client.clear_cache()
                self._request_data_fetch()
                self._needs_redraw = True
            elif key in (curses.KEY_DOWN, ord("j")):
                self._scroll_down()
            elif key in (curses.KEY_UP, ord("k")):
                self._scroll_up()

    def _redraw(self) -> None:
        stdscr = self._stdscr
        if stdscr is None:
            return

        try:
            h, w = stdscr.getmaxyx()
        except curses.error:
            return

        if h < MIN_LINES or w < MIN_COLS:
            stdscr.clear()
            msg = "Terminal too small"
            try:
                stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
            except curses.error:
                pass
            stdscr.refresh()
            return

        stdscr.clear()
        self._draw_header(w)
        self._draw_footer(h, w)
        stdscr.noutrefresh()

        # Draw content area via pad
        draw_h = h - HEADER_LINES - FOOTER_LINES
        draw_w = w

        if self._profile is None and not self._fetching:
            # No data and not loading — error state
            msg = self._fetch_error or "No data"
            try:
                stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
            except curses.error:
                pass
            stdscr.noutrefresh()
            curses.doupdate()
            return

        if self._profile is None:
            # Still loading
            msg = "Loading weather data..."
            try:
                stdscr.addstr(h // 2, max(0, (w - len(msg)) // 2), msg)
            except curses.error:
                pass
            stdscr.noutrefresh()
            curses.doupdate()
            return

        # Create pad large enough for content (oversize to be safe)
        pad_h = max(draw_h, 200)
        pad_w = max(draw_w, 120)
        try:
            self._pad = curses.newpad(pad_h, pad_w)
        except curses.error:
            curses.doupdate()
            return

        view = self._views[self._current_view]
        with self._data_lock:
            view.update_data(
                self._profile, self._forecast,
                regional_temp=self._regional_temp,
                regional_pressure=self._regional_pressure,
                radar=self._radar,
            )

        try:
            self._content_height = view.render(self._pad, draw_w, draw_h)
        except Exception:
            self._content_height = 0

        # Clamp scroll
        max_scroll = max(0, self._content_height - draw_h)
        self._scroll_offset = max(0, min(self._scroll_offset, max_scroll))

        try:
            self._pad.noutrefresh(
                self._scroll_offset, 0,
                HEADER_LINES, 0,
                h - FOOTER_LINES - 1, w - 1,
            )
        except curses.error:
            pass

        curses.doupdate()

    def _draw_header(self, w: int) -> None:
        stdscr = self._stdscr
        if stdscr is None:
            return

        # Line 0: title bar
        title = f" weathertype  |  {self._location}"
        status = ""
        if self._fetching:
            status = " Refreshing... "
        elif self._last_fetch_time_str:
            status = f" Updated: {self._last_fetch_time_str} "

        padding = w - len(title) - len(status)
        line0 = title + " " * max(0, padding) + status
        line0 = line0[:w]

        try:
            stdscr.addstr(0, 0, line0, curses.A_REVERSE | curses.A_BOLD)
        except curses.error:
            pass

        # Line 1: separator
        try:
            stdscr.addstr(1, 0, " " * (w - 1))
        except curses.error:
            pass

    def _draw_footer(self, h: int, w: int) -> None:
        stdscr = self._stdscr
        if stdscr is None:
            return

        # Build tab bar with view names
        footer_y = h - FOOTER_LINES

        # Separator line
        try:
            stdscr.addstr(footer_y, 0, " " * (w - 1))
        except curses.error:
            pass

        # View tabs + keybinding hints
        tabs = ""
        for i, view in enumerate(self._views):
            label = f" [{view.shortcut}] {view.name} "
            if i == self._current_view:
                # Highlight active view — we'll write it separately with attr
                tabs += label
            else:
                tabs += label

        keys_hint = " [Tab] Cycle  [r] Refresh  [j/k] Scroll  [q] Quit"
        line = tabs + keys_hint

        tab_y = h - 1
        col = 0
        for i, view in enumerate(self._views):
            label = f" [{view.shortcut}] {view.name} "
            attr = curses.A_REVERSE | curses.A_BOLD if i == self._current_view else curses.A_DIM
            try:
                stdscr.addstr(tab_y, col, label, attr)
            except curses.error:
                pass
            col += len(label)

        # Separator
        try:
            stdscr.addstr(tab_y, col, " | ", curses.A_DIM)
        except curses.error:
            pass
        col += 3

        # Keys hint
        remaining = w - col - 1
        hint = keys_hint[:remaining]
        try:
            stdscr.addstr(tab_y, col, hint, curses.A_DIM)
        except curses.error:
            pass

        # Scroll indicator on separator line if applicable
        if self._content_height > 0:
            draw_h = h - HEADER_LINES - FOOTER_LINES
            if self._content_height > draw_h:
                max_scroll = self._content_height - draw_h
                pct = self._scroll_offset / max_scroll if max_scroll > 0 else 0
                indicator = f" [{self._scroll_offset+1}-{self._scroll_offset+draw_h}/{self._content_height}] "
                try:
                    stdscr.addstr(footer_y, max(0, w - len(indicator) - 1), indicator, curses.A_DIM)
                except curses.error:
                    pass

    def _scroll_down(self) -> None:
        stdscr = self._stdscr
        if stdscr is None:
            return
        h, _ = stdscr.getmaxyx()
        draw_h = h - HEADER_LINES - FOOTER_LINES
        max_scroll = max(0, self._content_height - draw_h)
        if self._scroll_offset < max_scroll:
            self._scroll_offset += 1
            self._needs_redraw = True

    def _scroll_up(self) -> None:
        if self._scroll_offset > 0:
            self._scroll_offset -= 1
            self._needs_redraw = True

    def _handle_resize(self) -> None:
        if self._stdscr is not None:
            curses.update_lines_cols()
            self._stdscr.clear()
            self._needs_redraw = True

    def _request_data_fetch(self) -> None:
        if self._fetching:
            return
        self._fetching = True
        self._fetch_error = None
        t = threading.Thread(target=self._fetch_worker, daemon=True)
        t.start()

    def _fetch_worker(self) -> None:
        try:
            from concurrent.futures import ThreadPoolExecutor

            def fetch_profile():
                return self._client.get_weather_profile(self._lat, self._lon)

            def fetch_forecast():
                return self._client.get_forecast_data(self._lat, self._lon, hours=36)

            def fetch_regional_temp():
                return self._regional_client.get_regional_temperature(self._lat, self._lon)

            def fetch_regional_pressure():
                return self._regional_client.get_regional_pressure(self._lat, self._lon)

            def fetch_radar():
                return self._radar_client.get_radar_data(self._lat, self._lon)

            with ThreadPoolExecutor(max_workers=5) as pool:
                f_profile = pool.submit(fetch_profile)
                f_forecast = pool.submit(fetch_forecast)
                f_temp = pool.submit(fetch_regional_temp)
                f_pressure = pool.submit(fetch_regional_pressure)
                f_radar = pool.submit(fetch_radar)

                profile_resp = f_profile.result()
                forecast_resp = f_forecast.result()
                temp_resp = f_temp.result()
                pressure_resp = f_pressure.result()
                radar_resp = f_radar.result()

            with self._data_lock:
                if profile_resp.error:
                    self._fetch_error = profile_resp.error
                else:
                    self._profile = profile_resp.profile

                if not forecast_resp.error:
                    self._forecast = forecast_resp.forecast

                if not temp_resp.error and temp_resp.grid:
                    self._regional_temp = temp_resp.grid

                if not pressure_resp.error and pressure_resp.grid:
                    self._regional_pressure = pressure_resp.grid

                if not radar_resp.error and radar_resp.radar:
                    self._radar = radar_resp.radar

            self._last_fetch = time.monotonic()
            self._last_fetch_time_str = time.strftime("%H:%M:%S")
        except Exception as e:
            self._fetch_error = str(e)
        finally:
            self._fetching = False
            self._fetch_complete = True
