"""P0 of the user-level LDP plan: pin how ``user_id`` reaches ``SyntheticGenerator.fit``.

Fixture-only (``geolife_onroad``: users 005 and 006, four trips each). The tests spy on
``MarkovGenerator.fit`` during an orchestrator membership-inference run and record what
the target fit and the LiRA shadow fits receive. The facts they pin are written up in
docs/NACRT_ULDP_SINTEZA.md §7.1, point 3.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import trajguard.experiments.orchestrator as orch
from test_cells_mode import cells_config
from test_orchestrator import beijing_maps_dir, mia_config, write_config
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.datasets.cleaning import clean
from trajguard.datasets.split import split_by_user
from trajguard.experiments import registry
from trajguard.experiments.orchestrator import RunConfig, load_config, run
from trajguard.representation.views import TrajectoryView
from trajguard.synthesis.markov import MarkovGenerator

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here
N_SHADOW = 8  # mia_config / cells_config: attacker.n_shadow


def _labelled(cfg: RunConfig) -> list[CleanTrajectory]:
    """The run's population recomputed independently: load, clean, split by user."""
    loader = registry.get("dataset", cfg.dataset_id)(cfg.dataset_path)
    cleaned = [c for raw in loader.iter_trajectories() if (c := clean(raw, cfg.cleaning))]
    return split_by_user(cleaned, cfg.fractions, cfg.split_seed)


def _spy_fit(monkeypatch: pytest.MonkeyPatch) -> list[list[TrajectoryView]]:
    """Record the views of every MarkovGenerator.fit call, then fit as usual."""
    calls: list[list[TrajectoryView]] = []
    original = MarkovGenerator.fit

    def spy(self: MarkovGenerator, train: Sequence[TrajectoryView]) -> None:
        views = list(train)
        calls.append(views)
        original(self, views)

    monkeypatch.setattr(MarkovGenerator, "fit", spy)
    return calls


def _segments_config(tmp_path: Path, maps_dir: Path) -> dict[str, Any]:
    return mia_config(tmp_path, maps_dir)


def _cells_config(tmp_path: Path, _maps_dir: Path) -> dict[str, Any]:
    cfg = cells_config(tmp_path)
    cfg["synthetic_generators"] = [{"id": "markov", "params": {"order": 1}}]
    return cfg


@pytest.mark.parametrize("make_config", [_segments_config, _cells_config])
def test_target_fit_sees_user_id_of_every_train_trajectory(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch, make_config: Any
) -> None:
    """Target fit: one view per train trajectory, each with its user_id; n counts trips."""
    cfg_path = write_config(tmp_path, make_config(tmp_path, beijing_maps_dir))
    labelled = _labelled(load_config(cfg_path))
    train = [t for t in labelled if t.split == "train"]
    assert train, "fixture must put at least one user in the train split"

    calls = _spy_fit(monkeypatch)
    run(cfg_path)
    assert len(calls) == 1 + N_SHADOW  # one target fit, then one fit per shadow
    target_views = calls[0]

    assert all(v.user_id for v in target_views)
    assert all(v.split == "train" for v in target_views)
    # Grouping the target views by user_id gives exactly the fixture's train users.
    assert {v.user_id for v in target_views} == {t.user_id for t in train}
    # The generator is handed trajectories, not users: n here is the trip count.
    assert sorted(v.traj_id for v in target_views) == sorted(t.traj_id for t in train)
    assert len({v.user_id for v in target_views}) < len(target_views)


def test_shadow_fits_see_candidates_without_user_id(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """LiRA shadow fits get bare sequences: candidates enter with no user_id and no split."""
    cfg_path = write_config(tmp_path, mia_config(tmp_path, beijing_maps_dir))
    calls = _spy_fit(monkeypatch)
    run(cfg_path)
    target_views, shadow_calls = calls[0], calls[1:]
    member_seqs = {v.as_sequence() for v in target_views}

    seen: set[tuple[int, ...]] = set()
    for views in shadow_calls:
        assert all(v.user_id == "" and v.traj_id == "" and v.split is None for v in views)
        seen.update(v.as_sequence() for v in views)
    # Train members are among the shadow inputs, each as an anonymous single sequence.
    assert seen & member_seqs


def test_unmatched_train_trajectory_never_reaches_fit(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A train trajectory that fails map matching is absent from the target fit."""
    cfg_path = write_config(tmp_path, mia_config(tmp_path, beijing_maps_dir))
    train_ids = sorted(t.traj_id for t in _labelled(load_config(cfg_path)) if t.split == "train")
    lost = train_ids[0]
    original = orch.match_many

    def drop_one(*args: Any, **kwargs: Any) -> tuple[list[MatchedTrajectory], int]:
        kept, dropped = original(*args, **kwargs)
        return [m for m in kept if m.traj_id != lost], dropped + 1

    monkeypatch.setattr(orch, "match_many", drop_one)
    calls = _spy_fit(monkeypatch)
    run(cfg_path)
    target_ids = {v.traj_id for v in calls[0]}
    assert lost not in target_ids
    assert target_ids == set(train_ids[1:])
