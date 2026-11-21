"""Estimador con pérdida absoluta que scikit-learn no ofrece: perceptrón multicapa con pérdida L1."""
import numpy as np


class MLPL1:
    """Perceptrón multicapa (ReLU) para regresión con pérdida absoluta media, Adam, penalización L2 y parada temprana
    sobre un 10 % aleatorio de las filas de ajuste (igual que early_stopping de scikit-learn)."""

    def __init__(self, capas=(64,), alpha=1e-4, lr=1e-3, lote=512, epocas=80, paciencia=8, semilla=0):
        self.capas, self.alpha, self.lr, self.lote, self.epocas, self.paciencia, self.semilla = capas, alpha, lr, lote, epocas, paciencia, semilla

    def _adelante(self, X, W):
        H = [X]
        for k, (w, b) in enumerate(W):
            Z = H[-1] @ w + b
            H.append(np.maximum(Z, 0) if k < len(W) - 1 else Z)
        return H

    def perdida(self, X, y, W):
        """Error absoluto medio + (alpha/2) * suma de pesos al cuadrado (sin sesgos)."""
        return float(np.mean(np.abs(self._adelante(X, W)[-1][:, 0] - y)) + self.alpha / 2 * sum(np.sum(w ** 2) for w, _ in W))

    def gradientes(self, X, y, W):
        """Gradiente de perdida() por retropropagación; lo usa fit() y se verifica con diferencias finitas."""
        H = self._adelante(X, W); g = np.sign(H[-1][:, 0] - y)[:, None] / len(y); G = [None] * len(W)
        for k in range(len(W) - 1, -1, -1):
            w, b = W[k]; G[k] = (H[k].T @ g + self.alpha * w, g.sum(0))
            if k > 0: g = (g @ w.T) * (H[k] > 0)
        return G

    def fit(self, X, y):
        rng = np.random.default_rng(self.semilla); X = X.astype(np.float32); y = y.astype(np.float32)
        n = len(y); nv = max(int(.1 * n), 1); p = rng.permutation(n); Xt, yt, Xv, yv = X[p[nv:]], y[p[nv:]], X[p[:nv]], y[p[:nv]]
        dims = [X.shape[1], *self.capas, 1]
        W = [(rng.normal(0, np.sqrt(2 / dims[k]), (dims[k], dims[k + 1])).astype(np.float32), np.zeros(dims[k + 1], np.float32)) for k in range(len(dims) - 1)]
        W[-1] = (W[-1][0], np.full(1, np.median(yt), np.float32))
        m = [(np.zeros_like(w), np.zeros_like(b)) for w, b in W]; v = [(np.zeros_like(w), np.zeros_like(b)) for w, b in W]
        b1, b2, eps, paso = .9, .999, 1e-8, 0; mejor, sin_mejora, Wm = np.inf, 0, W
        for _ in range(self.epocas):
            orden = rng.permutation(len(yt))
            for i in range(0, len(yt), self.lote):
                idx = orden[i:i + self.lote]; G = self.gradientes(Xt[idx], yt[idx], W)
                paso += 1; nuevos = []
                for k in range(len(W) - 1, -1, -1):
                    w, b = W[k]; gw, gb = G[k]
                    mw, mb = m[k]; vw, vb = v[k]
                    mw = b1 * mw + (1 - b1) * gw; mb = b1 * mb + (1 - b1) * gb; vw = b2 * vw + (1 - b2) * gw ** 2; vb = b2 * vb + (1 - b2) * gb ** 2
                    m[k], v[k] = (mw, mb), (vw, vb); c1, c2 = 1 - b1 ** paso, 1 - b2 ** paso
                    nuevos.append((w - self.lr * (mw / c1) / (np.sqrt(vw / c2) + eps), b - self.lr * (mb / c1) / (np.sqrt(vb / c2) + eps)))
                W = nuevos[::-1]
            ev = float(np.mean(np.abs(self._adelante(Xv, W)[-1][:, 0] - yv)))
            if ev < mejor - 1e-6: mejor, sin_mejora, Wm = ev, 0, [(w.copy(), b.copy()) for w, b in W]
            else:
                sin_mejora += 1
                if sin_mejora >= self.paciencia: break
        self.W_ = Wm; return self

    def predict(self, X):
        return self._adelante(X.astype(np.float32), self.W_)[-1][:, 0]

