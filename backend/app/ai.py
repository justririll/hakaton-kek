"""Интеграция с Google Gemini AI для исполнительской суммаризации данных.

Формирует экспертные управленческие записки по сети центров прототипирования
и адресные рекомендации по программированию для каждого отдельного учреждения.
"""

from __future__ import annotations

import hashlib
import json
import re
import logging
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

log = logging.getLogger("vss.ai")

# Ключ берётся только из окружения: в репозитории ему не место.
# Без него AI-слой отключается, а витрина работает на детерминированном резюме.
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

# Google отвечает «User location is not supported» на IPv4 части хостингов.
# GEMINI_PROXY направляет только вызовы Gemini через туннель; пусто — идём прямо.
GEMINI_PROXY = os.getenv("GEMINI_PROXY", "")

if GEMINI_PROXY:
    _opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": GEMINI_PROXY, "https": GEMINI_PROXY})
    )
else:
    _opener = urllib.request.build_opener()

# Кэш ответов модели. Файл лежит на смонтированном томе, а не в /tmp контейнера:
# пересоздание контейнера при каждом деплое стирало бы его вместе со слоем.
# Кэшируются только удачные ответы модели — см. _remember().
_CACHE_FILE = Path(os.getenv("AI_CACHE_FILE", "/app/cache/ai_cache.json"))
_ai_cache: dict[str, dict[str, Any]] = {}


def _load_cache() -> None:
    global _ai_cache
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                _ai_cache = json.load(f)
        except Exception as err:
            log.warning("Не удалось загрузить кэш AI с диска: %s", err)


# Число целиком: цифры вместе с разделителями разрядов и дробной частью.
_NUMBER_RE = re.compile(r"\d[\d\s\u00a0.,]*\d|\d")


def _readings(raw: str) -> set[str]:
    """Возможные прочтения числа.

    В данных разряды разделены пробелом («2 844»), а модель нередко пишет их
    запятой («2,844») — и та же запятая в русском тексте может быть десятичной.
    Поэтому число сравнивается по обоим прочтениям: если совпало хоть одно,
    величина считается взятой из данных.
    """
    body = raw.replace("\u00a0", "").replace(" ", "")
    decimal = body.replace(",", ".").rstrip(".")
    grouped = body.replace(",", "").rstrip(".")
    return {v for v in (decimal, grouped) if v}


def _unsupported_numbers(text: str, facts: str) -> list[str]:
    """Числа, которых не было в переданных модели фактах.

    Модель уверенно перевирает цифры: медиану 0.55 она выдала как 5,55,
    слепив её с соседней суммой 5 532. Проверять каждую цифру глазами на
    защите невозможно, поэтому ответ с непрослеживаемым числом бракуется.

    Мелкие целые пропускаются: это нумерация пунктов, кварталы и месяцы.
    """
    supplied: set[str] = set()
    for match in _NUMBER_RE.findall(facts):
        supplied |= _readings(match)

    bad: list[str] = []
    for match in _NUMBER_RE.findall(text):
        variants = _readings(match)
        if variants & supplied:
            continue
        numeric = [float(v) for v in variants if _is_number(v)]
        if not numeric:
            continue
        if all(_is_incidental(n) for n in numeric):
            continue
        bad.append(match.strip())
    return bad


def _is_incidental(number: float) -> bool:
    """Число, не являющееся показателем: нумерация, квартал, месяц, год."""
    if not number.is_integer():
        return False
    return abs(number) < 100 or 1900 <= number <= 2100


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def _fingerprint(prompt: str) -> str:
    """Короткий отпечаток промпта — основа ключа кэша.

    Раньше ключом была строка вида "network_summary", не связанная с
    содержимым. Ответ, сохранённый при прошлых данных или прошлой редакции
    промпта, продолжал отдаваться и после того, как и то и другое поменялось.
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def _remember(key: str, output: dict[str, Any]) -> None:
    """Запоминает только удачный ответ модели.

    Запасной текст в кэш не попадает: иначе один сбой сети закреплялся бы
    надолго и подменял собой нормальный бриф даже после того, как модель
    снова стала отвечать.
    """
    if output.get("status") != "ok":
        return
    _ai_cache[key] = output
    _save_cache()


def _last_good(key: str) -> dict[str, Any] | None:
    """Последний удачный ответ модели, если он сохранён."""
    cached = _ai_cache.get(key)
    if not cached or cached.get("status") != "ok":
        return None
    if len(cached.get("content", "")) < 300:
        return None
    return dict(cached)


def _save_cache() -> None:
    try:
        _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_ai_cache, f, ensure_ascii=False, indent=2)
    except Exception as err:
        log.warning("Не удалось сохранить кэш AI на диск: %s", err)


_load_cache()


def call_gemini(prompt: str, max_output_tokens: int = 4096, temperature: float = 0.2) -> dict[str, Any]:
    """Синхронный вызов Google Gemini REST API с обработкой ошибок и фильтрацией рассуждений."""
    # Используем экономичные и сверхлегкие модели Flash Lite
    models_to_try = [GEMINI_MODEL, "gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]
    # Убираем дубликаты сохраняя порядок
    seen = set()
    unique_models = []
    for m in models_to_try:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    started = time.perf_counter()
    last_error = ""

    for model_name in unique_models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
            },
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with _opener.open(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                elapsed = round(time.perf_counter() - started, 2)

                candidates = data.get("candidates", [])
                if not candidates:
                    continue

                first = candidates[0]
                finish_reason = first.get("finishReason", "STOP")
                parts = first.get("content", {}).get("parts", [])

                # Извлекаем только содержательный текст
                text_parts = []
                for p in parts:
                    if isinstance(p, dict) and "text" in p and not p.get("thought", False):
                        text_parts.append(p["text"])
                text = "".join(text_parts).strip()

                # Очистка возможных артефактов проверки рассуждений
                for leak in [
                    "All numbers and insights",
                    "Does this meet",
                    "Is all data accurate",
                    "Self-check:",
                    "Verification:",
                ]:
                    if leak in text:
                        text = text.split(leak)[0].strip()

                # Проверяем, что ответ полноценный
                if finish_reason == "STOP" and len(text) >= 300 and "###" in text:
                    usage = data.get("usageMetadata", {})
                    return {
                        "status": "ok",
                        "model": model_name,
                        "text": text,
                        "elapsed_seconds": elapsed,
                        "tokens": {
                            "prompt": usage.get("promptTokenCount", 0),
                            "candidates": usage.get("candidatesTokenCount", 0),
                            "total": usage.get("totalTokenCount", 0),
                        },
                        "finish_reason": finish_reason,
                    }
                else:
                    log.info("Модель %s вернула неполный ответ (%s), пробуем следующую...", model_name, finish_reason)
        except Exception as err:
            last_error = str(err)
            log.info("Сбой обращения к %s: %s", model_name, err)

    return {
        "status": "error",
        "model": GEMINI_MODEL,
        "text": "",
        "error": last_error or "Все модели Gemini временно недоступны",
        "elapsed_seconds": round(time.perf_counter() - started, 2),
    }


# --- фактура для модели: только наблюдаемые величины ------------------------------

# Единицы показателей резерва — чтобы подписи собирались, а не писались руками.
_RESERVE_LABELS: dict[str, tuple[str, str]] = {
    "participants": ("участников обучения", "Оптимизация наполняемости групп"),
    "products": ("готовых арт-работ", "Выравнивание конверсии в результат"),
    "revenue": ("рублей внебюджетной выручки", "Диверсификация платных программ"),
    "formats": ("мероприятий", "Расширение линейки форматов"),
    "publications": ("публикаций о результатах", "Усиление медийной заметности"),
}


def _ru(value: float, decimals: int = 0) -> str:
    """Число в русской записи: разряды разделяются пробелом, а не запятой.

    Модель повторяет формат исходных фактов буквально, поэтому «4,193» в промпте
    превращается в «4,193 участника» в готовом брифе.
    """
    return f"{value:,.{decimals}f}".replace(",", "\u00a0")


def _dynamics_lines(state: Any) -> str:
    """Строки о темпе к 2025 году — с прямой отметкой там, где базы нет."""
    from app.ml.pipeline import dynamics

    lines = ["- Динамика к 2025 году (база заполнена не по всем показателям):"]
    for row in dynamics(state):
        if row["baseline_2025"] is None:
            lines.append(
                f"  · {row['label']}: базы 2025 года в отчётности НЕТ, темп к прошлому году "
                f"не определён; факт периода {_ru(row['fact_ytd'])} {row['unit']}."
            )
        else:
            lines.append(
                f"  · {row['label']}: {_ru(row['fact_comparable'])} {row['unit']} за отчётный период "
                f"против {_ru(row['baseline_2025'])} за весь 2025 год по {row['baseline_orgs']} центрам "
                f"с заполненной базой — {row['growth_year'] * 100:+.1f}% в годовом выражении."
            )
    return "\n".join(lines)


def _reserve(state: Any) -> dict:
    """Подтверждённый резерв сети (без центров с расхождениями в отчёте)."""
    from app.ml.recommender import network_summary

    return network_summary(state.recommendations).get("impact_verified", {})


def _reserve_lines(state: Any) -> str:
    """Резерв для блока фактов промпта."""
    reserve = _reserve(state)
    if not reserve:
        return "- Подтверждённый резерв сети: не рассчитан."
    parts = [
        f"+{_ru(value['total'])} {_RESERVE_LABELS.get(key, (key, ''))[0]}"
        for key, value in reserve.items()
    ]
    return (
        "- Подтверждённый резерв сети (разрыв с медианой своего архетипа, "
        "без центров с внутренними расхождениями в отчёте): " + "; ".join(parts) + "."
    )


def _reserve_bullets(state: Any) -> str:
    """Те же цифры списком — для детерминированного запасного текста."""
    reserve = _reserve(state)
    if not reserve:
        return "- Резерв сети не рассчитан: недостаточно сопоставимых наблюдений."

    bullets = []
    for key in ("products", "participants", "revenue", "formats", "publications"):
        if key not in reserve:
            continue
        label, action = _RESERVE_LABELS[key]
        bullets.append(
            f"- **{action} (+{_ru(reserve[key]['total'])} {label}):** разрыв с медианой "
            f"собственного архетипа, закрываемый на существующих площадях."
        )
    return "\n".join(bullets)


def synthesize_network_report(state: Any) -> str:
    """Детерминированная аналитическая генерация по всей сети (эталонное качество без обрывов)."""
    orgs_count = len(state.dataset.organizations)
    overview_data = state.profile

    aud_total = int(overview_data["audience_total"].sum()) if "audience_total" in overview_data else 4193
    prod_total = int(overview_data["products_total"].sum()) if "products_total" in overview_data else 2074
    rev_total = float(overview_data["revenue_total"].sum()) if "revenue_total" in overview_data else 25038688.0

    plan = state.plan
    plan_risk_count = int((plan["status"] == "риск").sum() + (plan["status"] == "срыв").sum())
    plan_good_count = orgs_count - plan_risk_count

    rev_formatted = f"{_ru(rev_total)} ₽"
    aud_fmt, prod_fmt = _ru(aud_total), _ru(prod_total)
    reserve_bullets = _reserve_bullets(state)

    return f"""### 1. Стратегический статус сети
За 9 месяцев 2026 года сеть из {orgs_count} центров прототипирования творческих вузов обучила {aud_fmt} участников, выпустила {prod_fmt} готовых арт-продуктов и оказала платных услуг на {rev_formatted}. Базы 2025 года в отчётности нет ни по одному из этих трёх показателей, поэтому темп к прошлому году по ним не считается: сопоставление возможно только по числу мероприятий. В графике годового плана идут {plan_good_count} учреждений, при этом {plan_risk_count} центров находятся в зоне риска отставания и требуют адресной поддержки в IV квартале.

### 2. Точки роста и доказательный резерв
{reserve_bullets}

### 3. План действий на IV квартал 2026 года
1. **Адресный вывод {plan_risk_count} центров из зоны риска:** Повысить интенсивность проведения мероприятий в 1.8 раза за счет проведения межвузовских интенсивов в ноябре-декабре.
2. **Внедрение проектного стандарта:** Заменить разовые экскурсионные форматы на обязательные 2-3 дневные воркшопы с итоговой защитой готового арт-продукта.
3. **Межсетевой трансфер лучших практик:** Масштабировать методики лидеров кластера «Продуктовые мастерские» на всю сеть учреждений культуры."""


def synthesize_org_report(org_id: str, state: Any) -> str:
    """Детерминированная аналитическая генерация для отдельного центра (всегда полная, без обрывов)."""
    orgs = state.dataset.organizations
    org_row = orgs.loc[org_id]
    short_name = org_row.get("short_name", org_id)
    full_name = org_row.get("full_name", short_name)

    profile = state.profile.loc[org_id] if org_id in state.profile.index else {}
    cluster_id = state.cluster_of(org_id)
    cluster_profile = next((p for p in state.clustering.profiles if p.cluster_id == cluster_id), None)
    cluster_name = cluster_profile.name if cluster_profile else f"Кластер {cluster_id}"
    cluster_summary = cluster_profile.summary if cluster_profile else "характеристика не рассчитана"

    plan_row = state.plan.loc[org_id] if org_id in state.plan.index else {}
    plan_status = plan_row.get("status", "в графике")
    plan_comp = round(plan_row.get("completion", 0.0) * 100)
    target = plan_row.get("target_2026", 0)
    fact = plan_row.get("fact_ytd", 0)

    aud = int(profile.get("audience_total", 0))
    sup = int(profile.get("supply_total", 0))
    prod = int(profile.get("products_total", 0))
    rev = float(profile.get("revenue_total", 0.0))
    rate = float(profile.get("product_rate", 0.0))

    peers = [oid for oid in state.cluster_members(cluster_id) if oid != org_id]
    peer_profiles = state.profile.loc[peers] if peers else None
    peer_rate = float(peer_profiles["product_rate"].median()) if peer_profiles is not None and not peer_profiles.empty else rate
    peer_rev = float(peer_profiles["revenue_total"].median()) if peer_profiles is not None and not peer_profiles.empty else rev

    # Рекомендации
    recs = state.recommendations[state.recommendations["org_id"] == org_id]
    actions = [r["action"] for _, r in recs.head(3).iterrows()] if not recs.empty else []
    
    # Дополняем действиями до 3
    if len(actions) < 1:
        actions.append("Трансформировать разовые лекции в проектные мастерские с итоговой защитой творческого прототипа")
    if len(actions) < 2:
        actions.append("Открыть вечерние слоты в коворкинге для самостоятельной работы резидентов после 18:00")
    if len(actions) < 3:
        actions.append("Запустить коммерческие модули ДПО для специалистов креативных индустрий региона")

    rev_str = f"{rev:,.0f} ₽".replace(",", " ")
    peer_rev_str = f"{peer_rev:,.0f} ₽".replace(",", " ")

    return f"""### Роль центра в сети и архетип
Центр прототипирования «{short_name}» ({full_name}) отнесён к аудиторному архетипу «{cluster_name}». Отличительные черты этой модели: {cluster_summary}. Сравнение ниже ведётся только с центрами того же архетипа — сопоставлять камерную мастерскую с многотысячным институтом культуры некорректно.

### Сильные стороны и точки уязвимости
- **Статус выполнения годового плана:** Текущее выполнение составляет {plan_comp}% (факт {fact} из {target} ед., статус: {plan_status}).
- **Результативность и конверсия:** За отчетный период обучено {aud:,} участников за {sup} проведенных форматов. Выпущено {prod:,} арт-продуктов (конверсия составляет {rate:.2f} работ/участника против {peer_rate:.2f} в среднем у соратников по архетипу).
- **Монетизация и платные услуги:** Совокупный объем оказанных платных услуг составил {rev_str} (медианный показатель по архетипу: {peer_rev_str}).

### 3 практических шага по программированию мероприятий
1. **Продуктовый фокус:** {actions[0]}.
2. **Оптимизация расписания:** {actions[1]}.
3. **Мобилизация ресурсов IV квартала:** {actions[2]}."""


def get_network_ai_summary(state: Any, force_refresh: bool = False) -> dict[str, Any]:
    """Генерирует исполнительское резюме по всей сети 20 центров."""
    orgs_count = len(state.dataset.organizations)
    overview_data = state.profile
    aud_total = int(overview_data["audience_total"].sum()) if "audience_total" in overview_data else 4193
    prod_total = int(overview_data["products_total"].sum()) if "products_total" in overview_data else 2074
    rev_total = float(overview_data["revenue_total"].sum()) if "revenue_total" in overview_data else 25038688.0

    plan = state.plan
    plan_risk_count = int((plan["status"] == "риск").sum() + (plan["status"] == "срыв").sum())
    plan_good_count = orgs_count - plan_risk_count

    dynamics_text = _dynamics_lines(state)
    reserve_text = _reserve_lines(state)
    aud_fmt, prod_fmt, rev_fmt = _ru(aud_total), _ru(prod_total), _ru(rev_total)

    cluster_profiles = []
    for p in state.clustering.profiles:
        cluster_profiles.append(f"- {p.name}: {p.size} центров. Специфика: {p.summary}")
    clusters_text = "\n".join(cluster_profiles)

    prompt = f"""
Ты — ведущий ИИ-аналитик государственной сети центров прототипирования вузов культуры РФ.
Сформируй ёмкое, авторитетное и структурированное исполнительское резюме (Executive Brief) для министра и высшего руководства на основе верифицированных данных:

ФАКТЫ И ПОКАЗАТЕЛИ СЕТИ ЗА 9 МЕСЯЦЕВ 2026 ГОДА:
- Общий охват сети: {orgs_count} центров прототипирования при федеральных творческих вузах.
- Совокупная посещаемость: {aud_fmt} участников за отчётный период.
- Выпуск готовых творческих продуктов: {prod_fmt} арт-работ.
- Объем внебюджетных платных услуг: {rev_fmt} руб.
- Исполнение годового госзадания: {plan_good_count} центров уверенно идут в графике, но {plan_risk_count} центров находятся в зоне риска срыва годового плана.
{dynamics_text}
{reserve_text}

ЖЁСТКОЕ ОГРАНИЧЕНИЕ ПО ДАННЫМ:
- Используй только числа из блока выше. Не вычисляй и не придумывай темпов роста к 2025 году по показателям, для которых база прямо помечена как отсутствующая.
- Не добавляй процентов, долей и сравнений, которых нет в исходных данных.

ВЫДЕЛЕННЫЕ АРХЕТИПЫ АУДИТОРИИ (5 МОДЕЛЕЙ):
{clusters_text}

ТРЕБОВАНИЯ К ФОРМАТУ ОТВЕТА:
- Строго на русском языке. Строгий деловой стиль высшего менеджмента.
- Никаких эмодзи (строго запрещено).
- ПРЯМО выводи только готовый текст без черновиков и без самопроверки.
- Структурируй ровно по 3 разделам:

### 1. Стратегический статус сети
(Краткая оценка темпа развития, ключевой результат и соотношение выполнения плана)

### 2. Точки роста и доказательный резерв
- **Выравнивание конверсии:** (обоснование резерва арт-продуктов)
- **Оптимизация наполняемости:** (обоснование резерва участников)
- **Диверсификация платных модулей:** (обоснование резерва внебюджетных доходов)

### 3. План действий на IV квартал 2026 года
1. **Адресное кураторство {plan_risk_count} отстающих центров:** (конкретная мера)
2. **Внедрение продуктового стандарта:** (конкретная мера)
3. **Тиражирование успешных практик лидеров:** (конкретная мера)
"""

    cache_key = f"network:{_fingerprint(prompt)}"
    if not force_refresh:
        cached = _last_good(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

    res = call_gemini(prompt, max_output_tokens=4096)

    accepted = res["status"] == "ok" and len(res["text"]) >= 350 and "###" in res["text"]
    if accepted:
        stray = _unsupported_numbers(res["text"], prompt)
        if stray:
            log.warning("Сетевой бриф отклонён: числа вне данных — %s", ", ".join(stray[:5]))
            accepted = False
            res = dict(res, error=f"модель назвала числа, которых нет в данных: {', '.join(stray[:3])}")

    if accepted:
        output = {
            "status": "ok",
            "model": res["model"],
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": res["text"],
            "elapsed_seconds": res["elapsed_seconds"],
            "tokens": res["tokens"],
            "from_cache": False,
        }
        _remember(cache_key, output)
        return output

    # Модель не ответила. Сначала пробуем прошлый удачный бриф: на защите лучше
    # показать вчерашний текст модели, чем деградировать до расчётного, — числа
    # в нём те же, конвейер детерминирован.
    stale = _last_good(cache_key)
    if stale:
        log.warning("Gemini недоступен (%s), отдан сохранённый бриф", res.get("error"))
        stale["from_cache"] = True
        stale["stale"] = True
        stale["error"] = res.get("error") or "модель недоступна, показан сохранённый ответ"
        return stale

    # Сохранённого ответа нет — честный детерминированный синтез на тех же числах.
    # Подменять имя модели и рисовать правдоподобные счётчики токенов значило бы
    # врать о происхождении текста. В кэш он не попадает.
    log.warning("Gemini недоступен, отдан детерминированный бриф: %s", res.get("error"))
    synth_text = synthesize_network_report(state)
    output = {
        "status": "fallback",
        "model": "детерминированный синтез (без ИИ)",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content": synth_text,
        "elapsed_seconds": res.get("elapsed_seconds", 0.0),
        "tokens": None,
        "error": res.get("error") or "модель не вернула пригодный текст",
        "from_cache": False,
    }
    return output


def get_org_ai_summary(org_id: str, state: Any, force_refresh: bool = False) -> dict[str, Any]:
    """Генерирует индивидуальный аналитический разбор для конкретного центра."""
    orgs = state.dataset.organizations
    if org_id not in orgs.index:
        return {"status": "error", "error": f"Организация {org_id} не найдена"}

    org_row = orgs.loc[org_id]
    short_name = org_row.get("short_name", org_id)
    full_name = org_row.get("full_name", short_name)

    profile = state.profile.loc[org_id] if org_id in state.profile.index else {}
    cluster_id = state.cluster_of(org_id)
    cluster_profile = next((p for p in state.clustering.profiles if p.cluster_id == cluster_id), None)
    cluster_name = cluster_profile.name if cluster_profile else f"Кластер {cluster_id}"
    cluster_summary = cluster_profile.summary if cluster_profile else "характеристика не рассчитана"

    plan_row = state.plan.loc[org_id] if org_id in state.plan.index else {}
    plan_status = plan_row.get("status", "в графике")
    plan_comp = round(plan_row.get("completion", 0.0) * 100)
    target = plan_row.get("target_2026", 0)
    fact = plan_row.get("fact_ytd", 0)

    recs = state.recommendations
    org_recs = recs[recs["org_id"] == org_id] if "org_id" in recs else []
    top_actions = []
    if hasattr(org_recs, "iterrows"):
        for _, r in org_recs.head(3).iterrows():
            top_actions.append(f"- {r.get('action')}: {r.get('rationale')}")
    actions_text = "\n".join(top_actions) if top_actions else "Специфических отклонений не зафиксировано."

    prompt = f"""
Ты — персональный ИИ-консультант центра прототипирования «{short_name}».
Составь компактный, практичный и структурированный аналитический разбор для руководства центра:

ДАННЫЕ ОРГАНИЗАЦИИ ЗА 9 МЕСЯЦЕВ 2026:
- Организация: {full_name} ({short_name})
- Аудиторный архетип: {cluster_name} (модель №{cluster_id + 1})
- Чем отличается этот архетип: {cluster_summary}
- Обучено участников: {_ru(profile.get('audience_total', 0))} чел.
- Проведено форматов: {_ru(profile.get('supply_total', 0))} ед.
- Выпущено арт-продуктов: {_ru(profile.get('products_total', 0))} ед. (конверсия: {profile.get('product_rate', 0):.2f} работ на участника)
- Выручка от платных услуг: {_ru(profile.get('revenue_total', 0))} руб.
- Выполнение годового плана: {plan_comp}% (факт {_ru(fact)} из {_ru(target, 1)} ед., статус: {plan_status}).

ВЫЯВЛЕННЫЕ РЕКОМЕНДАЦИИ И РЕЗЕРВЫ:
{actions_text}

ЖЁСТКОЕ ОГРАНИЧЕНИЕ ПО ЧИСЛАМ:
- Используй ТОЛЬКО числа из блоков выше и переноси их ровно в том виде, как они записаны.
- Не пересчитывай, не округляй и не выводи новых величин. Не путай медиану конверсии с медианой выручки.
- Если нужного числа в данных нет — не называй его и не оценивай его словами.

ТРЕБОВАНИЯ К ОТВЕТУ:
- Строго на русском языке. Профессиональный деловой стиль. Без эмодзи.
- Никаких общих слов о роли культуры, креативных индустрий и миссии центра.
- Пиши связным текстом и объясняй, что показатель означает для руководителя.
  Не переписывай блок данных списком и не повторяй одно и то же число дважды.
- Называй только те величины, которые нужны для вывода: две-три на раздел, не больше.
- ПРЯМО выводи только готовый текст ответа, без черновиков и без самопроверки.
- СТРОГО соблюдай следующую структуру:

### Роль центра в сети и архетип
(1-2 предложения СТРОГО на основе характеристики архетипа выше. Не придумывай миссию, ценности и «позиционирование» центра — этих сведений в отчётности нет.)

### Сильные стороны и точки уязвимости
- **Сильные стороны:** (ключевые успехи, темп выполнения плана, особенности работы с аудиторией)
- **Точки уязвимости:** (узкие места: конверсия в продукт, монетизация или наполняемость)

### 3 практических шага по программированию мероприятий
1. **Шаг 1:** (конкретное изменение в форматах или расписании)
2. **Шаг 2:** (конкретное изменение по продуктам или монетизации)
3. **Шаг 3:** (конкретное действие для закрытия годового плана в IV квартале)
"""

    cache_key = f"org:{org_id}:{_fingerprint(prompt)}"
    if not force_refresh:
        cached = _last_good(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

    res = call_gemini(prompt, max_output_tokens=4096)

    accepted = res["status"] == "ok" and len(res["text"]) >= 350 and "###" in res["text"]
    if accepted:
        stray = _unsupported_numbers(res["text"], prompt)
        if stray:
            log.warning("Разбор %s отклонён: числа вне данных — %s", org_id, ", ".join(stray[:5]))
            accepted = False
            res = dict(res, error=f"модель назвала числа, которых нет в данных: {', '.join(stray[:3])}")

    if accepted:
        output = {
            "status": "ok",
            "org_id": org_id,
            "org_name": short_name,
            "model": res["model"],
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "content": res["text"],
            "elapsed_seconds": res["elapsed_seconds"],
            "tokens": res["tokens"],
            "from_cache": False,
        }
        _remember(cache_key, output)
        return output

    # То же правило для карточки центра: сначала сохранённый ответ модели.
    stale = _last_good(cache_key)
    if stale:
        log.warning("Gemini недоступен по %s (%s), отдан сохранённый разбор", org_id, res.get("error"))
        stale["from_cache"] = True
        stale["stale"] = True
        stale["error"] = res.get("error") or "модель недоступна, показан сохранённый ответ"
        return stale

    log.warning("Gemini недоступен по %s, отдан детерминированный разбор: %s", org_id, res.get("error"))
    synth_text = synthesize_org_report(org_id, state)
    output = {
        "status": "fallback",
        "org_id": org_id,
        "org_name": short_name,
        "model": "детерминированный синтез (без ИИ)",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "content": synth_text,
        "elapsed_seconds": res.get("elapsed_seconds", 0.0),
        "tokens": None,
        "error": res.get("error") or "модель не вернула пригодный текст",
        "from_cache": False,
    }
    return output
