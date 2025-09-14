from generic_controler import GenericControler


if __name__ == "__main__":
    controler_definitions = {
        "kp": 2.0,
        "ki": 0.5,
        "kd": 0.1,
        "K": 100,                    # limite superior (0..100)
        "modo": "automatico",       # "automatico" | "manual"
        "acao": "direta",           # "direta" | "reversa"
        "sp": 50.0,                 # setpoint
        "ts": 1,                    # período de amostragem (s)
        "pv": 0
    }

    GenericControler(controler_definitions).main()
