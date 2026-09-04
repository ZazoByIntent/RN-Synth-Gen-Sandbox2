"""LDPTraceDatLoader (reference ``.dat`` reader) and the Porto → ``.dat`` conversion (fixtures)."""

import json
import lzma
import pickle
from pathlib import Path

import numpy as np
import pytest

from trajguard.datasets.ldptrace_dat import (
    _PICKLE_BATCH,
    GRID_MARGIN,
    PORTO_CENTRE_BBOX,
    LDPTraceDatLoader,
    convert_porto,
    drop_reason,
    read_dat,
    write_dat,
    write_reference_xz,
)
from trajguard.experiments import registry

FIXTURES = Path(__file__).parent / "fixtures"
TINY_DAT = FIXTURES / "ldptrace_dat" / "tiny.dat"
TINY_CSV = FIXTURES / "porto_csv" / "train_tiny.csv"

# id -> (x, y) = (lon, lat) points, see fixtures/ldptrace_dat/README.md
EXPECTED_TINY: dict[str, list[tuple[float, float]]] = {
    "0": [(0.5, 0.5), (1.5, 0.5), (2.5, 1.5)],
    "1": [(0.5, 0.5), (3.5, 1.5)],
    "2": [(2.5, 2.5)],
    "3": [(4.5, 4.5), (4.6, 4.4), (5.5, 5.5)],
    "4": [(5.5, 0.5), (4.5, 1.5), (3.5, 2.5), (2.5, 3.5)],
}
# The three kept rows of train_tiny.csv, see fixtures/porto_csv/README.md
KEPT_PORTO: list[list[tuple[float, float]]] = [
    [(-8.618643, 41.141412), (-8.618499, 41.141376), (-8.620326, 41.14251)],
    [(-8.629847, 41.159826), (-8.630351, 41.159871)],
    [(-8.612964, 41.140359), (-8.613378, 41.14035), (-8.614215, 41.140278), (-8.614773, 41.140368)],
]
KEPT_PORTO_BBOX = [-8.630351, 41.140278, -8.612964, 41.159871]


# -- loader -------------------------------------------------------------------------------


def test_registered_name() -> None:
    assert registry.get("dataset", "ldptrace_dat") is LDPTraceDatLoader


def test_loader_reads_tiny_dat() -> None:
    loader = LDPTraceDatLoader(TINY_DAT)
    assert loader.dataset_id == "ldptrace_dat"
    assert loader.native_region == "none"
    trajs = list(loader.iter_trajectories())
    assert [t.user_id for t in trajs] == ["0", "1", "2", "3", "4"]
    for traj in trajs:
        expected = EXPECTED_TINY[traj.user_id]
        assert traj.traj_id == f"ldptrace_dat/{traj.user_id}"
        assert traj.dataset_id == "ldptrace_dat"
        assert [(lon, lat) for lat, lon, _ in traj.points] == expected
        assert [p[2] for p in traj.points] == [15.0 * i for i in range(len(expected))]
        assert traj.start_t == 0.0
        assert traj.end_t == 15.0 * (len(expected) - 1)
        assert traj.n_points == len(expected)
        assert traj.source_file == str(TINY_DAT)


def test_loader_custom_dt() -> None:
    first = next(LDPTraceDatLoader(TINY_DAT, dt_s=5.0).iter_trajectories())
    assert [p[2] for p in first.points] == [0.0, 5.0, 10.0]
    with pytest.raises(ValueError, match="dt_s"):
        LDPTraceDatLoader(TINY_DAT, dt_s=0.0)


@pytest.mark.parametrize(
    ("text", "lineno", "message"),
    [
        ("#0:\n>0: 1,2;x,y;\n", 2, "bad point 'x,y'"),
        ("#0:\n>0: 1,2,3;\n", 2, "bad point '1,2,3'"),
        ("#0:\n#1:\n>0: 1,2;\n", 2, "has no point line"),
        (">0: 1,2;\n", 1, "without a preceding"),
        ("#0:\n>0: ;\n", 2, "has no points"),
        ("#0:\nhello\n", 2, "unexpected line"),
        ("#0\n>0: 1,2;\n", 1, "expected '#<id>:'"),
    ],
)
def test_malformed_lines_raise_with_line_number(
    tmp_path: Path, text: str, lineno: int, message: str
) -> None:
    path = tmp_path / "bad.dat"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match=rf":{lineno}: .*{message}"):
        list(read_dat(path))


def test_trailing_header_without_points_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.dat"
    path.write_text("#0:\n>0: 1,2;\n#1:\n", encoding="utf-8")
    with pytest.raises(ValueError, match="record '1' at end of file"):
        list(read_dat(path))


def test_write_dat_round_trips_in_reference_layout(tmp_path: Path) -> None:
    path = tmp_path / "out.dat"
    assert write_dat(path, EXPECTED_TINY.values()) == 5
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[:2] == ["#0:", ">0: 0.5,0.5;1.5,0.5;2.5,1.5;"]
    assert lines[4:6] == ["#2:", ">0: 2.5,2.5;"]
    assert dict(read_dat(path)) == EXPECTED_TINY


# -- Porto conversion ---------------------------------------------------------------------


def test_drop_reason_rules() -> None:
    bbox = PORTO_CENTRE_BBOX
    inside = [(-8.6, 41.15), (-8.61, 41.16)]
    assert drop_reason(False, inside, bbox) is None
    assert drop_reason(True, inside, bbox) == "missing_data"
    assert drop_reason(True, [], bbox) == "missing_data"  # missing data checked first
    assert drop_reason(False, [], bbox) == "too_short"  # Kaggle's empty "[]" polylines
    assert drop_reason(False, inside[:1], bbox) == "too_short"
    assert drop_reason(False, [*inside, (-8.7, 41.15)], bbox) == "outside_bbox"
    assert drop_reason(False, [*inside, (-8.6, 41.2)], bbox) == "outside_bbox"
    # border points count as inside
    assert drop_reason(False, [(-8.64, 41.14), (-8.60, 41.17)], bbox) is None


def test_convert_porto_on_tiny_csv(tmp_path: Path) -> None:
    out = tmp_path / "porto"
    stats = convert_porto(TINY_CSV, out)
    assert stats["n_read"] == 6
    assert stats["n_kept"] == 3
    assert stats["n_dropped"] == {"missing_data": 1, "too_short": 1, "outside_bbox": 1}
    assert stats["n_points"] == 9
    assert stats["bbox"] == KEPT_PORTO_BBOX
    assert stats["grid_bbox"] == pytest.approx(
        [
            KEPT_PORTO_BBOX[0] - GRID_MARGIN,
            KEPT_PORTO_BBOX[1] - GRID_MARGIN,
            KEPT_PORTO_BBOX[2] + GRID_MARGIN,
            KEPT_PORTO_BBOX[3] + GRID_MARGIN,
        ],
        abs=1e-12,
    )
    assert stats["bbox_filter"] == list(PORTO_CENTRE_BBOX)
    assert stats["max_trajectories"] is None
    assert stats["source"] == str(TINY_CSV)
    assert json.loads((out / "porto_stats.json").read_text(encoding="utf-8")) == stats

    # porto.dat reads back through the loader with the CSV's (lon, lat) points.
    trajs = list(LDPTraceDatLoader(out / "porto.dat").iter_trajectories())
    assert [t.user_id for t in trajs] == ["0", "1", "2"]
    assert [[(lon, lat) for lat, lon, _ in t.points] for t in trajs] == KEPT_PORTO

    # porto.xz is what the reference code loads: a list of lists of (x, y) pairs.
    with lzma.open(out / "porto.xz", "rb") as fh:
        db = pickle.load(fh)
    assert db == KEPT_PORTO
    assert all(isinstance(p, tuple) for traj in db for p in traj)


def test_write_reference_xz_streams_the_same_pickle_as_pickle_dump(tmp_path: Path) -> None:
    """Opcode-streamed pickle == pickle.dump of the list, across APPENDS batch boundaries."""
    long_poly = [(float(i), float(-i)) for i in range(2 * _PICKLE_BATCH + 7)]
    db = [[(0.5, 1.5), (2.5, 3.5)]] * (_PICKLE_BATCH + 3) + [long_poly, [(9.0, 9.0), (8.0, 8.0)]]
    path = tmp_path / "db.xz"
    write_reference_xz(path, db)
    with lzma.open(path, "rb") as fh:
        loaded = pickle.load(fh)
    assert loaded == db
    assert all(type(p) is tuple and type(p[0]) is float for traj in loaded for p in traj)
    # numpy arrays (what convert_porto keeps) serialise to the same plain structure
    write_reference_xz(path, [np.asarray(traj) for traj in db])
    with lzma.open(path, "rb") as fh:
        assert pickle.load(fh) == db


def test_convert_porto_max_trajectories_stops_early(tmp_path: Path) -> None:
    stats = convert_porto(TINY_CSV, tmp_path / "two", max_trajectories=2)
    assert stats["n_kept"] == 2
    assert stats["n_read"] == 2  # the first two rows are kept, so reading stops there
    assert stats["max_trajectories"] == 2
    assert stats["n_points"] == 5
    with pytest.raises(ValueError, match="max_trajectories"):
        convert_porto(TINY_CSV, tmp_path / "zero", max_trajectories=0)


def test_convert_porto_refuses_data_raw(tmp_path: Path) -> None:
    target = tmp_path / "data" / "raw" / "porto"
    with pytest.raises(ValueError, match="data/raw"):
        convert_porto(TINY_CSV, target)
    assert not (tmp_path / "data").exists()


def test_convert_porto_validation(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="bbox"):
        convert_porto(TINY_CSV, tmp_path / "bad_bbox", bbox=(-8.55, 41.13, -8.69, 41.19))
    with pytest.raises(ValueError, match="survived"):
        convert_porto(TINY_CSV, tmp_path / "empty", bbox=(0.0, 0.0, 1.0, 1.0))
    assert not (tmp_path / "empty").exists()
    wrong = tmp_path / "wrong.csv"
    wrong.write_text('"TRIP_ID","POLYLINE"\n"1","[]"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="missing columns"):
        convert_porto(wrong, tmp_path / "wrong")
