
import tkinter as tk
from tkinter import ttk, messagebox
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from generic_controler import GenericControler

DEFAULTS = {
    "kp": 0.5,
    "ki": 0.5,
    "kd": 0.1,
    "K": 100,                    # limite superior (0..100)
    "modo": "automatico",         # "automatico" | "manual"
    "acao": "direta",             # "direta" | "reversa" (UI); mapeado para "inversa" no controlador
    "sp": 50.0,                   # setpoint
    "ts": 1,                      # período de amostragem (s)
    "pv": 0,
    "anti_reset_windap": 1000
}



def ui2ctrl_action(v: str) -> str:
    return "inversa" if v == "reversa" else "direta"



class PIDUI(tk.Tk):
    def __init__(self, defaults=None):
        super().__init__()
        self.title("GenericControler - UI Responsiva")
        self.geometry("1100x700")
        self.minsize(960, 620)

        self.defaults = dict(DEFAULTS if defaults is None else defaults)
        self.running = False
        self.started = False
        self.step_idx = 0
        self.history = []  # lista de dicts por iteração
        self._last_modo = self.defaults.get("modo", "automatico")
        self._changing_mode = False            # evita reentrância do trace
        self._was_running_before_manual = False

        # controlador
        ctrl_defs = dict(self.defaults)
        ctrl_defs["acao"] = ui2ctrl_action(ctrl_defs.get("acao", "direta"))
        self.ctrl = GenericControler(ctrl_defs)

        # ---- Layout base ----
        self.columnconfigure(0, weight=1)   # esquerda (painel + gráfico)
        self.rowconfigure(1, weight=1)      # gráfico cresce

        self._build_top_controls()
        self._build_plot()
        self._build_table()
        self._wire_resize()



    # ---------- UI building ----------
    def _build_top_controls(self):
        frm = ttk.Frame(self, padding=(8, 8, 8, 4))
        frm.grid(row=0, column=0, sticky="ew")
        frm.columnconfigure(0, weight=1)
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(2, weight=1)
        frm.columnconfigure(3, weight=1)
        frm.columnconfigure(4, weight=1)

        # Vars
        self.var_kp = tk.DoubleVar(value=self.defaults["kp"])
        self.var_ki = tk.DoubleVar(value=self.defaults["ki"])
        self.var_kd = tk.DoubleVar(value=self.defaults["kd"])
        self.var_K  = tk.IntVar(value=self.defaults["K"])
        self.var_sp = tk.DoubleVar(value=self.defaults["sp"])
        self.var_ts = tk.DoubleVar(value=self.defaults["ts"])
        self.var_pv = tk.DoubleVar(value=self.defaults["pv"])
        self.var_anti = tk.IntVar(value=self.defaults["anti_reset_windap"])
        self.var_modo = tk.StringVar(value=self.defaults["modo"])
        self.var_acao = tk.StringVar(value=self.defaults["acao"])  # "direta" | "reversa"

        def spin(frame, label, var, inc, fmt="{:.2f}", is_int=False):
            sub = ttk.Frame(frame)
            ttk.Label(sub, text=label).grid(row=0, column=0, padx=(0,4))
            ent = ttk.Entry(sub, width=8, textvariable=var, justify="right")
            ent.grid(row=0, column=1)
            def add(v=inc):
                try:
                    if is_int:
                        var.set(int(var.get()) + int(v))
                    else:
                        var.set(round(float(var.get()) + float(v), 6))
                except tk.TclError:
                    pass
            def subf(v=inc):
                try:
                    if is_int:
                        var.set(int(var.get()) - int(v))
                    else:
                        var.set(round(float(var.get()) - float(v), 6))
                except tk.TclError:
                    pass
            ttk.Button(sub, text="–", width=2, command=subf).grid(row=0, column=2, padx=2)
            ttk.Button(sub, text="+", width=2, command=add).grid(row=0, column=3, padx=(2,8))
            return sub

        # Linha 1
        row1 = ttk.Frame(frm)
        row1.grid(row=0, column=0, columnspan=5, sticky="ew")
        spin(row1, "kp", self.var_kp, 0.1).grid(row=0, column=0, padx=4, pady=2)
        spin(row1, "ki", self.var_ki, 0.1).grid(row=0, column=1, padx=4, pady=2)
        spin(row1, "kd", self.var_kd, 0.1).grid(row=0, column=2, padx=4, pady=2)
        spin(row1, "K",  self.var_K, 10, is_int=True).grid(row=0, column=3, padx=4, pady=2)
        spin(row1, "sp", self.var_sp, 10).grid(row=0, column=4, padx=4, pady=2)

        # Linha 2
        row2 = ttk.Frame(frm)
        row2.grid(row=1, column=0, columnspan=5, sticky="ew")
        spin(row2, "ts (s)", self.var_ts, 0.1).grid(row=0, column=0, padx=4, pady=2)
        spin(row2, "pv", self.var_pv, 1).grid(row=0, column=1, padx=4, pady=2)
        spin(row2, "anti_reset_windap", self.var_anti, 100, is_int=True).grid(row=0, column=2, padx=4, pady=2)

        # Selects
        ttk.Label(row2, text="modo").grid(row=0, column=3, padx=(8,2))
        self.cmb_modo = ttk.Combobox(
            row2, textvariable=self.var_modo,
            values=["automatico", "manual"], width=12, state="readonly"
        )
        self.cmb_modo.grid(row=0, column=4, padx=(0,8))
        # dispara pop-up ao mudar para manual
        self.var_modo.trace_add("write", self._on_modo_change)

        ttk.Label(row2, text="acao").grid(row=0, column=5, padx=(8,2))
        ttk.Combobox(row2, textvariable=self.var_acao, values=["direta", "reversa"],
                    width=12, state="readonly").grid(row=0, column=6, padx=(0,8))

        # Start/Stop/Reset
        row3 = ttk.Frame(frm)
        row3.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(6,0))
        ttk.Button(row3, text="Iniciar", command=self.start).grid(row=0, column=0, padx=4)
        self.btn_pause = ttk.Button(row3, text="Pausar", command=self.toggle_pause)
        self.btn_pause.grid(row=0, column=1, padx=4)
        ttk.Button(row3, text="Reset", command=self.reset).grid(row=0, column=2, padx=4)



    def _on_modo_change(self, *args):
        # evita reentrância quando trocamos o modo programaticamente
        if self._changing_mode:
            return

        new_mode = self.var_modo.get()

        # só reage quando realmente mudou
        if new_mode != self._last_modo and new_mode == "manual":
            # pausa o loop e lembra se estava rodando
            self._was_running_before_manual = self.running
            if self.running:
                self.running = False
                try:
                    self.btn_pause.config(text="Retomar")
                except Exception:
                    pass
            # abre o pop-up
            self._prompt_manual_m()

        self._last_modo = new_mode



    def _prompt_manual_m(self):
        # valor sugerido: vm atual
        try:
            suggested = float(self.ctrl.vm)
        except Exception:
            suggested = 0.0

        lim = abs(self.ctrl.anti_reset_windap) or 1.0  # evita 0

        win = tk.Toplevel(self)
        win.title("Valor manual de m")
        win.transient(self)
        win.grab_set()

        ttk.Label(win, text=f"Defina m (limitado a ±{lim:.2f})").grid(row=0, column=0, columnspan=3, pady=(10,6), padx=10)

        var_val = tk.DoubleVar(value=round(suggested, 2))
        ent = ttk.Entry(win, textvariable=var_val, width=12, justify="right")
        ent.grid(row=1, column=0, padx=(10,6), pady=4)
        ent.focus_set()

        def bump(v):
            try:
                var_val.set(round(float(var_val.get()) + v, 6))
            except Exception:
                pass

        ttk.Button(win, text="−10", width=6, command=lambda: bump(-10)).grid(row=1, column=1, padx=4, pady=4)
        ttk.Button(win, text="+10", width=6, command=lambda: bump(+10)).grid(row=1, column=2, padx=(4,10), pady=4)

        def apply_and_close():
            # lê valor e faz clamp
            try:
                val = float(var_val.get())
            except Exception:
                val = suggested
            if val >  lim: val =  lim
            if val < -lim: val = -lim

            # aplica no controlador mantendo continuidade
            self.ctrl._m0 = float(val)
            self.ctrl._m1 = float(val)
            self.ctrl.vm  = round(float(val), 2)

            # atualiza o gráfico imediatamente (opcional)
            self.ax.relim(); self.ax.autoscale_view()
            self.canvas.draw_idle()

            # volta para AUTOMÁTICO e, se estava rodando antes do manual, tenta retomar
            self._changing_mode = True
            try:
                self.var_modo.set("automatico")
            finally:
                self._changing_mode = False
            self._last_modo = "automatico"

            # respeita o limite K antes de retomar
            if self._was_running_before_manual:
                try:
                    K_limit = int(self.var_K.get())
                except Exception:
                    K_limit = self.ctrl.K
                if self.step_idx < K_limit:
                    # retoma
                    self.running = True
                    self.started = True
                    try:
                        self.btn_pause.config(text="Pausar")
                    except Exception:
                        pass
                    self._tick()
                else:
                    # bateu K: não retoma
                    try:
                        self.btn_pause.config(text="Aumente K p/ retomar")
                    except Exception:
                        pass

            win.destroy()

        def cancel_and_close():
            # se cancelar, apenas mantém pausado em manual
            win.destroy()

        btns = ttk.Frame(win)
        btns.grid(row=2, column=0, columnspan=3, pady=(8,10))
        ttk.Button(btns, text="OK", width=10, command=apply_and_close).grid(row=0, column=0, padx=6)
        ttk.Button(btns, text="Cancelar", width=10, command=cancel_and_close).grid(row=0, column=1, padx=6)

        win.bind("<Return>", lambda e: apply_and_close())
        win.bind("<Escape>", lambda e: cancel_and_close())



    def _build_plot(self):
        self.fig = Figure(figsize=(5,3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("Saída (vm) em tempo real")
        self.ax.set_xlabel("Passo")
        self.ax.set_ylabel("vm")
        self.line, = self.ax.plot([], [])
        self.ax.grid(True)

        self.ax.set_autoscale_on(True)
        self.ax.autoscale(enable=True, axis='y')
        self.ax.relim()
        self.ax.autoscale_view()

        self.canvas = FigureCanvasTkAgg(self.fig, master=self)
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        # dados do gráfico
        self.xdata = []
        self.ydata = []



    def _build_table(self):
        # Tabela de histórico
        frm = ttk.Frame(self, padding=8)
        frm.grid(row=2, column=0, sticky="nsew")
        self.rowconfigure(2, weight=1)
        frm.rowconfigure(0, weight=1)
        frm.columnconfigure(0, weight=1)

        cols = [
            "step",
            "kp",
            "ki",
            "kd",
            "K",
            "modo",
            "acao",
            "sp",
            "ts",
            "pv",
            "anti_reset_windap",
            "vm",
            "m",
            "e0",
            "e1",
            "e2"
                ]

        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=8)

        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")

        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")

    def _wire_resize(self):
        self.grid_rowconfigure(1, weight=3)
        self.grid_rowconfigure(2, weight=2)
        self.grid_columnconfigure(0, weight=1)

    # ---------- Control flow ----------
    def start(self):
        if self.running:
            return
        try:
            K_limit = int(self.var_K.get())
        except Exception:
            K_limit = self.ctrl.K
        if self.step_idx >= K_limit:
            try:
                self.btn_pause.config(text="Aumente K p/ iniciar")
            except Exception:
                pass
            return

        self.started = True  # << novo
        self.running = True
        try:
            self.btn_pause.config(text="Pausar")
        except Exception:
            pass
        self._tick()



    def toggle_pause(self):
        # Se tentar retomar sem nunca ter iniciado, ignore
        if not self.running and not self.started:
            try:
                self.btn_pause.config(text="Use Iniciar")
            except Exception:
                pass
            return

        # Bloqueia retomar se já atingiu K
        if not self.running:
            try:
                K_limit = int(self.var_K.get())
            except Exception:
                K_limit = self.ctrl.K
            if self.step_idx >= K_limit:
                try:
                    self.btn_pause.config(text="Aumente K p/ retomar")
                except Exception:
                    pass
                return

        # Alterna pausa/retomar
        if self.running:
            self.running = False
            try:
                self.btn_pause.config(text="Retomar")
            except Exception:
                pass
        else:
            self.running = True
            try:
                self.btn_pause.config(text="Pausar")
            except Exception:
                pass
            self._tick()



    def stop(self):
        self.toggle_pause()



    def reset(self):
        if self.running:
            self.stop()
        self.started = False
        self.reached_K = False
        self.step_idx = 0
        self.history.clear()
        self.xdata.clear()
        self.ydata.clear()
        self.line.set_data([], [])
        self.ax.relim(); self.ax.autoscale_view()
        self.canvas.draw_idle()

        defs = self._current_defs()
        defs["acao"] = ui2ctrl_action(defs.get("acao", "direta"))
        self.ctrl = GenericControler(defs)

        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.btn_pause.config(text="Pausar")
        except Exception:
            pass



    def _current_defs(self):
        # captura valores atuais da UI em um dict
        return {
            "kp": float(self.var_kp.get()),
            "ki": float(self.var_ki.get()),
            "kd": float(self.var_kd.get()),
            "K": int(self.var_K.get()),
            "modo": self.var_modo.get(),
            "acao": self.var_acao.get(),
            "sp": float(self.var_sp.get()),
            "ts": float(self.var_ts.get()),
            "pv": float(self.var_pv.get()),
            "anti_reset_windap": int(self.var_anti.get()),
        }



    def _apply_defs_to_ctrl(self):
        # aplica valores da UI no controlador existente (sem recriar)
        d = self._current_defs()
        self.ctrl.kp = d["kp"]
        self.ctrl.ki = d["ki"]
        self.ctrl.kd = d["kd"]
        self.ctrl.K  = d["K"]
        self.ctrl.mode = d["modo"]
        self.ctrl.action = ui2ctrl_action(d["acao"])
        self.ctrl.sp = d["sp"]
        self.ctrl.ts = d["ts"]
        self.ctrl.pv = d["pv"]
        self.ctrl.anti_reset_windap = d["anti_reset_windap"]
        # T também pode ser igual a ts
        self.ctrl.T = self.ctrl.ts



    def _tick(self):
        if not self.running:
            return

        self._apply_defs_to_ctrl()

        out = self.ctrl.ctrl()
        self.step_idx += 1

        # Se atingir K, pausa e trava até aumentar K
        try:
            K_limit = int(self.var_K.get())
        except Exception:
            K_limit = self.ctrl.K
        if self.step_idx >= K_limit:
            self.running = False
            self.reached_K = True
            try:
                self.btn_pause.config(text="Aumente K p/ retomar")
            except Exception:
                pass

        # Atualiza gráfico
        self.xdata.append(self.step_idx)
        self.ydata.append(self.ctrl.vm)
        self.line.set_data(self.xdata, self.ydata)
        self.ax.relim(); self.ax.autoscale_view()
        self.canvas.draw_idle()

        # Atualiza tabela
        row = {
            "step": self.step_idx,
            "kp": self.ctrl.kp, "ki": self.ctrl.ki, "kd": self.ctrl.kd,
            "K": self.ctrl.K, "modo": self.ctrl.mode,
            "acao": "reversa" if self.ctrl.action == "inversa" else "direta",
            "sp": self.ctrl.sp, "ts": self.ctrl.ts, "pv": self.ctrl.pv,
            "anti_reset_windap": self.ctrl.anti_reset_windap,
            "vm": self.ctrl.vm, "m": out["m"],
            "e0": out["e0"], "e1": out["e1"], "e2": out["e2"]
        }
        self.history.append(row)
        values = [row[c] for c in ["step","kp","ki","kd","K","modo","acao","sp","ts","pv","anti_reset_windap","vm","m","e0","e1","e2"]]
        self.tree.insert("", "end", values=values)

        # Só agenda próximo passo se ainda puder rodar
        delay_ms = max(1, int(self.ctrl.ts * 1000))
        if self.running:
            self.after(delay_ms, self._tick)


if __name__ == "__main__":
    app = PIDUI()
    app.mainloop()
