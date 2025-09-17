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


    def main(self) -> dict:


        for step in range(self.K):

            change_mode = input("Digite 'm' p/ manual, 'a' p/ automatico ou ENTER p/ manter: ").lower()
            if change_mode == "m":
                self.mode = "manual"

            elif change_mode == "a":
                self.mode = "automatico"

            if self.mode == "automatico":
                out = self.ctrl()

            elif self.mode == "manual":
                manual_value = input(f"Step {step:03d} (manual) - digite valor para m(k): ").strip()

                if manual_value.isdigit():
                    self._m0 = float(manual_value)
                    self._m1 = float(manual_value)

                    out = self.ctrl()
            
            else:
                print(f"modo: {self.mode} - invalido")    

            print(f"{step:03d}: {out}")

            if self.vm > self.anti_reset_windap:
                break

            self.pass_time()

        return {"sp": self.sp, "vm": self.vm}



    def ctrl(self) -> dict:

        self._e2 = self._e1

        self._e1 = self._e0

        self._e0 = self._erro()

        self.a0 = self.kp * (1 + (self.T / self.Ti) + (self.Td / self.T))

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
        if self.acao == "inversa":
            self._e0 = self.pv - self.sp

        return self.sp - self.pv



    def _infer_Ti(self) -> float:
        if self.ki > 0.0 and self.kp > 0.0:
            return self.kp / self.ki
        return 0.0



    def _infer_Td(self) -> float:
        if self.kp > 0.0 and self.kd > 0.0:
            return self.kd / self.kp
        return 0.0
