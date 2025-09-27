import time
import matplotlib.pyplot as plt
from matplotlib.widgets import Button

import tkinter as tk
from tkinter import simpledialog
_HAS_TK = True



class GenericControler():
    """
    Controler class (PID incremental / forma de velocidade)
    """

    #   K = 0 a 100

    def __init__(self, controler_definitions: dict):

        self.kp = float(controler_definitions.get("kp", 0.0))
        self.ki = float(controler_definitions.get("ki", 0.0))
        self.kd = float(controler_definitions.get("kd", 0.0))
        self.sp = float(controler_definitions.get("sp", 0.0))
        self.ts = float(controler_definitions.get("ts", 1.0))

        self.pv = float(controler_definitions.get("pv", 0.0))
        self.K = int(controler_definitions.get("K", 100))

        self.mode = str(controler_definitions.get("modo", "manual"))
        self.acao = str(controler_definitions.get("acao", "direta"))

        self.T = self.ts
        self.Ti = self._infer_Ti()
        self.Td = self._infer_Td()

        self.a0 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0

        self._e0 = 0.0              # e(k)
        self._e1 = 0.0              # e(k-1)
        self._e2 = 0.0              # e(k-2)

        self._m0 = 0.0              # m(k)
        self._m1 = 0.0              # m(k-1)
        self.vm = 0.0               # saída atual (K)
        self._ticks = 0

        self.anti_reset_windap = int(controler_definitions.get("anti_reset_windap", 1000))

        # --- HISTÓRICO PARA O GRÁFICO ---
        self._hist_t = []
        self._hist_vm = []

        # --- UI (preparada depois) ---
        self._fig = None
        self._ax = None
        self._line = None
        self._btns = {}
        self._running = True


    def main(self) -> dict:
        # abre a UI
        self._setup_ui()

        for step in range(self.K):

            # controle
            out = self.ctrl()
            print(f"{step:03d}: {out}")

            if abs(self.vm) >= abs(self.anti_reset_windap):
                break

            # histórico para o gráfico
            self._hist_t.append(self._ticks)
            self._hist_vm.append(self.vm)
            self._update_plot()

            self.pass_time()

            # if not plt.fignum_exists(self._fig.number):
            #     self._running = False
            #     break

            plt.pause(0.001)

        return {"sp": self.sp, "vm": self.vm}



    def ctrl(self) -> dict:

        self._e2 = self._e1
        self._e1 = self._e0
        self._e0 = self._erro()

        # atualiza Ti/Td toda iteração (caso kp/ki/kd mudem pelos botões)
        self.Ti = self._infer_Ti()
        self.Td = self._infer_Td()

        self.a0 = self.kp * (1 + (self.T / (self.Ti if self.Ti > 0 else 1e9)) + (self.Td / self.T))
        self.a1 = -self.kp * (1 + (2 * (self.Td) / self.T))
        self.a2 = (self.kp * self.Td) / self.T

        if self.mode == "automatico":
            self._m0 = (self.a0 * self._e0) + (self.a1 * self._e1) + (self.a2 * self._e2) + self._m1

        self._m1 = self._m0
        self.vm = round(self._m0, 2)

        return {
            "sp": self.sp,
            "vm": self.vm,
            "pv": self.pv,
            "modo": self.mode,
            "acao": self.acao,
            "a0": self.a0,
            "a1": self.a1,
            "a2": self.a2,
            "e0": self._e0,
            "e1": self._e1,
            "e2": self._e2,
            "m": round(self._m0, 2),
            "m1": round(self._m1, 2)
        }



    def pass_time(self) -> int:
        """
        Aguarda Ts segundos e retorna o número de passos executados.
        """
        time.sleep(self.ts)
        self._ticks += 1
        return self._ticks



    def _erro(self) -> None:
        """
        Calcula o erro de acordo com a acao aplicada.
        """
        # OBS: teu código verificava "inversa", então o botão alterna para "inversa"
        if self.acao == "inversa":
            self._e0 = self.pv - self.sp
            return self._e0
        return self.sp - self.pv



    def _infer_Ti(self) -> float:
        if self.ki > 0.0 and self.kp > 0.0:
            return self.kp / self.ki
        return 0.0



    def _infer_Td(self) -> float:
        if self.kp > 0.0 and self.kd > 0.0:
            return self.kd / self.kp
        return 0.0

    # ================= UI =================

    def _setup_ui(self) -> None:
        plt.ion()
        self._fig, self._ax = plt.subplots(figsize=(9, 5))
        plt.subplots_adjust(left=0.08, right=0.98, top=0.85, bottom=0.22)

        (self._line,) = self._ax.plot(self._hist_t, self._hist_vm, lw=2)
        self._ax.set_xlabel("tempo (ticks)")
        self._ax.set_ylabel("vm")
        self._ax.grid(True, alpha=0.3)
        self._refresh_title()

        # --- BOTÕES ---
        # layout simples em 2 linhas de botões
        ax_modo  = self._fig.add_axes([0.08, 0.12, 0.12, 0.06])
        ax_acao  = self._fig.add_axes([0.22, 0.12, 0.12, 0.06])
        ax_mset  = self._fig.add_axes([0.36, 0.12, 0.14, 0.06])

        ax_kp_up   = self._fig.add_axes([0.56, 0.12, 0.04, 0.06])
        ax_kp_dn   = self._fig.add_axes([0.61, 0.12, 0.04, 0.06])
        ax_ki_up   = self._fig.add_axes([0.68, 0.12, 0.04, 0.06])
        ax_ki_dn   = self._fig.add_axes([0.73, 0.12, 0.04, 0.06])
        ax_kd_up   = self._fig.add_axes([0.80, 0.12, 0.04, 0.06])
        ax_kd_dn   = self._fig.add_axes([0.85, 0.12, 0.04, 0.06])

        self._btns["modo"] = Button(ax_modo, f"Modo: {self.mode}")
        self._btns["acao"] = Button(ax_acao, f"Ação: {self.acao}")
        self._btns["mset"] = Button(ax_mset, "Definir m(k)")

        self._btns["kp_up"] = Button(ax_kp_up, "kp ▲")
        self._btns["kp_dn"] = Button(ax_kp_dn, "kp ▼")
        self._btns["ki_up"] = Button(ax_ki_up, "ki ▲")
        self._btns["ki_dn"] = Button(ax_ki_dn, "ki ▼")
        self._btns["kd_up"] = Button(ax_kd_up, "kd ▲")
        self._btns["kd_dn"] = Button(ax_kd_dn, "kd ▼")

        # callbacks
        self._btns["modo"].on_clicked(self._on_toggle_modo)
        self._btns["acao"].on_clicked(self._on_toggle_acao)
        self._btns["mset"].on_clicked(self._on_set_manual_m)

        self._btns["kp_up"].on_clicked(lambda evt: self._bump_gain("kp", +0.2))
        self._btns["kp_dn"].on_clicked(lambda evt: self._bump_gain("kp", -0.2))
        self._btns["ki_up"].on_clicked(lambda evt: self._bump_gain("ki", +0.2))
        self._btns["ki_dn"].on_clicked(lambda evt: self._bump_gain("ki", -0.2))
        self._btns["kd_up"].on_clicked(lambda evt: self._bump_gain("kd", +0.2))
        self._btns["kd_dn"].on_clicked(lambda evt: self._bump_gain("kd", -0.2))

        self._fig.canvas.mpl_connect("close_event", self._on_close)
        plt.show(block=False)



    def _on_close(self, event=None):
        self._running = False



    def _refresh_title(self) -> None:
        self._fig.suptitle(
            f"PID • modo={self.mode} • ação={self.acao} • sp={self.sp:.2f} • "
            f"kp={self.kp:.3f} ki={self.ki:.3f} kd={self.kd:.3f} • vm={self.vm:.2f}",
            fontsize=12
        )



    def _update_plot(self) -> None:
        self._line.set_data(self._hist_t, self._hist_vm)
        # auto-ajusta eixos
        if self._hist_t:
            self._ax.set_xlim(max(0, self._hist_t[-1] - 60), self._hist_t[-1] + 1)  # janela móvel ~60 ticks
        if self._hist_vm:
            ymin = min(self._hist_vm[-60:]) if len(self._hist_vm) > 0 else 0
            ymax = max(self._hist_vm[-60:]) if len(self._hist_vm) > 0 else 1
            if ymin == ymax:
                ymax = ymin + 1
            self._ax.set_ylim(ymin - 0.05*(abs(ymin)+1), ymax + 0.05*(abs(ymax)+1))
        self._refresh_title()
        self._fig.canvas.draw_idle()


    # --------- Botões ---------


    def _on_toggle_modo(self, event=None):
        self.mode = "manual" if self.mode == "automatico" else "automatico"
        self._btns["modo"].label.set_text(f"Modo: {self.mode}")
        self._refresh_title()



    def _on_toggle_acao(self, event=None):
        # OBS: usando "inversa" para casar com teu _erro()
        self.acao = "inversa" if self.acao == "direta" else "direta"
        self._btns["acao"].label.set_text(f"Ação: {self.acao}")
        self._refresh_title()



    def _on_set_manual_m(self, event=None):
        if self.mode != "manual":
            # sem pop-up; apenas ignore (ou poderíamos trocar para manual)
            return
        val = None
        if _HAS_TK:
            try:
                root = tk.Tk()
                root.withdraw()
                val = simpledialog.askfloat("Valor manual", "Digite o valor para m(k):", minvalue=-1e9, maxvalue=1e9)
                root.destroy()
            except Exception:
                val = None
        if val is None:
            # fallback via console se não houver tkinter
            try:
                txt = input("Modo manual: digite o valor de m(k): ").strip()
                if txt:
                    val = float(txt)
            except Exception:
                val = None
        if val is not None:
            self._m0 = float(val)
            self._m1 = float(val)
            self.vm = round(self._m0, 2)
            self._refresh_title()



    def _bump_gain(self, which: str, delta: float):
        if which == "kp":
            self.kp = max(0.0, self.kp + delta)
        elif which == "ki":
            self.ki = max(0.0, self.ki + delta)
        elif which == "kd":
            self.kd = max(0.0, self.kd + delta)
        self._refresh_title()
