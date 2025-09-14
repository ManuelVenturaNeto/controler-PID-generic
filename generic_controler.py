import time

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

        self.modo = str(controler_definitions.get("modo", "manual"))
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



    def main(self) -> dict:


        for step in range(self.K):
            out = self.ctrl()
            print(f"{step:03d}: {out}")
            self.pass_time()

        return {"sp": self.sp, "vm": self.vm}



    def ctrl(self) -> dict:

        self._e2 = self._e1

        self._e1 = self._e0

        self._e0 = self._erro()

        self.a0 = self.kp * (1 + (self.T / self.Ti) + (self.Td / self.T))

        self.a1 = -self.kp * (1 + (2 * (self.Td) / self.T))

        self.a2 = (self.kp * self.Td) / self.T

        self._m = (self.a0 * self._e0) + (self.a1 * self._e1) + (self.a2 * self._e2) + self._m1

        self._m1 = self._m if self.sp < self.vm else -self._m

        self.vm = self._m

        return {
            "sp": self.sp,
            "vm": self.vm,
            "pv": self.pv,
            "modo": self.modo,
            "acao": self.acao,
            "a0": self.a0,
            "a1": self.a1,
            "a2": self.a2,
            "e0": self._e0,
            "e1": self._e1,
            "e2": self._e2,
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
        self._e0 = self.sp - self.pv

        if self.acao == "inversa":
            return -self._e0

        return self._e0



    def _infer_Ti(self) -> float:
        if self.ki > 0.0 and self.kp > 0.0:
            return self.kp / self.ki
        return 0.0



    def _infer_Td(self) -> float:
        if self.kp > 0.0 and self.kd > 0.0:
            return self.kd / self.kp
        return 0.0
