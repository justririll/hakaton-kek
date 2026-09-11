"""Учебный пример. Все люди и посещения вымышлены; Excel-файлы не используются."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

if __package__:
    from .cluster import HERE, run_clustering, save_result
else:
    from cluster import HERE, run_clustering, save_result

DEMO_AS_OF = "2026-09-11"


def make_demo(seed: int = 42) -> pd.DataFrame:
    """240 искусственных посетителей, три способа генерации поведения.

    Группы генератора не передаются кластеризатору как признаки или метки.
    Такой пример проверяет работоспособность, а не качество на реальных людях.
    """
    rng = np.random.default_rng(seed)
    formats = np.array(["мастер-класс", "образовательный модуль", "выставка"])
    scenarios = [
        (8, 15, 1, 90, [0.88, 0.08, 0.04]),
        (4, 9, 5, 125, [0.08, 0.88, 0.04]),
        (1, 4, 70, 179, [0.08, 0.08, 0.84]),
    ]
    assignment = rng.permutation(np.repeat(np.arange(3), 80))
    rows = []
    for number, scenario in enumerate(assignment):
        low, high, first_day, last_day, probabilities = scenarios[scenario]
        n_visits = int(rng.integers(low, high))
        days_ago = rng.choice(np.arange(first_day, last_day), n_visits, replace=False)
        for days in days_ago:
            event_date = (pd.Timestamp(DEMO_AS_OF) - pd.Timedelta(days=int(days))).date()
            event_type = str(rng.choice(formats, p=probabilities))
            institution = f"demo_institution_{int(rng.integers(1, 4))}"
            event_id = f"{institution}_{event_date}_{list(formats).index(event_type)}"
            rating = round(float(np.clip(rng.normal(4.1, 0.6), 1, 5)), 1)
            rows.append({
                "visitor_id": f"demo_visitor_{number:04d}",
                "event_id": event_id, "event_date": str(event_date),
                "institution_id": institution, "event_type": event_type,
                "rating": rating if rng.random() < 0.6 else None,
                "is_synthetic": True,
            })
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "output_demo")
    args = parser.parse_args()
    visits = make_demo()
    audience, report = run_clustering(visits, as_of=DEMO_AS_OF)
    args.output.mkdir(parents=True, exist_ok=True)
    visits.to_csv(args.output / "SYNTHETIC_visits.csv", index=False, encoding="utf-8-sig")
    save_result(audience, report, args.output)
    print("УЧЕБНЫЙ ПРИМЕР: все посетители и посещения искусственные.")
    print(f"Посещений: {len(visits)}; посетителей: {len(audience)}; "
          f"групп: {report['diagnostics']['k']}.")
    print(f"Силуэт: {report['diagnostics']['silhouette']:.3f}. Это не точность модели.")
    for profile in report["profiles"]:
        print(f"  {profile['cluster_id']}: {profile['name']}; "
              f"{profile['visitor_count']} чел.; "
              f"{profile['mean_visit_count']:.1f} посещения в среднем.")
    print(f"Результаты: {args.output}")


if __name__ == "__main__":
    main()
