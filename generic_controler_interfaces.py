from abc import ABC, abstractmethod



class GenericControlerInterface(ABC):

    @abstractmethod
    def __incremental(self) -> None:
        """
        Também chamado de primeira ordem.
        Incremental é contrario ao posicional. o chat gpt chama de velocity.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __proporcional_integral(self) -> None:
        """
        Também chamado de segunda ordem.
        p é de primeira ordem e pi é de segunda ordem. e(k-2)
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __equivalente_ao_pid(self) -> None:
        """
        a0 referente a kp, a1 referente a ki e a2 referente a kd.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __manual_automatico(self) -> None:
        """
        Define se ele está rodando em manual ou automatico.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __bumpess(self) -> None:
        """
        Da divergencia da onda quando muda-se me manual para automatico ou automatico pra manual.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __tracking(self) -> None:
        """
        registrar o Sp que é o r(k) e o Vm que é o m(k).
        Imprimir recursivamente o Sp e o Vm.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __antireset(self) -> None:
        """
        Não calcula mais do que ele consegue calcular.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __hold_de_ordem_zero(self) -> None:
        """
        ele tem que gerar uma reta.
        porém a mais correta seria uma escadinha seguindo a rampa.
        não pode ser parabola, hiperbole ou qualquer outra curva como saida.
        """
        raise ValueError("Method not implemented")

    @abstractmethod
    def __acao_direta_ou_reversa(self) -> None:
        """
        quando a variavel de processo sobe a variavel manipulada também sobe.
        quando a variavel de processo desce a variavel manipulada desce.
        e(k) = v(k) - c(k)  --> reversa
        e(k) = c(k) - v(k)  --> direta
        """
        raise ValueError("Method not implemented")