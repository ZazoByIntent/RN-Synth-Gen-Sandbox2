"""Markov / n-gram generator over road-segment sequences (design §2.2 module 6, MVP baseline)."""

import math
from collections import Counter, defaultdict
from collections.abc import Sequence

import numpy as np

from trajguard.datamodel import SyntheticTrajectory
from trajguard.experiments.registry import register
from trajguard.privacy.base import params_hash
from trajguard.representation import TrajectoryView
from trajguard.synthesis.base import SyntheticGenerator

# Sentinels outside the (non-negative) edge-id space: pad the context head and mark
# sequence termination. START never appears as a "next" symbol; END does.
_START = -2
_END = -1


@register("generator", "markov")
class MarkovGenerator(SyntheticGenerator):
    """Fits an order-k Markov model over edge-id sequences and samples new ones.

    Segment sequences (``view.as_segments()``) are padded with START/END sentinels;
    transition counts get additive (Laplace) smoothing over the observed-edge ∪ {END}
    symbol space, so ``sequence_log_prob`` stays finite for any sequence (the statistic
    the membership-inference attack queries) and generation always terminates. Fits on
    the train split only (design T3: strict train/test/synthetic separation).
    """

    def __init__(self, order: int = 1, alpha: float = 1.0, max_len: int = 50) -> None:
        """Order-k n-gram with additive smoothing ``alpha`` and a generation length cap.

        Sampling randomness comes solely from the ``seed`` argument to :meth:`generate`.
        """
        if order < 1:
            raise ValueError(f"order must be >= 1, got {order}")
        if alpha <= 0:
            raise ValueError(f"alpha must be > 0, got {alpha}")
        self.order = order
        self.alpha = alpha
        self.max_len = max_len
        self._counts: dict[tuple[int, ...], Counter[int]] = {}
        self._vocab: tuple[int, ...] = ()  # observed real edge ids, sorted
        self._symbols: tuple[int, ...] = ()  # vocab + (_END,): the "next" symbol space
        self._map_id = ""
        self._trained_on_split = ""
        self._fitted = False

    def fit(self, train: Sequence[TrajectoryView]) -> None:
        """Count padded order-k transitions over the training edge sequences."""
        splits = {v.split for v in train if v.split is not None}
        if splits - {"train"}:
            raise ValueError(
                f"MarkovGenerator fits on the train split only, got splits {sorted(splits)}"
            )
        counts: dict[tuple[int, ...], Counter[int]] = defaultdict(Counter)
        vocab: set[int] = set()
        map_ids: set[str] = set()
        for view in train:
            seq = view.as_segments()
            map_ids.add(view.map_id)
            vocab.update(seq)
            padded = (_START,) * self.order + tuple(seq) + (_END,)
            for i in range(self.order, len(padded)):
                counts[padded[i - self.order : i]][padded[i]] += 1
        self._counts = dict(counts)
        self._vocab = tuple(sorted(vocab))
        self._symbols = (*self._vocab, _END)
        self._map_id = next(iter(map_ids)) if len(map_ids) == 1 else ""
        self._trained_on_split = "train"
        self._fitted = True

    def generate(self, n: int, seed: int) -> Sequence[SyntheticTrajectory]:
        """Sample ``n`` synthetic edge sequences, deterministic in ``seed``."""
        if not self._fitted:
            raise RuntimeError("MarkovGenerator.generate called before fit()")
        rng = np.random.default_rng(seed)
        ph = params_hash({"order": self.order, "alpha": self.alpha, "seed": seed})
        out: list[SyntheticTrajectory] = []
        for i in range(n):
            out.append(
                SyntheticTrajectory(
                    syn_id=f"markov/{seed}/{i}",
                    generator_id="markov",
                    params_hash=ph,
                    payload=self._sample_sequence(rng),
                    trained_on_split=self._trained_on_split,
                    map_id=self._map_id,
                )
            )
        return out

    def sequence_log_prob(self, edge_seq: Sequence[int]) -> float:
        """Log-likelihood of an edge sequence under the fitted model (never −inf)."""
        if not self._fitted:
            raise RuntimeError("MarkovGenerator.sequence_log_prob called before fit()")
        padded = (_START,) * self.order + tuple(edge_seq) + (_END,)
        return sum(
            self._log_prob_next(padded[i - self.order : i], padded[i])
            for i in range(self.order, len(padded))
        )

    def _log_prob_next(self, context: tuple[int, ...], symbol: int) -> float:
        """Additive-smoothed log P(symbol | context); uniform for an unseen context."""
        v = len(self._symbols)
        cnt = self._counts.get(context)
        if cnt is None:
            return -math.log(v)
        total = sum(cnt.values())
        return math.log((cnt[symbol] + self.alpha) / (total + self.alpha * v))

    def _sample_sequence(self, rng: np.random.Generator) -> tuple[int, ...]:
        """Walk contexts from START, emitting observed edges until END or ``max_len``."""
        context = (_START,) * self.order
        produced: list[int] = []
        while len(produced) < self.max_len:
            symbol = self._sample_next(context, rng)
            if symbol == _END:
                break
            produced.append(symbol)
            context = (*context[1:], symbol)
        return tuple(produced)

    def _sample_next(self, context: tuple[int, ...], rng: np.random.Generator) -> int:
        """Sample one next symbol from the smoothed distribution over the symbol space."""
        cnt = self._counts.get(context)
        weights = np.array(
            [(cnt[s] if cnt is not None else 0) + self.alpha for s in self._symbols],
            dtype=float,
        )
        weights /= weights.sum()
        return int(self._symbols[int(rng.choice(len(self._symbols), p=weights))])
