"""Каноническая схема показателей Форм 1 и 2 госпрограммы «Развитие культуры».

Источник: ежеквартальный отчёт по контрольной точке «Обеспечен мониторинг
реализации соответствующего проекта» для центров прототипирования и творческих
инкубаторов, созданных на базе вузов культуры.

Ключ показателя — пара (форма, номер строки). Нумерация строк в шаблоне
стабильна во всех 20 выгрузках, поэтому она используется как первичный ключ,
а ключевые слова названия — как контрольная проверка (см. `keywords`).
"""

from __future__ import annotations

from dataclasses import dataclass, field


# --- роли листов книги --------------------------------------------------------
FORM1 = "form1"
FORM1_APP = "form1_app"
FORM2 = "form2"
TITLE = "title"


@dataclass(frozen=True)
class Indicator:
    """Описание одного показателя отчётной формы."""

    key: str  # машинный идентификатор
    form: str  # роль листа
    code: str  # номер строки в форме («3.1»)
    title: str  # человекочитаемое название (короткое)
    unit: str  # единица измерения
    group: str  # аналитическая группа
    keywords: tuple[str, ...] = field(default=())  # контроль: достаточно одного совпадения
    parent: str | None = None  # ключ агрегата, если строка — подпункт
    monetary: bool = False  # денежный показатель: нужна нормализация единиц


def _kw(*words: str) -> tuple[str, ...]:
    return tuple(w.lower() for w in words)


# Группы:
#   activity   — предложение: что центр разработал и провёл
#   audience   — аудитория: сколько человек пришло и обучилось
#   engagement — вовлечённость: что аудитория создала, как центр звучит вовне
#   economics  — экономика: объём оказанных услуг
#   ip         — интеллектуальная собственность
#   growth     — сводный темп роста из Формы 1

INDICATORS: tuple[Indicator, ...] = (
    # --- ФОРМА 1 -------------------------------------------------------------
    Indicator(
        key="events_growth_rate",
        form=FORM1,
        code="1",
        title="Темп роста числа мероприятий",
        unit="ед.",
        group="growth",
        keywords=_kw("темп роста числа мероприятий", "увеличение числа мероприятий"),
    ),
    # --- ПРИЛОЖЕНИЕ К ФОРМЕ 1: предложение (разработанные форматы) ------------
    Indicator(
        key="dev_modules",
        form=FORM1_APP,
        code="1",
        title="Образовательные модули",
        unit="ед.",
        group="activity",
        keywords=_kw("разработанных образовательных модулей"),
    ),
    Indicator(
        key="dev_masterclasses",
        form=FORM1_APP,
        code="2",
        title="Мастер-классы",
        unit="ед.",
        group="activity",
        keywords=_kw("разработанных мастер-классов"),
    ),
    Indicator(
        key="dev_cpd",
        form=FORM1_APP,
        code="3",
        title="Курсы повышения квалификации",
        unit="ед.",
        group="activity",
        keywords=_kw("курсов повышения квалификации"),
    ),
    Indicator(
        key="dev_retraining",
        form=FORM1_APP,
        code="4",
        title="Курсы профессиональной переподготовки",
        unit="ед.",
        group="activity",
        keywords=_kw("профессиональной переподготовки"),
    ),
    # --- ФОРМА 2: внешняя активность ------------------------------------------
    Indicator(
        key="federal_events",
        form=FORM2,
        code="1",
        title="Участие в федеральных мероприятиях",
        unit="ед.",
        group="engagement",
        keywords=_kw("федеральных и международных мероприятиях"),
    ),
    Indicator(
        key="media_publications",
        form=FORM2,
        code="2",
        title="Публикации в СМИ и интернете",
        unit="ед.",
        group="engagement",
        keywords=_kw("публикаций в средствах массовой информации"),
    ),
    # --- ФОРМА 2, блок 3: аудитория -------------------------------------------
    Indicator(
        key="residents_total",
        form=FORM2,
        code="3",
        title="Резиденты, создавшие продукт",
        unit="чел./ед.",
        group="engagement",
        keywords=_kw("резидентов, которые создали"),
    ),
    Indicator(
        key="trained_modules",
        form=FORM2,
        code="3.1",
        title="Обучено на образовательных модулях",
        unit="чел.",
        group="audience",
        keywords=_kw("прошедших обучение в рамках образовательных модулей"),
        parent="audience_total",
    ),
    Indicator(
        key="trained_masterclasses",
        form=FORM2,
        code="3.2",
        title="Обучено на мастер-классах",
        unit="чел.",
        group="audience",
        keywords=_kw("прошедших обучение в рамках мастер-классов"),
        parent="audience_total",
    ),
    Indicator(
        key="trained_cpd",
        form=FORM2,
        code="3.3",
        title="Обучено на курсах повышения квалификации",
        unit="чел.",
        group="audience",
        keywords=_kw("прошедших обучение в рамках курсов повышения"),
        parent="audience_total",
    ),
    Indicator(
        key="trained_retraining",
        form=FORM2,
        code="3.4",
        title="Обучено на курсах переподготовки",
        unit="чел.",
        group="audience",
        keywords=_kw("прошедших обучение в рамках курсов профессиональной"),
        parent="audience_total",
    ),
    Indicator(
        key="residents_extra",
        form=FORM2,
        code="3.5",
        title="Резиденты по дополнительным услугам",
        unit="ед.",
        group="audience",
        keywords=_kw("в рамках оказания", "дополнительных услуг", "дополнительных  услуг"),
    ),
    # --- ФОРМА 2, блок 4: результат (созданные продукты) ----------------------
    Indicator(
        key="products_total",
        form=FORM2,
        code="4",
        title="Создано творческих продуктов",
        unit="ед.",
        group="engagement",
        keywords=_kw("созданных", "продуктов", "по итогам оказания услуг"),
    ),
    Indicator(
        key="products_modules",
        form=FORM2,
        code="4.1",
        title="Продукты на образовательных модулях",
        unit="ед.",
        group="engagement",
        keywords=_kw("образовательных модулей"),
        parent="products_total",
    ),
    Indicator(
        key="products_masterclasses",
        form=FORM2,
        code="4.2",
        title="Продукты на мастер-классах",
        unit="ед.",
        group="engagement",
        keywords=_kw("мастер-классов"),
        parent="products_total",
    ),
    Indicator(
        key="products_cpd",
        form=FORM2,
        code="4.3",
        title="Продукты на курсах повышения квалификации",
        unit="ед.",
        group="engagement",
        keywords=_kw("повышения квалификации"),
        parent="products_total",
    ),
    Indicator(
        key="products_retraining",
        form=FORM2,
        code="4.4",
        title="Продукты на курсах переподготовки",
        unit="ед.",
        group="engagement",
        keywords=_kw("переподготовки"),
        parent="products_total",
    ),
    Indicator(
        key="products_extra",
        form=FORM2,
        code="4.5",
        title="Продукты по дополнительным услугам",
        unit="ед.",
        group="engagement",
        keywords=_kw("дополнительных услуг"),
        parent="products_total",
    ),
    # --- ФОРМА 2, блок 5: интеллектуальная собственность ----------------------
    Indicator(
        key="ip_total",
        form=FORM2,
        code="5",
        title="Патенты и авторские права",
        unit="ед.",
        group="ip",
        keywords=_kw("патентов и авторских прав"),
    ),
    Indicator(
        key="copyrights",
        form=FORM2,
        code="5.1",
        title="Авторские права",
        unit="ед.",
        group="ip",
        keywords=_kw("авторских прав"),
        parent="ip_total",
    ),
    Indicator(
        key="patents",
        form=FORM2,
        code="5.2",
        title="Патенты",
        unit="ед.",
        group="ip",
        keywords=_kw("патентов"),
        parent="ip_total",
    ),
    # --- ФОРМА 2, блок 6: экономика -------------------------------------------
    Indicator(
        key="revenue_total",
        monetary=True,
        form=FORM2,
        code="6",
        title="Объём оказанных услуг",
        unit="руб.",
        group="economics",
        keywords=_kw("объем оказанных услуг"),
    ),
    Indicator(
        key="revenue_science",
        monetary=True,
        form=FORM2,
        code="6.1",
        title="Услуги: научно-инновационная деятельность",
        unit="руб.",
        group="economics",
        keywords=_kw("научно-инновационной"),
        parent="revenue_total",
    ),
    Indicator(
        key="revenue_education",
        monetary=True,
        form=FORM2,
        code="6.2",
        title="Услуги: образовательная деятельность",
        unit="руб.",
        group="economics",
        keywords=_kw("образовательной деятельности"),
        parent="revenue_total",
    ),
    Indicator(
        key="revenue_other",
        monetary=True,
        form=FORM2,
        code="6.3",
        title="Услуги: иные виды деятельности",
        unit="руб.",
        group="economics",
        keywords=_kw("иных видов деятельности"),
        parent="revenue_total",
    ),
)

BY_KEY: dict[str, Indicator] = {i.key: i for i in INDICATORS}
BY_FORM_CODE: dict[tuple[str, str], Indicator] = {(i.form, i.code): i for i in INDICATORS}

# Каналы «формат ↔ аудитория ↔ результат» — основа профиля аудитории центра.
CHANNELS: tuple[tuple[str, str, str, str], ...] = (
    # (channel_key, подпись, показатель аудитории, показатель результата)
    ("modules", "Образовательные модули", "trained_modules", "products_modules"),
    ("masterclasses", "Мастер-классы", "trained_masterclasses", "products_masterclasses"),
    ("cpd", "Повышение квалификации", "trained_cpd", "products_cpd"),
    ("retraining", "Переподготовка", "trained_retraining", "products_retraining"),
)

# Показатель предложения для каждого канала (из приложения к Форме 1).
CHANNEL_SUPPLY: dict[str, str] = {
    "modules": "dev_modules",
    "masterclasses": "dev_masterclasses",
    "cpd": "dev_cpd",
    "retraining": "dev_retraining",
}
