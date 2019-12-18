class Opts:
    def __init__(self,
                 nug: bool = False,
                 iga: bool = False,
                 fct: bool = False,
                 n_iters: int = 2,
                 eps: float = 1e-8
                 ):
        self._nug = nug
        self._n_iters = n_iters
        self._iga = iga
        self._fct = fct
        self._eps = eps

    @property
    def nug(self) -> bool:
        return self._nug

    @property
    def n_iters(self) -> int:
        return self._n_iters

    @property
    def iga(self) -> bool:
        return self._iga

    @property
    def fct(self) -> bool:
        return self._fct


    @property
    def eps(self) -> float:
        return self._eps

