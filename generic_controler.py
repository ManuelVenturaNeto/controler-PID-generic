import time
import math
from collections import deque


class GenericControler():
    """
    Controler class (PID incremental / forma de velocidade) + modelo discreto (Z-transform).
    """

    def __init__(self, controler_definitions: dict):

        self.kp = float(controler_definitions.get("kp", 0.0))
        self.ki = float(controler_definitions.get("ki", 0.0))
        self.kd = float(controler_definitions.get("kd", 0.0))
        self.sp = float(controler_definitions.get("sp", 0.0))
        self.ts = float(controler_definitions.get("ts", 1.0))

        self.pv = float(controler_definitions.get("pv", 0.0))
        self.K = int(controler_definitions.get("K", 100))

        self.mode = str(controler_definitions.get("modo", "manual"))
        self.action = str(controler_definitions.get("acao", "direta"))

        self.action_dir = -1 if self.action == "direta" else 1

        self.T = self.ts
        self.Ti = self._infer_Ti()
        self.Td = self._infer_Td()

        self.a0 = 0.0
        self.a1 = 0.0
        self.a2 = 0.0

        self._e0 = 0.0              # e(k)
        self._e1 = 0.0              # e(k-1)
        self._e2 = 0.0              # e(k-2)

        self._c0 = 0.0              # c(k)
        self._c1 = 0.0              # c(k-1)
        self._c2 = 0.0              # c(k-2)

        self.k = float(controler_definitions.get("k", 0.0))   # ganho do processo
        self.j = float(controler_definitions.get("j", 0.0))   # constante de tempo (tau)
        self.tm = float(controler_definitions.get("tm", 0.0)) # tempo morto

        self._m0 = 0.0              # m(k)
        self._m1 = 0.0              # m(k-1)
        self.vm = 0.0               # saída atual (K)
        self._ticks = 0

        self.anti_reset_windap = int(controler_definitions.get("anti_reset_windap", 1000))

        # --- buffer para tempo morto discreto: eta = 1 + floor(tm/T) ---
        self._eta = 1
        self._m_delay_buf = deque([0.0], maxlen=self._eta)

        # Coefs últimos calculados (expostos via dict)
        self.a_n = 0.0
        self.b_1 = 0.0

        # Parâmetros de distúrbio
        self.disturbio_magnitude = float(controler_definitions.get("disturbio_magnitude", 0.0))
        self.disturbio_duracao = int(controler_definitions.get("disturbio_duracao", 0))
        self.disturbio_inicio = int(controler_definitions.get("disturbio_inicio", 0))
        self._disturbio_ativo = False
        self._disturbio_contador = 0

        # Estado interno do processo
        self._process_state = 0.0



    def _update_eta(self):
        # garante eta >= 1
        new_eta = 1
        if self.T >= 0.0 and self.tm >= 0.0:
            new_eta = 1 + int(self.tm / self.T)
        if new_eta < 1:
            new_eta = 1
        if new_eta != self._eta:
            self._eta = new_eta
            self._m_delay_buf = deque([0.0] * self._eta, maxlen=self._eta)



    def _aplicar_disturbio(self):
        """Aplica distúrbio ao sistema se estiver no período configurado"""
        if self.disturbio_duracao <= 0 or self.disturbio_magnitude == 0:
            return 0.0
        
        # Ativa o distúrbio se atingiu o início
        if not self._disturbio_ativo and self._ticks >= self.disturbio_inicio:
            self._disturbio_ativo = True
            self._disturbio_contador = 0
        
        # Aplica o distúrbio enquanto estiver ativo
        if self._disturbio_ativo:
            if self._disturbio_contador < self.disturbio_duracao:
                self._disturbio_contador += 1
                return self.disturbio_magnitude
            else:
                # Desativa o distúrbio após a duração
                self._disturbio_ativo = False
        
        return 0.0



    def ctrl(self) -> dict:
        """
        Executa 1 iteração de controle (PID incremental) e calcula C(k) via modelo discreto.
        """

        # --- PID incremental ---
        self._e2 = self._e1
        self._e1 = self._e0
        self._e0 = self._erro()

        self.Ti = self._infer_Ti()
        self.Td = self._infer_Td()

        self.a0 = self.kp * (1 + (self.T / self.Ti) + (self.Td / self.T)) if self.Ti > 0 or self.Td > 0 else self.kp
        self.a1 = -self.kp * (1 + (2 * (self.Td) / self.T)) if self.T > 0 else 0.0
        self.a2 = (self.kp * self.Td) / self.T if self.T > 0 else 0.0

        if self.mode == "automatico":
            delta = (self.a0 * self._e0) + (self.a1 * self._e1) + (self.a2 * self._e2)
            self.action_dir = -1 if self.action == "direta" else 1
            self._m0 = self._m1 + self.action_dir * delta

        lim = abs(self.anti_reset_windap)
        if self._m0 >  lim: self._m0 = float(lim)
        if self._m0 < -lim: self._m0 = -float(lim)

        # Aplica distúrbio na variável manipulada ANTES do cálculo do processo
        disturbio_atual = self._aplicar_disturbio()
        m0_com_disturbio = self._m0 + disturbio_atual

        self._m1 = self._m0
        self.vm = round(m0_com_disturbio, 2)  # Agora vm inclui o distúrbio

        # --- Z-transform / modelo discreto ---
        if self.k > 0.0 and self.j > 0.0 and self.T > 0.0:
            self.a_n = self.k * (1.0 - math.exp(-self.T / self.j))
            self.b_1 = math.exp(-self.T / self.j)

            # tempo morto discreto eta = 1 + floor(tm/T)
            self._update_eta()
            self._m_delay_buf.append(m0_com_disturbio)  # Usa m0 COM distúrbio
            m_delay = self._m_delay_buf[0]  # m(k-eta) COM distúrbio

            # Atualiza o estado do processo
            self._process_state = (self.a_n * m_delay) + (self.b_1 * self._process_state)
            ck = self._process_state
        else:
            # fallback simples quando modelo não parametrizado
            ck = m0_com_disturbio

        # Fechamento da malha - PV é a saída do processo
        self.pv = ck

        # Atualiza as variáveis de estado para o próximo ciclo
        self._c1 = self._c0
        self._c0 = ck

        # Incrementa ticks para controle de distúrbio
        self._ticks += 1

        return {
            "sp": self.sp,
            "vm": self.vm,
            "pv": self.pv,
            "modo": self.mode,
            "acao": self.action,
            "a0": self.a0,
            "a1": self.a1,
            "a2": self.a2,
            "e0": self._e0,
            "e1": self._e1,
            "e2": self._e2,
            "m": round(self._m0, 3),
            "m1": round(self._m1, 3),
            "ck": round(ck, 3),
            "a_n": round(self.a_n, 3),
            "b_1": round(self.b_1, 3),
            "disturbio_ativo": self._disturbio_ativo,
            "disturbio_valor": disturbio_atual,
        }



    def pass_time(self) -> int:
        time.sleep(self.ts)
        self._ticks += 1
        return self._ticks



    def _erro(self) -> float:
        return self.sp - self.pv



    def _infer_Ti(self) -> float:
        if self.ki > 0.0 and self.kp > 0.0:
            return self.kp / self.ki
        return 0.0



    def _infer_Td(self) -> float:
        if self.kp > 0.0 and self.kd > 0.0:
            return self.kd / self.kp
        return 0.0
