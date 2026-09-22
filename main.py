import kivy
kivy.require("2.1.0")
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.slider import Slider
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
from kivy.core.window import Window
import requests
import json
import urllib.request
import datetime
import math
import threading
import time

# Импорты внутри функций
import sys
import os

# Цвета
BG_COLOR = (0.08, 0.09, 0.12, 1)
CARD_COLOR = (0.12, 0.13, 0.18, 1)
ACCENT = (0.20, 0.55, 0.90, 1)
GREEN = (0.18, 0.70, 0.35, 1)
RED = (0.85, 0.25, 0.25, 1)
TEXT_LIGHT = (0.90, 0.90, 0.92, 1)
TEXT_DIM = (0.55, 0.56, 0.60, 1)
YELLOW = (0.95, 0.80, 0.20, 1)

PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "DOGE/USDT", "AVAX/USDT", "DOT/USDT", "LINK/USDT",
    "MATIC/USDT", "LTC/USDT", "TRX/USDT", "ATOM/USDT"
]

TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]
TIMEFRAME_VALUES = {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}

INDICATORS = ["RSI", "MACD", "Bollinger", "Stochastic", "EMA", "Williams %R", "ADX", "Volume"]


def fetch_klines(symbol, interval, limit=200):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol.replace('/', '')}&interval={interval}&limit={limit}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return data
    except Exception as e:
        print(f"Fetch error: {e}")
        return []


def parse_candles(raw):
    candles = []
    for row in raw:
        t = int(row[0] / 1000)
        o, h, l, c = float(row[1]), float(row[2]), float(row[3]), float(row[4])
        v = float(row[5])
        candles.append({"time": t, "open": o, "high": h, "low": l, "close": c, "volume": v})
    return candles


def calc_rsi(candles, period=14):
    if len(candles) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        diff = candles[i]["close"] - candles[i - 1]["close"]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


def calc_ema(values, period):
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    ema = [values[0]]
    for i in range(1, len(values)):
        ema.append(values[i] * k + ema[-1] * (1 - k))
    return ema


def calc_macd(candles):
    closes = [c["close"] for c in candles]
    if len(closes) < 26:
        return 0.0, 0.0, 0.0
    ema12 = calc_ema(closes, 12)
    ema26 = calc_ema(closes, 26)
    macd_line = [ema12[i] - ema26[i] for i in range(len(closes))]
    signal = calc_ema(macd_line, 9)
    hist = macd_line[-1] - signal[-1]
    return macd_line[-1], signal[-1], hist


def calc_bollinger(candles, period=20, std_mult=2):
    if len(candles) < period:
        return 0, 0, 0
    closes = [c["close"] for c in candles[-period:]]
    mean = sum(closes) / period
    variance = sum((c - mean) ** 2 for c in closes) / period
    std = math.sqrt(variance)
    upper = mean + std_mult * std
    lower = mean - std_mult * std
    return upper, mean, lower


def calc_stochastic(candles, period=14):
    if len(candles) < period:
        return 50.0
    highs = [c["high"] for c in candles[-period:]]
    lows = [c["low"] for c in candles[-period:]]
    highest = max(highs)
    lowest = min(lows)
    if highest == lowest:
        return 50.0
    close = candles[-1]["close"]
    return (close - lowest) / (highest - lowest) * 100.0


def calc_williams(candles, period=14):
    if len(candles) < period:
        return -50.0
    highs = [c["high"] for c in candles[-period:]]
    lows = [c["low"] for c in candles[-period:]]
    highest = max(highs)
    lowest = min(lows)
    if highest == lowest:
        return -50.0
    close = candles[-1]["close"]
    return (highest - close) / (highest - lowest) * -100.0


def calc_adx(candles, period=14):
    if len(candles) < period + 1:
        return 20.0
    trs = []
    plus_dms = []
    minus_dms = []
    for i in range(-period, 0):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_high = candles[i - 1]["high"]
        prev_low = candles[i - 1]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
        up_move = high - prev_high
        down_move = prev_low - low
        if up_move > down_move and up_move > 0:
            plus_dms.append(up_move)
        else:
            plus_dms.append(0)
        if down_move > up_move and down_move > 0:
            minus_dms.append(down_move)
        else:
            minus_dms.append(0)
    atr = sum(trs) / period if trs else 1
    plus_di = (sum(plus_dms) / period / atr) * 100 if atr > 0 else 0
    minus_di = (sum(minus_dms) / period / atr) * 100 if atr > 0 else 0
    if plus_di + minus_di == 0:
        return 20.0
    dx = abs(plus_di - minus_di) / (plus_di + minus_di) * 100
    return dx


def generate_signal(candles, indicator):
    if not candles or len(candles) < 30:
        return "NO DATA", 0

    price = candles[-1]["close"]

    if indicator == "RSI":
        rsi = calc_rsi(candles)
        if rsi < 30:
            return "BUY", rsi
        elif rsi > 70:
            return "SELL", rsi
        return "NEUTRAL", rsi

    elif indicator == "MACD":
        macd_line, signal_line, hist = calc_macd(candles)
        if hist > 0 and macd_line > signal_line:
            return "BUY", hist
        elif hist < 0 and macd_line < signal_line:
            return "SELL", hist
        return "NEUTRAL", hist

    elif indicator == "Bollinger":
        upper, mid, lower = calc_bollinger(candles)
        if price <= lower:
            return "BUY", price
        elif price >= upper:
            return "SELL", price
        return "NEUTRAL", price

    elif indicator == "Stochastic":
        st = calc_stochastic(candles)
        if st < 20:
            return "BUY", st
        elif st > 80:
            return "SELL", st
        return "NEUTRAL", st

    elif indicator == "EMA":
        closes = [c["close"] for c in candles]
        ema_fast = calc_ema(closes, 9)
        ema_slow = calc_ema(closes, 21)
        if ema_fast[-1] > ema_slow[-1]:
            return "BUY", ema_fast[-1]
        else:
            return "SELL", ema_fast[-1]

    elif indicator == "Williams %R":
        wr = calc_williams(candles)
        if wr <= -80:
            return "BUY", wr
        elif wr >= -20:
            return "SELL", wr
        return "NEUTRAL", wr

    elif indicator == "ADX":
        adx = calc_adx(candles)
        closes = [c["close"] for c in candles]
        ema_fast = calc_ema(closes, 9)
        ema_slow = calc_ema(closes, 21)
        if adx > 25 and ema_fast[-1] > ema_slow[-1]:
            return "BUY", adx
        elif adx > 25 and ema_fast[-1] < ema_slow[-1]:
            return "SELL", adx
        return "NEUTRAL", adx

    elif indicator == "Volume":
        if len(candles) < 20:
            return "NEUTRAL", 0
        avg_vol = sum(c["volume"] for c in candles[-20:-1]) / 19
        cur_vol = candles[-1]["volume"]
        price_up = candles[-1]["close"] > candles[-2]["close"]
        if cur_vol > avg_vol * 1.5 and price_up:
            return "BUY", cur_vol
        elif cur_vol > avg_vol * 1.5 and not price_up:
            return "SELL", cur_vol
        return "NEUTRAL", cur_vol

    return "NEUTRAL", 0


class ChartWidget(Widget):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.candles = []
        self.bind(size=self._update)
        self.bind(pos=self._update)

    def _update(self, *args):
        self.draw()

    def set_candles(self, candles):
        self.candles = candles
        self.draw()

    def draw(self):
        self.canvas.clear()
        if not self.candles or self.width < 10 or self.height < 10:
            return
        n = len(self.candles)
        if n < 2:
            return
        w = self.width
        h = self.height
        prices = [c["close"] for c in self.candles]
        min_p = min(prices)
        max_p = max(prices)
        if max_p == min_p:
            return
        step_x = w / max(n - 1, 1)
        with self.canvas:
            Color(*ACCENT)
            points = []
            for i, p in enumerate(prices):
                x = i * step_x
                y = (p - min_p) / (max_p - min_p) * (h - 20) + 10
                points.extend([x, y])
            if len(points) >= 4:
                Line(points=points, width=1.2)
            Color(0.15, 0.16, 0.20, 0.5)
            Line(points=[0, h * 0.5, w, h * 0.5], width=0.5)
            Line(points=[0, h * 0.25, w, h * 0.25], width=0.5)
            Line(points=[0, h * 0.75, w, h * 0.75], width=0.5)


class IndicatorCard(BoxLayout):
    def __init__(self, name, signal, value, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.size_hint_y = None
        self.height = 70
        self.padding = [10, 5]
        self.spacing = 3

        with self.canvas.before:
            Color(*CARD_COLOR)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

        top_row = BoxLayout(size_hint_y=None, height=25, spacing=5)
        name_label = Label(text=name, color=TEXT_LIGHT, font_size="13sp", bold=True, size_hint_x=0.5)
        top_row.add_widget(name_label)

        sig_color = GREEN if signal == "BUY" else RED if signal == "SELL" else YELLOW
        sig_label = Label(text=signal, color=sig_color, font_size="13sp", bold=True, size_hint_x=0.5)
        top_row.add_widget(sig_label)
        self.add_widget(top_row)

        val_text = f"Value: {value:.2f}" if isinstance(value, float) else f"Value: {value}"
        val_label = Label(text=val_text, color=TEXT_DIM, font_size="11sp", size_hint_y=None, height=18)
        self.add_widget(val_label)

    def _update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class TradingApp(App):
    def build(self):
        self.title = "Trading Helper"
        self.selected_pair = PAIRS[0]
        self.selected_tf = "15m"
        self.selected_indicator = "RSI"
        self.martingale_level = 1
        self.candles = []
        self.title_color = ACCENT

        root = BoxLayout(orientation="vertical", padding=10, spacing=8)

        with root.canvas.before:
            Color(*BG_COLOR)
            self.bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)
        self.root_widget = root

        header = Label(
            text="Trading Helper",
            color=ACCENT,
            font_size="22sp",
            bold=True,
            size_hint_y=None,
            height=40
        )
        root.add_widget(header)

        pair_spinner = Spinner(
            text=self.selected_pair,
            values=PAIRS,
            size_hint_y=None,
            height=40,
            background_color=ACCENT,
            color=TEXT_LIGHT
        )
        pair_spinner.bind(text=self.on_pair_change)
        root.add_widget(pair_spinner)

        tf_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
        for tf in TIMEFRAMES:
            btn = ToggleButton(
                text=tf,
                group="timeframe",
                state="down" if tf == self.selected_tf else "normal",
                size_hint_x=1,
                font_size="12sp"
            )
            btn.bind(on_release=lambda btn: self.on_tf_change(btn.text))
            tf_row.add_widget(btn)
        root.add_widget(tf_row)

        ind_spinner = Spinner(
            text=self.selected_indicator,
            values=INDICATORS,
            size_hint_y=None,
            height=40,
            background_color=ACCENT,
            color=TEXT_LIGHT
        )
        ind_spinner.bind(text=self.on_indicator_change)
        root.add_widget(ind_spinner)

        self.chart = ChartWidget(size_hint_y=None, height=180)
        root.add_widget(self.chart)

        info_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=30, spacing=5)
        self.price_label = Label(text="Price: --", color=TEXT_LIGHT, font_size="14sp", bold=True)
        self.signal_label = Label(text="Signal: --", color=YELLOW, font_size="14sp", bold=True)
        info_box.add_widget(self.price_label)
        info_box.add_widget(self.signal_label)
        root.add_widget(info_box)

        self.scroll = ScrollView(size_hint=(1, 1))
        self.results_grid = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.results_grid.bind(minimum_height=self.results_grid.setter("height"))
        self.scroll.add_widget(self.results_grid)
        root.add_widget(self.scroll)

        martingale_box = BoxLayout(orientation="horizontal", size_hint_y=None, height=40, spacing=5)
        m_label = Label(text="Martingale: 1", color=TEXT_LIGHT, font_size="13sp", size_hint_x=0.4)
        m_down = Button(text="-", size_hint_x=0.2, font_size="16sp")
        m_up = Button(text="+", size_hint_x=0.2, font_size="16sp")
        m_reset = Button(text="Reset", size_hint_x=0.2, font_size="11sp")
        m_down.bind(on_release=lambda *a: self.change_martingale(-1))
        m_up.bind(on_release=lambda *a: self.change_martingale(1))
        m_reset.bind(on_release=lambda *a: self.reset_martingale())
        self.m_label = m_label
        martingale_box.add_widget(m_label)
        martingale_box.add_widget(m_down)
        martingale_box.add_widget(m_up)
        martingale_box.add_widget(m_reset)
        root.add_widget(martingale_box)

        analyze_btn = Button(
            text="Analyze",
            size_hint_y=None,
            height=50,
            background_color=ACCENT,
            color=TEXT_LIGHT,
            font_size="16sp",
            bold=True
        )
        analyze_btn.bind(on_release=lambda *a: self.analyze())
        root.add_widget(analyze_btn)

        self.status_label = Label(text="Ready", color=TEXT_DIM, font_size="11sp", size_hint_y=None, height=20)
        root.add_widget(self.status_label)

        Clock.schedule_once(lambda dt: self.analyze(), 2)
        return root

    def _update_bg(self, *args):
        self.bg_rect.pos = self.root_widget.pos
        self.bg_rect.size = self.root_widget.size

    def on_pair_change(self, spinner, text):
        self.selected_pair = text
        self.analyze()

    def on_tf_change(self, text):
        self.selected_tf = text
        self.analyze()

    def on_indicator_change(self, spinner, text):
        self.selected_indicator = text

    def change_martingale(self, delta):
        self.martingale_level = max(1, min(5, self.martingale_level + delta))
        self.m_label.text = f"Martingale: {self.martingale_level}"

    def reset_martingale(self):
        self.martingale_level = 1
        self.m_label.text = "Martingale: 1"

    def analyze(self):
        self.status_label.text = f"Loading {self.selected_pair} {self.selected_tf}..."
        threading.Thread(target=self._do_analyze, daemon=True).start()

    def _do_analyze(self):
        symbol = self.selected_pair.replace("/", "")
        interval = self.selected_tf
        raw = fetch_klines(symbol, interval, 200)
        if not raw:
            Clock.schedule_once(lambda dt: self._show_error("Failed to load data"))
            return
        self.candles = parse_candles(raw)
        Clock.schedule_once(lambda dt: self._show_results())

    def _show_error(self, msg):
        self.status_label.text = msg
        self.price_label.text = "Price: --"
        self.signal_label.text = "Signal: --"

    def _show_results(self):
        self.results_grid.clear_widgets()
        if not self.candles:
            self.status_label.text = "No data"
            return

        price = self.candles[-1]["close"]
        self.price_label.text = f"Price: {price:.2f}"

        signal, value = generate_signal(self.candles, self.selected_indicator)
        sig_color = GREEN if signal == "BUY" else RED if signal == "SELL" else YELLOW
        self.signal_label.color = sig_color
        self.signal_label.text = f"Signal: {signal}"

        for ind in INDICATORS:
            sig, val = generate_signal(self.candles, ind)
            card = IndicatorCard(ind, sig, val if isinstance(val, float) else 0)
            self.results_grid.add_widget(card)

        if signal == "BUY":
            self.martingale_level = max(1, self.martingale_level - 1) if self.martingale_level > 1 else 1
        elif signal == "SELL":
            pass
        self.m_label.text = f"Martingale: {self.martingale_level}"

        self.chart.set_candles(self.candles)
        self.status_label.text = f"Updated: {datetime.datetime.now().strftime('%H:%M:%S')}"


if __name__ == "__main__":
    TradingApp().run()
