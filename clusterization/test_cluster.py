"""Проверки смысла данных и контракта. Запуск: python -m unittest clusterization.test_cluster -v"""

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from clusterization.audit_dataset import audit_dataset
from clusterization.cluster import (
    HERE,
    build_audience,
    prepare_visits,
    read_visits,
    run_clustering,
    save_result,
)
from clusterization.demo import DEMO_AS_OF, make_demo


def small_log() -> pd.DataFrame:
    return pd.DataFrame([
        ["001", "a", "2026-09-05", "org_a", "Мастер-класс", 4],
        ["001", "b", "2026-09-10", "org_b", "Выставка", None],
        ["002", "a", "2026-09-05", "org_a", "Мастер-класс", None],
    ], columns=["visitor_id", "event_id", "event_date", "institution_id", "event_type", "rating"])


class AudienceTests(unittest.TestCase):
    def test_one_person_has_one_row_across_institutions(self):
        clean, meta = prepare_visits(small_log(), DEMO_AS_OF)
        people = build_audience(clean, meta["as_of_exclusive"])
        self.assertEqual(len(people), 2)
        self.assertEqual(people.loc["001", "visit_count"], 2)
        self.assertEqual(people.loc["001", "institution_count"], 2)
        self.assertEqual(people.loc["001", "recency_days"], 1)
        self.assertEqual(people.loc["001", "weekend_share"], 0.5)
        self.assertEqual(people.loc["001", "share::выставка"], 0.5)
        np.testing.assert_allclose(people.filter(like="share::").sum(axis=1), 1)
        self.assertTrue(pd.isna(people.loc["002", "mean_rating"]))

    def test_exact_repeat_does_not_inflate_frequency(self):
        original = small_log()
        doubled = pd.concat([original, original.iloc[[0]]], ignore_index=True)
        clean, meta = prepare_visits(doubled, DEMO_AS_OF)
        self.assertEqual(len(clean), 3)
        self.assertEqual(meta["exact_duplicates_removed"], 1)

    def test_conflicting_attendance_is_rejected(self):
        original = small_log()
        conflict = original.iloc[[0]].copy()
        conflict["rating"] = 2
        with self.assertRaisesRegex(ValueError, "противоречивые"):
            prepare_visits(pd.concat([original, conflict], ignore_index=True))

    def test_event_metadata_is_consistent_between_people(self):
        visits = small_log()
        visits.loc[2, "event_type"] = "Спектакль"
        with self.assertRaisesRegex(ValueError, "различаются"):
            prepare_visits(visits)

    def test_window_boundaries_and_default_date(self):
        visits = small_log()
        visits["event_id"] = ["a", "b", "c"]
        visits["event_date"] = ["2026-09-01", "2026-08-31", "2026-09-11"]
        clean, meta = prepare_visits(visits, DEMO_AS_OF, window_days=10)
        self.assertEqual(len(clean), 1)
        self.assertEqual(meta["window_start_inclusive"], "2026-09-01")
        self.assertEqual(meta["rows_before_window"], 1)
        self.assertEqual(meta["rows_on_or_after_cutoff"], 1)
        _, default = prepare_visits(visits)
        self.assertEqual(default["as_of_exclusive"], "2026-09-12")

    def test_invalid_values_are_not_silently_imputed(self):
        for column, value in [("event_date", "2026-02-30"), ("rating", 6),
                              ("visitor_id", ""), ("institution_id", None)]:
            with self.subTest(column=column):
                visits = small_log()
                visits.loc[0, column] = value
                with self.assertRaises(ValueError):
                    prepare_visits(visits)

    def test_aggregate_table_is_rejected(self):
        totals = pd.DataFrame({"institution": ["АГИК"], "masterclasses": [409]})
        with self.assertRaisesRegex(ValueError, "visitor_id"):
            run_clustering(totals)

    def test_one_or_identical_people_are_not_forcibly_split(self):
        for n in (1, 20):
            with self.subTest(n=n):
                visits = pd.concat([small_log().iloc[[0]]] * n, ignore_index=True)
                visits["visitor_id"] = [str(i) for i in range(n)]
                people, report = run_clustering(visits, as_of=DEMO_AS_OF)
                self.assertEqual(len(people), n)
                self.assertEqual(report["diagnostics"]["k"], 1)
                self.assertEqual(report["diagnostics"]["status"], "no_supported_split")
                self.assertIsNone(report["diagnostics"]["silhouette"])
                self.assertTrue(np.isfinite(people[["pca_x", "pca_y"]]).all().all())

    def test_explicit_invalid_k_is_rejected(self):
        with self.assertRaises(ValueError):
            run_clustering(small_log(), k=6)

    def test_output_contract_reproducibility_and_missing_rating(self):
        visits = make_demo()
        people, report = run_clustering(visits, as_of=DEMO_AS_OF)
        shuffled, report2 = run_clustering(visits.sample(frac=1, random_state=7), as_of=DEMO_AS_OF)
        pd.testing.assert_series_equal(people["cluster_id"], shuffled["cluster_id"])
        self.assertTrue(people["visitor_id"].is_unique)
        self.assertEqual(len(people), visits["visitor_id"].nunique())
        self.assertEqual(people["visit_count"].sum(), len(visits))
        self.assertEqual(sum(p["visitor_count"] for p in report["profiles"]), len(people))
        self.assertEqual(report["input"]["data_kind"], "synthetic")
        self.assertNotIn("visitor_id", report["features"]["columns"])
        self.assertEqual(report["diagnostics"]["k"], report2["diagnostics"]["k"])
        no_rating, no_rating_report = run_clustering(visits.drop(columns="rating"), as_of=DEMO_AS_OF)
        pd.testing.assert_series_equal(people["cluster_id"], no_rating["cluster_id"])
        self.assertTrue(all(p["mean_rating"] is None for p in no_rating_report["profiles"]))
        json.dumps(no_rating_report, allow_nan=False)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            small_log().to_csv(root / "visits.csv", index=False)
            self.assertEqual(read_visits(root / "visits.csv").iloc[0]["visitor_id"], "001")
            visits.to_csv(root / "demo.csv", index=False)
            _, meta = prepare_visits(read_visits(root / "demo.csv"), DEMO_AS_OF)
            self.assertEqual(meta["data_kind"], "synthetic")
            save_result(no_rating, no_rating_report, root)
            records = json.loads((root / "audience_clusters.json").read_text())
            self.assertIsNone(records[0]["mean_rating"])
            self.assertGreater((root / "clusters.png").stat().st_size, 1000)

    @unittest.skipUnless((HERE.parent / "DATASET").is_dir(), "Исходный DATASET не приложен")
    def test_all_twenty_original_workbooks(self):
        audit = audit_dataset(HERE.parent / "DATASET")
        self.assertEqual(audit["workbooks"], 20)
        self.assertEqual(audit["status"], "aggregate_reports_only")
        self.assertFalse(audit["can_cluster_individual_visitors"])
        agik = next(b for b in audit["files"] if b["file"] == "АГИК.xlsx")
        masterclass = next(r for r in agik["audience_indicators"] if r["indicator_code"] == "3.2")
        self.assertEqual(float(masterclass["raw_value"]), 409)


if __name__ == "__main__":
    unittest.main()
