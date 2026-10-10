"""P11 of the user-level LDP plan: every training user is enrolled, matched trips or not.

Fixture-only. ``geolife_onroad`` has two users; the tests copy it into ``tmp_path`` with
two renamed twins (105, 106) so the default split puts two users in ``train``. One train
user then loses every trip to map matching (``match_many`` is monkeypatched), which is
finding F3 of docs/NACRT_ULDP_RANGI.md §10: that user must still be in the roster, once.
"""

import json
import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

import trajguard.experiments.orchestrator as orch
from test_orchestrator import FIXTURES, beijing_maps_dir, mia_config, write_config
from trajguard.datamodel import CleanTrajectory, MatchedTrajectory
from trajguard.datasets.cleaning import clean_trips
from trajguard.datasets.split import split_by_user
from trajguard.experiments import registry
from trajguard.experiments.orchestrator import RunConfig, load_config, run
from trajguard.representation.views import TrajectoryView
from trajguard.synthesis.base import views_by_user
from trajguard.synthesis.markov import MarkovGenerator

_ = beijing_maps_dir  # imported so pytest resolves the fixture by name here


def _four_user_dataset(tmp_path: Path) -> Path:
    """Copy the two on-road fixture users and add a renamed twin of each."""
    src = FIXTURES / "geolife_onroad" / "Data"
    root = tmp_path / "geolife4"
    for user, twin in (("005", "105"), ("006", "106")):
        shutil.copytree(src / user, root / "Data" / user)
        shutil.copytree(src / user, root / "Data" / twin)
    return root


def _config(tmp_path: Path, maps_dir: Path) -> Path:
    cfg = mia_config(tmp_path, maps_dir)
    cfg["dataset"]["path"] = str(_four_user_dataset(tmp_path))
    return write_config(tmp_path, cfg)


def _split_train_users(cfg: RunConfig) -> list[str]:
    """Train users recomputed from the split alone: load, clean, split; no matching."""
    loader = registry.get("dataset", cfg.dataset_id)(cfg.dataset_path)
    cleaned = [c for raw in loader.iter_trajectories() for c in clean_trips(raw, cfg.cleaning)]
    labelled = split_by_user(cleaned, cfg.fractions, cfg.split_seed)
    return sorted({t.user_id for t in labelled if t.split == "train"})


def _drop_user_matches(monkeypatch: pytest.MonkeyPatch, user: str) -> None:
    """Make every trip of ``user`` fail map matching."""
    original = orch.match_many

    def drop(*args: Any, **kwargs: Any) -> tuple[list[MatchedTrajectory], int]:
        kept, dropped = original(*args, **kwargs)
        lost = [m for m in kept if m.user_id == user]
        return [m for m in kept if m.user_id != user], dropped + len(lost)

    monkeypatch.setattr(orch, "match_many", drop)


def _spy(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, ...]], list[list[TrajectoryView]]]:
    """Record every roster hand-over and every MarkovGenerator.fit call."""
    rosters: list[tuple[str, ...]] = []
    fits: list[list[TrajectoryView]] = []
    set_roster, fit = MarkovGenerator.set_user_roster, MarkovGenerator.fit

    def spy_roster(self: MarkovGenerator, users: Sequence[str]) -> None:
        rosters.append(tuple(users))
        set_roster(self, users)

    def spy_fit(self: MarkovGenerator, train: Sequence[TrajectoryView]) -> None:
        fits.append(list(train))
        fit(self, train)

    monkeypatch.setattr(MarkovGenerator, "set_user_roster", spy_roster)
    monkeypatch.setattr(MarkovGenerator, "fit", spy_fit)
    return rosters, fits


def test_user_without_matched_trip_stays_in_roster(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An opted-in generator gets every split train user; the unmatched one, once, no trips."""
    cfg_path = _config(tmp_path, beijing_maps_dir)
    train_users = _split_train_users(load_config(cfg_path))
    assert len(train_users) == 2, "fixture copy must put two users in the train split"
    lost = train_users[0]
    _drop_user_matches(monkeypatch, lost)
    monkeypatch.setattr(MarkovGenerator, "needs_user_roster", True)
    rosters, fits = _spy(monkeypatch)

    run(cfg_path)

    n_shadow = dict(load_config(cfg_path).attacks[0].mia_params).get("n_shadow", 16)
    assert len(rosters) == 1 + n_shadow  # the target, then every LiRA shadow (P5)
    for shadow_roster, shadow_fit in zip(rosters[1:], fits[1:], strict=True):
        # Candidates enter under their own user_id, with no split label to trip guards.
        assert {v.user_id for v in shadow_fit} == set(shadow_roster)
        assert all(v.split is None and v.clean is None for v in shadow_fit)
    roster = rosters[0]
    assert list(roster) == train_users  # from the split, not from matching
    assert roster.count(lost) == 1
    grouped = views_by_user(fits[0], roster)
    assert grouped[lost] == []
    assert {v.user_id for v in fits[0]} == {train_users[1]}
    assert len(roster) == 2  # n for epsilon accounting counts users, not trips


def test_roster_is_off_by_default(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A generator that does not opt in never receives a roster: today's input exactly."""
    assert MarkovGenerator.needs_user_roster is False
    rosters, fits = _spy(monkeypatch)
    run(_config(tmp_path, beijing_maps_dir))
    assert rosters == [] and fits


def test_roster_recomputed_for_a_pool_cached_before_p11(
    tmp_path: Path, beijing_maps_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A cached pool without ``train_users`` in meta.json still yields the split roster."""
    cfg_path = _config(tmp_path, beijing_maps_dir)
    cfg = load_config(cfg_path)
    train_users = _split_train_users(cfg)
    _drop_user_matches(monkeypatch, train_users[0])
    run(cfg_path)
    assert list(orch._train_roster(cfg)) == train_users  # read from meta.json

    meta_path = cfg.cache_dir / orch._version_hash(cfg) / "meta.json"
    meta = json.loads(meta_path.read_text())
    meta.pop("train_users")
    meta_path.write_text(json.dumps(meta))
    assert list(orch._train_roster(cfg)) == train_users  # recomputed from the split


def test_set_user_roster_and_grouping_reject_bad_input() -> None:
    """A roster lists each user once; a view of a user outside the roster is an error."""
    gen = MarkovGenerator(order=1)
    with pytest.raises(ValueError, match="more than once"):
        gen.set_user_roster(["a", "a"])
    gen.set_user_roster(["a", "b"])
    assert gen.user_roster == ("a", "b")
    assert views_by_user([], ["a", "b"]) == {"a": [], "b": []}
    with pytest.raises(ValueError, match="more than once"):
        views_by_user([], ["a", "a"])
    stranger = CleanTrajectory("t", "c", ((0.0, 0.0, 0.0),), (0.0, 0.0, 0.0, 0.0), 0, 0, 0, ())
    with pytest.raises(ValueError, match="not in the user roster"):
        views_by_user([TrajectoryView(clean=stranger)], ["a", "b"])
