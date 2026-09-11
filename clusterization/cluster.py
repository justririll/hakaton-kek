from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

REQUIRED = ("visitor_id", "event_id", "event_date", "institution_id", "event_type")
ATTENDANCE_KEY = ["visitor_id", "institution_id", "event_id"]
SEED = 42
HERE = Path(__file__).resolve().parent


def read_visits(path: str | Path) -> pd.DataFrame:
    """CSV UTF-8, запятая/точка с запятой. ID остаются строками, включая 001."""
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise ValueError("Нужен CSV с посещениями. Сводные Excel-формы не подходят.")
    return pd.read_csv(path, sep=None, engine="python", dtype=str,
                       keep_default_na=False, encoding="utf-8-sig")


def prepare_visits(visits: pd.DataFrame, as_of: str | None = None,
                   window_days: int = 180) -> tuple[pd.DataFrame, dict]:
    """Проверяем данные, убираем точные повторы, выбираем единое окно дат."""
    missing = sorted(set(REQUIRED) - set(visits.columns))
    if missing:
        raise ValueError("Нет обязательных колонок: " + ", ".join(missing)
                         + ". Нужна одна строка на посещение конкретного человека.")
    if visits.empty:
        raise ValueError("Журнал посещений пуст.")
    if not isinstance(window_days, int) or window_days < 1:
        raise ValueError("window_days должен быть положительным целым числом.")
    data = visits[list(REQUIRED)].copy()
    for column in REQUIRED:
        data[column] = data[column].astype("string").str.strip()
        if (data[column].isna() | data[column].eq("")).any():
            raise ValueError(f"В {column} есть пустые значения.")
    data["event_type"] = data["event_type"].str.casefold()
    iso = data["event_date"].str.fullmatch(r"\d{4}-\d{2}-\d{2}")
    dates = pd.to_datetime(data["event_date"], format="%Y-%m-%d", errors="coerce")
    if not iso.all() or dates.isna().any():
        raise ValueError("event_date: нужны существующие даты в формате YYYY-MM-DD.")
    data["event_date"] = dates

    # Отсутствие отзыва не равно плохой оценке. Оценки не входят в модель.
    if "rating" in visits:
        text = visits["rating"].astype("string").str.strip().replace("", pd.NA)
        ratings = pd.to_numeric(text, errors="coerce")
        invalid = text.notna() & (ratings.isna() | ~ratings.between(1, 5))
        if invalid.any():
            raise ValueError("rating: допустимы числа от 1 до 5 или пустое значение.")
        data["rating"] = ratings.astype(float)
    else:
        data["rating"] = np.nan
    data["is_synthetic"] = False
    if "is_synthetic" in visits:
        marker = visits["is_synthetic"].astype("string").str.strip().str.lower()
        if not marker.isin(["true", "false", "1", "0"]).all():
            raise ValueError("is_synthetic: нужны true/false или 1/0.")
        data["is_synthetic"] = marker.isin(["true", "1"])
    duplicates = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()
    if data.duplicated(ATTENDANCE_KEY).any():
        raise ValueError("Для одного visitor_id + institution_id + event_id есть "
                         "противоречивые записи. Исправьте их до кластеризации.")
    events = data.groupby(["institution_id", "event_id"])[
        ["event_date", "event_type"]].nunique()
    if (events > 1).any().any():
        raise ValueError("У одного мероприятия различаются дата или формат. "
                         "Каждый сеанс должен иметь свой event_id.")

    if as_of is None:
        cutoff = dates.max() + pd.Timedelta(days=1)
        cutoff_source = "day_after_latest_event"
    else:
        try:
            cutoff = pd.to_datetime(as_of, format="%Y-%m-%d", errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError("as_of должен быть датой YYYY-MM-DD.") from exc
        if pd.isna(cutoff) or cutoff.strftime("%Y-%m-%d") != as_of:
            raise ValueError("as_of должен быть датой YYYY-MM-DD.")
        cutoff_source = "explicit"
    start = cutoff - pd.Timedelta(days=window_days)
    before = data["event_date"] < start
    after = data["event_date"] >= cutoff
    selected = data.loc[~before & ~after].copy()
    if selected.empty:
        raise ValueError("В выбранном временном окне нет посещений.")
    if selected["event_type"].nunique() > 40:
        raise ValueError("Более 40 event_type. Передайте форматы мероприятий, "
                         "например «мастер-класс», а не их уникальные названия.")
    synthetic = selected["is_synthetic"]
    kind = ("synthetic" if synthetic.all() else
            "mixed_with_synthetic" if synthetic.any() else "user_provided")
    metadata = {
        "data_kind": kind, "input_rows": len(visits),
        "exact_duplicates_removed": duplicates,
        "rows_before_window": int(before.sum()),
        "rows_on_or_after_cutoff": int(after.sum()),
        "visits_in_window": len(selected),
        "visitors_in_window": int(selected["visitor_id"].nunique()),
        "visitors_outside_window_only": int(data["visitor_id"].nunique()
                                           - selected["visitor_id"].nunique()),
        "window_start_inclusive": start.strftime("%Y-%m-%d"),
        "as_of_exclusive": cutoff.strftime("%Y-%m-%d"),
        "as_of_source": cutoff_source, "window_days": window_days,
    }
    return selected, metadata


def build_audience(visits: pd.DataFrame, as_of: str) -> pd.DataFrame:
    """Много посещений одного человека превращаются в одну строку."""
    grouped = visits.groupby("visitor_id", sort=True)
    audience = grouped.agg(
        visit_count=("event_id", "size"),
        institution_count=("institution_id", "nunique"),
        last_visit=("event_date", "max"),
        mean_rating=("rating", "mean"),
        rated_visits=("rating", "count"),
    )
    audience["recency_days"] = (pd.Timestamp(as_of) - audience["last_visit"]).dt.days
    audience["weekend_share"] = visits.assign(
        weekend=visits["event_date"].dt.dayofweek >= 5
    ).groupby("visitor_id")["weekend"].mean()
    counts = pd.crosstab(visits["visitor_id"], visits["event_type"])
    shares = counts.div(counts.sum(axis=1), axis=0).add_prefix("share::")
    audience = audience.join(shares)
    audience["last_visit"] = audience["last_visit"].dt.strftime("%Y-%m-%d")
    return audience


def feature_matrix(audience: pd.DataFrame) -> tuple[np.ndarray, dict]:
    """ID и оценки не используются как признаки. Два блока имеют равный вес."""
    behavior = np.log1p(audience[["visit_count", "recency_days", "institution_count"]])
    behavior["weekend_share"] = audience["weekend_share"]
    behavior = behavior.loc[:, behavior.nunique() > 1]
    blocks, names = [], []
    if not behavior.empty:
        blocks.append(StandardScaler().fit_transform(behavior)
                      / np.sqrt(behavior.shape[1]))
        names.extend(behavior.columns)
    # Корни долей допускают нули. Общий множитель не раздувает редкие форматы.
    interests = np.sqrt(audience.filter(like="share::").to_numpy(dtype=float))
    centered = interests - interests.mean(axis=0)
    spread = float(np.sqrt(np.var(centered, axis=0).sum()))
    if spread > 1e-12:
        blocks.append(centered / spread)
        names.extend(audience.filter(like="share::").columns)
    matrix = np.column_stack(blocks) if blocks else np.zeros((len(audience), 1))
    return matrix, {"columns": list(names), "block_weighting": "equal_total_variance",
                    "behavior": "log1p counts/recency, StandardScaler",
                    "interests": "sqrt shares, center, one scale for the block"}


def _silhouette(matrix: np.ndarray, labels: np.ndarray) -> float:
    """До 3000 точек, с обязательным присутствием каждого кластера."""
    if len(labels) <= 3000:
        return float(silhouette_score(matrix, labels))
    rng = np.random.default_rng(SEED)
    mandatory = np.concatenate([
        rng.choice(np.flatnonzero(labels == label), 2, replace=False)
        for label in np.unique(labels)
    ])
    pool = np.setdiff1d(np.arange(len(labels)), mandatory)
    indices = np.concatenate([mandatory, rng.choice(
        pool, 3000 - len(mandatory), replace=False)])
    return float(silhouette_score(matrix[indices], labels[indices]))


def choose_clusters(matrix: np.ndarray, k: int | None = None,
                    max_k: int = 6, min_cluster_size: int = 5) -> tuple[np.ndarray, dict]:
    """Перебираем k. Не создаём искусственные сегменты из единичных точек."""
    if min_cluster_size < 2 or not 2 <= max_k <= 20:
        raise ValueError("min_cluster_size >= 2, max_k от 2 до 20.")
    if k is not None and not 2 <= k <= 20:
        raise ValueError("k должен быть от 2 до 20.")
    n = len(matrix)
    distinct = len(np.unique(matrix, axis=0))
    upper = min(max_k if k is None else k, distinct, n - 1, n // min_cluster_size)
    if k is not None and k > upper:
        raise ValueError("Для заданного k недостаточно разных посетителей или "
                         "не выполняется минимальный размер кластера.")
    candidates, valid = [], []
    with threadpool_limits(limits=1):
        for candidate_k in ([k] if k is not None else range(2, upper + 1)):
            labels = KMeans(n_clusters=candidate_k, n_init=20,
                            random_state=SEED).fit_predict(matrix)
            sizes = np.bincount(labels, minlength=candidate_k)
            accepted = bool(sizes.min() >= min_cluster_size)
            score = _silhouette(matrix, labels) if accepted else None
            candidates.append({"k": candidate_k, "sizes": sizes.tolist(),
                               "silhouette": score, "accepted": accepted})
            if accepted:
                valid.append((score, candidate_k, labels))
        if not valid:
            if k is not None:
                raise ValueError("При этом k возникли слишком маленькие кластеры.")
            return np.zeros(n, dtype=int), {
                "status": "no_supported_split", "k": 1, "silhouette": None,
                "candidates": candidates, "seed_stability_ari": None,
                "note": "Данных недостаточно для допустимого разбиения. "
                        "Общая группа не считается найденным сегментом.",
            }
        best_score = max(item[0] for item in valid)
        # Если разница силуэта <= 0.02, выбираем более простое разбиение.
        score, chosen_k, labels = min(
            (item for item in valid if item[0] >= best_score - 0.02),
            key=lambda item: item[1],
        )
        stability = [adjusted_rand_score(labels, KMeans(
            n_clusters=chosen_k, n_init=20, random_state=seed
        ).fit_predict(matrix)) for seed in (7, 19, 73, 101, 202)]
    return labels, {
        "status": "weak_separation" if score < 0.25 else "exploratory",
        "k": chosen_k, "silhouette": score, "candidates": candidates,
        "silhouette_sample_size": min(3000, n),
        "seed_stability_ari": float(np.mean(stability)),
        "min_cluster_size": min_cluster_size,
        "selection": "manual" if k is not None else "silhouette_then_smaller_k_within_0.02",
        "note": "Силуэт оценивает разделение в выбранных признаках, а не точность. "
                "ARI здесь проверяет только случайную инициализацию. "
                "Порог 0.25 — эвристика для пометки слабого разделения.",
    }


def make_profiles(audience: pd.DataFrame, no_split: bool = False) -> list[dict]:
    """Портреты в исходных единицах и проверяемые гипотезы мероприятий."""
    profiles = []
    shares = list(audience.filter(like="share::").columns)
    for cluster_id, group in audience.groupby("cluster_id", sort=True):
        mean_shares = group[shares].mean().sort_values(ascending=False)
        top = mean_shares.index[0].removeprefix("share::")
        name = "Общая группа: разбиение не найдено" if no_split else f"Чаще посещают: {top}"
        n_rated = int(group["rated_visits"].sum())
        mean_rating = (float((group["mean_rating"].fillna(0)
                             * group["rated_visits"]).sum() / n_rated)
                       if n_rated else None)
        hypothesis = (
            "Сначала собрать больше наблюдений и проверить различия поведения."
            if no_split else f"Проверить спрос на программу формата «{top}»; "
            "сравнить посещаемость пилота с сопоставимыми мероприятиями."
        )
        profiles.append({
            "cluster_id": int(cluster_id), "name": name, "visitor_count": len(group),
            "audience_share": len(group) / len(audience),
            "mean_visit_count": float(group["visit_count"].mean()),
            "median_visit_count": float(group["visit_count"].median()),
            "mean_recency_days": float(group["recency_days"].mean()),
            "mean_institution_count": float(group["institution_count"].mean()),
            "mean_weekend_share": float(group["weekend_share"].mean()),
            "mean_rating": mean_rating, "rated_visits": n_rated,
            "event_type_shares": {c.removeprefix("share::"): float(v)
                                  for c, v in mean_shares.items()},
            "recommendation_hypothesis": hypothesis,
        })
    return profiles


def run_clustering(visits: pd.DataFrame, *, as_of: str | None = None,
                   window_days: int = 180, k: int | None = None,
                   max_k: int = 6, min_cluster_size: int = 5) -> tuple[pd.DataFrame, dict]:
    """Точка входа для backend: таблица людей и JSON-совместимый отчёт."""
    clean, metadata = prepare_visits(visits, as_of, window_days)
    audience = build_audience(clean, metadata["as_of_exclusive"])
    matrix, feature_info = feature_matrix(audience)
    labels, diagnostics = choose_clusters(matrix, k, max_k, min_cluster_size)
    audience["cluster_id"] = labels
    # Номера воспроизводимы при том же снимке и версиях, но не вечные ID сегментов.
    ordered = audience.groupby("cluster_id")["visit_count"].mean().sort_values(
        ascending=False, kind="stable").index
    mapping = {old: new for new, old in enumerate(ordered)}
    audience["cluster_id"] = audience["cluster_id"].map(mapping).astype(int)
    audience["data_kind"] = metadata["data_kind"]
    profiles = make_profiles(audience, diagnostics["k"] == 1)
    audience["cluster_name"] = audience["cluster_id"].map(
        {p["cluster_id"]: p["name"] for p in profiles})
    if np.var(matrix, axis=0).sum() > 1e-12:
        pca = PCA(n_components=min(2, matrix.shape[1], len(matrix)), random_state=SEED)
        coords = pca.fit_transform(matrix)
        variance = pca.explained_variance_ratio_.tolist()
    else:
        coords, variance = np.zeros((len(matrix), 1)), [0.0]
    audience["pca_x"] = coords[:, 0]
    audience["pca_y"] = coords[:, 1] if coords.shape[1] > 1 else 0.0
    report = {
        "schema_version": 1, "unit_of_analysis": "visitor",
        "input": metadata, "method": "KMeans", "random_state": SEED,
        "features": feature_info, "diagnostics": diagnostics,
        "pca_explained_variance_ratio": variance, "profiles": profiles,
        "limitations": [
            "Нужен единый visitor_id для одного человека во всех учреждениях.",
            "Учитываются только люди с посещением внутри выбранного окна.",
            "Посещения отражают также доступность программ, а не только интерес.",
            "Возраст, повторные визиты и предпочтения нельзя восстановить из сводных форм.",
            "Рекомендации — гипотезы по профилям, без доказанного эффекта.",
            "PCA используется только для рисунка; кластеры строятся по всем признакам.",
            "Модуль работает в памяти и является MVP для тестового журнала.",
        ],
    }
    return audience.reset_index(), report


def save_result(audience: pd.DataFrame, report: dict, output: str | Path) -> None:
    """CSV для просмотра, JSON для backend и статический рисунок для проверки."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    audience.to_csv(output / "audience_clusters.csv", index=False, encoding="utf-8-sig")
    records = json.loads(audience.to_json(orient="records", force_ascii=False))
    for filename, value in (("audience_clusters.json", records), ("report.json", report)):
        (output / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2,
                                                  allow_nan=False), encoding="utf-8")
    fig, (ax, bars) = plt.subplots(1, 2, figsize=(12, 4.5), layout="constrained")
    colors = plt.get_cmap("tab10")
    for profile in report["profiles"]:
        cid = profile["cluster_id"]
        group = audience[audience["cluster_id"] == cid]
        ax.scatter(group["pca_x"], group["pca_y"], s=22, alpha=0.65,
                   color=colors(cid % 10), label=f"Группа {cid}: {len(group)} чел.")
    ax.set(xlabel="PCA 1", ylabel="PCA 2", title="Одна точка — один посетитель")
    ax.legend(frameon=False, fontsize=8)
    profiles = report["profiles"]
    bars.bar([str(p["cluster_id"]) for p in profiles],
             [p["visitor_count"] for p in profiles],
             color=[colors(p["cluster_id"] % 10) for p in profiles])
    bars.set(xlabel="Номер группы", ylabel="Посетители, человек", title="Размеры групп")
    synthetic = report["input"]["data_kind"] != "user_provided"
    title = "УЧЕБНЫЙ ПРИМЕР — ИСКУССТВЕННЫЕ ДАННЫЕ" if synthetic else "Сегменты посетителей"
    if report["diagnostics"]["k"] == 1:
        title += "\nРазбиение не найдено"
    fig.suptitle(title, fontsize=13, fontweight="bold")
    fig.savefig(output / "clusters.png", dpi=160)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="CSV: строка = посещение")
    parser.add_argument("--output", type=Path, default=HERE / "output")
    parser.add_argument("--as-of", help="YYYY-MM-DD, граница окна, не входит в него")
    parser.add_argument("--window-days", type=int, default=180)
    parser.add_argument("--k", type=int, help="Без параметра число групп выбирается автоматически")
    parser.add_argument("--max-k", type=int, default=6)
    parser.add_argument("--min-cluster-size", type=int, default=5)
    args = parser.parse_args()
    try:
        audience, report = run_clustering(
            read_visits(args.input), as_of=args.as_of, window_days=args.window_days,
            k=args.k, max_k=args.max_k, min_cluster_size=args.min_cluster_size)
        save_result(audience, report, args.output)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(2, f"Ошибка: {exc}\n")
    print(f"Источник: {report['input']['data_kind']}. Посетителей: {len(audience)}. "
          f"Групп: {report['diagnostics']['k']}. Результаты: {args.output}")
    print(report["diagnostics"]["note"])


if __name__ == "__main__":
    main()
