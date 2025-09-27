from generic_controler import GenericControler


if __name__ == "__main__":
    controler_definitions = {
        "kp": 0.5,
        "ki": 0.5,
        "kd": 0.1,
        "K": 1500,                    # limite superior (0..100)
        "modo": "automatico",       # "automatico" | "manual"
        "acao": "direta",           # "direta" | "reversa"
        "sp": 50.0,                 # setpoint
        "ts": 1,                    # período de amostragem (s)
        "pv": 0,
        "anti_reset_windap": 15000
    }

    GenericControler(controler_definitions).main()
