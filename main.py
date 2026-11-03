# -*- coding: utf-8 -*-
"""MEXC mobile market scanner - Kivy port (paper trading only)."""
import os
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from scanner import scan_market, get_price
from storage import init_db, get_setting, save_setting, save_trade, get_trades


BG = (0.055, 0.075, 0.10, 1)
PANEL = (0.09, 0.12, 0.16, 1)
ACCENT = (0.0, 0.72, 0.78, 1)
WHITE = (0.92, 0.95, 0.98, 1)


class MEXCMobileApp(App):
    def build(self):
        self.title = "MEXC Market Scanner"
        init_db(self.user_data_dir)
        self.scanning = False
        self.stop_event = threading.Event()
        self.scan_thread = None
        self.active = None
        self.log_lines = []
        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        root.canvas.before.clear()
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG)
            self.bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._update_bg, size=self._update_bg)

        title = Label(text="[b]MEXC PRO — MOBILE SCANNER[/b]", markup=True, size_hint_y=None,
                      height=dp(42), color=ACCENT, font_size="19sp")
        root.add_widget(title)
        subtitle = Label(text="ماسح السوق ووضع المحاكاة الورقي Paper فقط", size_hint_y=None,
                         height=dp(26), color=WHITE, font_size="13sp")
        root.add_widget(subtitle)

        scroll = ScrollView(do_scroll_x=False)
        body = BoxLayout(orientation="vertical", spacing=dp(9), size_hint_y=None, padding=dp(4))
        body.bind(minimum_height=body.setter("height"))
        scroll.add_widget(body)
        root.add_widget(scroll)

        body.add_widget(self.section_title("إعدادات الفحص والمحاكاة"))
        self.amount = self.field(body, "مبلغ المحاكاة بالدولار", "15")
        self.tp = self.field(body, "هدف الربح TP %", "2.2")
        self.sl = self.field(body, "وقف الخسارة SL %", "0.8")
        self.vol = self.field(body, "معامل حجم التداول x", "1.2")
        self.max_change = self.field(body, "أقصى تغير سعري %", "0.60")
        self.rsi_min = self.field(body, "RSI الأدنى", "45")
        self.rsi_max = self.field(body, "RSI الأعلى", "70")
        self.chk_rsi = self.toggle(body, "تفعيل فلتر RSI", True)
        self.chk_macd = self.toggle(body, "تفعيل فلتر MACD", True)
        self.chk_book = self.toggle(body, "تفعيل فلتر دفتر الأوامر", True)
        self.chk_change = self.toggle(body, "تفعيل فلتر التغير السعري", True)

        controls = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self.start_btn = self.make_button("بدء الفحص", ACCENT, self.start_scan)
        self.stop_btn = self.make_button("إيقاف", (0.65, 0.22, 0.20, 1), self.stop_scan)
        self.stop_btn.disabled = True
        controls.add_widget(self.start_btn)
        controls.add_widget(self.stop_btn)
        body.add_widget(controls)

        body.add_widget(self.section_title("الصفقة التجريبية"))
        self.position_label = Label(text="لا توجد صفقة تجريبية مفتوحة", color=WHITE,
                                    size_hint_y=None, height=dp(56), halign="left", valign="middle")
        self.position_label.bind(size=lambda w, s: setattr(w, "text_size", s))
        body.add_widget(self.position_label)
        self.close_btn = self.make_button("إغلاق الصفقة التجريبية", (0.85, 0.55, 0.15, 1), self.close_paper)
        self.close_btn.disabled = True
        body.add_widget(self.close_btn)

        body.add_widget(self.section_title("السجل"))
        self.log_label = Label(text="جاهز. اضغط بدء الفحص.", color=WHITE, size_hint_y=None,
                               height=dp(230), halign="left", valign="top", font_size="12sp")
        self.log_label.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
        body.add_widget(self.log_label)
        history_btn = self.make_button("عرض آخر الصفقات التجريبية", PANEL, self.show_history)
        body.add_widget(history_btn)

        footer = Label(text="إعداد المشروع: MEXC Kivy Port | لا ينفذ أوامر مالية حقيقية",
                       size_hint_y=None, height=dp(28), color=(0.65, 0.72, 0.78, 1), font_size="10sp")
        root.add_widget(footer)
        self._load_settings()
        Clock.schedule_interval(self.update_position, 3)
        return root

    def _update_bg(self, widget, *_):
        self.bg_rect.pos = widget.pos
        self.bg_rect.size = widget.size

    def section_title(self, text):
        return Label(text=f"[b]{text}[/b]", markup=True, color=ACCENT,
                     size_hint_y=None, height=dp(30), halign="right")

    def field(self, parent, label, default):
        row = BoxLayout(size_hint_y=None, height=dp(43), spacing=dp(8))
        row.add_widget(Label(text=label, color=WHITE, size_hint_x=0.58, halign="right"))
        inp = TextInput(text=default, multiline=False, input_filter="float", size_hint_x=0.42,
                        background_color=PANEL, foreground_color=WHITE, cursor_color=ACCENT,
                        padding=(dp(8), dp(8)))
        row.add_widget(inp)
        parent.add_widget(row)
        return inp

    def toggle(self, parent, label, default):
        row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(8))
        cb = CheckBox(active=default, size_hint_x=None, width=dp(42), color=ACCENT)
        row.add_widget(cb)
        row.add_widget(Label(text=label, color=WHITE, halign="right"))
        parent.add_widget(row)
        return cb

    def make_button(self, text, color, callback):
        btn = Button(text=text, background_normal="", background_color=color,
                     color=(1, 1, 1, 1), size_hint_y=None, height=dp(46))
        btn.bind(on_release=callback)
        return btn

    def _load_settings(self):
        for key, widget, default in [
            ("amount", self.amount, "15"), ("tp", self.tp, "2.2"),
            ("sl", self.sl, "0.8"), ("vol", self.vol, "1.2"),
            ("max_change", self.max_change, "0.60"),
            ("rsi_min", self.rsi_min, "45"), ("rsi_max", self.rsi_max, "70")]:
            widget.text = get_setting(self.user_data_dir, key, default)
        for key, widget in [("rsi", self.chk_rsi), ("macd", self.chk_macd),
                            ("book", self.chk_book), ("change", self.chk_change)]:
            widget.active = get_setting(self.user_data_dir, "enable_" + key, "1") == "1"

    def _cfg(self):
        def f(widget, default):
            try: return float(widget.text)
            except (ValueError, TypeError): return default
        cfg = {"vol_multiplier": f(self.vol, 1.2), "max_price_change_pct": f(self.max_change, .60),
               "enable_low_price_change_filter": self.chk_change.active,
               "enable_order_book_filter": self.chk_book.active,
               "enable_rsi_filter": self.chk_rsi.active, "rsi_min": f(self.rsi_min, 45),
               "rsi_max": f(self.rsi_max, 70), "enable_macd_filter": self.chk_macd.active}
        for key, widget in [("amount", self.amount), ("tp", self.tp), ("sl", self.sl),
                            ("vol", self.vol), ("max_change", self.max_change),
                            ("rsi_min", self.rsi_min), ("rsi_max", self.rsi_max)]:
            save_setting(self.user_data_dir, key, widget.text)
        for key, widget in [("rsi", self.chk_rsi), ("macd", self.chk_macd),
                            ("book", self.chk_book), ("change", self.chk_change)]:
            save_setting(self.user_data_dir, "enable_" + key, "1" if widget.active else "0")
        return cfg

    def log(self, message):
        self.log_lines.append(f"{datetime.now().strftime('%H:%M:%S')}  {message}")
        self.log_lines = self.log_lines[-35:]
        self.log_label.text = "\n".join(self.log_lines)

    def start_scan(self, *_):
        if self.scanning: return
        if self.active:
            self.popup("هناك صفقة محاكاة مفتوحة", "أغلق الصفقة الحالية قبل بدء بحث جديد.")
            return
        cfg = self._cfg()
        self.scanning = True
        self.stop_event.clear()
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self.log("بدأ فحص أزواج Spot العامة من MEXC...")
        self.scan_thread = threading.Thread(target=self._scan_worker, args=(cfg,), daemon=True)
        self.scan_thread.start()

    def _scan_worker(self, cfg):
        try:
            result = scan_market(cfg, self._thread_log, self.stop_event.is_set)
            if result:
                Clock.schedule_once(lambda dt: self.on_signal(result), 0)
            else:
                Clock.schedule_once(lambda dt: self._scan_finished("لم يتم العثور على إشارة مطابقة."), 0)
        except Exception as exc:
            message = str(exc)
            Clock.schedule_once(lambda dt: self._scan_finished(f"خطأ أثناء الفحص: {message}"), 0)

    def _thread_log(self, message):
        Clock.schedule_once(lambda dt: self.log(message), 0)

    def _scan_finished(self, message):
        self.scanning = False
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.log(message)

    def stop_scan(self, *_):
        # Requests are bounded by network timeouts; the worker exits after the current symbol.
        self.scanning = False
        self.stop_event.set()
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.log("تم طلب إيقاف الفحص؛ سينتهي بعد الطلب الحالي.")

    def on_signal(self, result):
        self.scanning = False
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        symbol, price, reason = result
        try: amount = max(1.0, float(self.amount.text))
        except ValueError: amount = 15.0
        try: tp = max(.1, float(self.tp.text))
        except ValueError: tp = 2.2
        try: sl = max(.1, float(self.sl.text))
        except ValueError: sl = .8
        self.active = {"symbol": symbol, "entry": price, "amount": amount, "tp": tp, "sl": sl}
        self.position_label.text = f"{symbol}\nدخول محاكى: {price:.8g} USDT | المبلغ: ${amount:.2f}\nTP: {tp}% | SL: {sl}%"
        self.close_btn.disabled = False
        self.log(f"إشارة {symbol} عند {price:.8g} — تم فتح مركز محاكاة فقط. {reason}")

    def update_position(self, _dt):
        if not self.active: return
        pos = self.active
        price = get_price(pos["symbol"])
        if not price: return
        pct = (price - pos["entry"]) / pos["entry"] * 100
        pnl = pos["amount"] * pct / 100
        self.position_label.text = (f"{pos['symbol']} | السعر: {price:.8g} USDT\n"
            f"الدخول: {pos['entry']:.8g} | الربح/الخسارة: {pnl:+.3f}$ ({pct:+.2f}%)\n"
            f"الهدف: +{pos['tp']}% | الوقف: -{pos['sl']}%")
        if pct >= pos["tp"]: self._finish_paper(price, "TP")
        elif pct <= -pos["sl"]: self._finish_paper(price, "SL")

    def close_paper(self, *_):
        if self.active:
            price = get_price(self.active["symbol"]) or self.active["entry"]
            self._finish_paper(price, "MANUAL")

    def _finish_paper(self, exit_price, reason):
        pos = self.active
        if not pos: return
        pct = (exit_price - pos["entry"]) / pos["entry"] * 100
        pnl = pos["amount"] * pct / 100
        save_trade(self.user_data_dir, pos["symbol"], pos["entry"], exit_price,
                   pos["amount"], pnl, pct, reason)
        self.log(f"إغلاق محاكاة {pos['symbol']} ({reason}) — النتيجة: {pnl:+.3f}$ ({pct:+.2f}%).")
        self.active = None
        self.position_label.text = "لا توجد صفقة تجريبية مفتوحة"
        self.close_btn.disabled = True

    def show_history(self, *_):
        rows = get_trades(self.user_data_dir)
        body = "\n".join([f"{r[0]} | {r[1]:.6g} → {r[2]:.6g} | {r[4]:+.3f}$ ({r[5]:+.2f}%) | {r[6]}" for r in rows])
        if not body: body = "لا يوجد سجل حتى الآن."
        label = Label(text=body, color=WHITE, halign="left", valign="top")
        label.bind(size=lambda w, s: setattr(w, "text_size", s))
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        scroll = ScrollView(); scroll.add_widget(label); content.add_widget(scroll)
        close = self.make_button("إغلاق", ACCENT, lambda *_: popup.dismiss())
        content.add_widget(close)
        popup = Popup(title="سجل المحاكاة", content=content, size_hint=(.94, .78))
        popup.open()

    def popup(self, title, message):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        box.add_widget(Label(text=message, color=WHITE))
        popup = Popup(title=title, content=box, size_hint=(.85, .35))
        btn = self.make_button("حسنًا", ACCENT, lambda *_: popup.dismiss())
        box.add_widget(btn); popup.open()


if __name__ == "__main__":
    MEXCMobileApp().run()
