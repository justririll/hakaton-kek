from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class Metrics(BaseModel):
    total_attendees: int = Field(ge=0)
    algorithm_used: str
    silhouette_score: float = Field(ge=-1, le=1)
    initial_attendance_rate: int = Field(ge=0, le=100)
    optimized_attendance_rate: int = Field(ge=0, le=100)
    growth_percent: int


class Cluster(BaseModel):
    id: int
    name: str
    tag: str
    color: str
    count: int = Field(ge=0)
    share_percent: int = Field(ge=0, le=100)
    key_interests: list[str]


class ScatterPoint(BaseModel):
    x: float
    y: float
    cluster_id: int
    name: str
    target: str


class ScheduleItem(BaseModel):
    id: str
    title: str
    hall: str
    cluster_id: int
    time_slot: str
    has_conflict: bool
    optimized_time_slot: str


class Recommendation(BaseModel):
    event_id: str
    event_title: str
    action: str
    from_slot: str
    to_slot: str
    reason: str
    impact: str


class AnalyticsDashboard(BaseModel):
    metrics: Metrics
    clusters: list[Cluster]
    scatter_points: list[ScatterPoint]
    schedule: list[ScheduleItem]
    recommendations: list[Recommendation]


@router.get("/dashboard", response_model=AnalyticsDashboard)
async def get_dashboard() -> AnalyticsDashboard:
    # '''
    # Fetch data here
    # '''
    return AnalyticsDashboard(
        metrics=Metrics(
            total_attendees=1420,
            algorithm_used="K-Means (k=4)",
            silhouette_score=0.64,
            initial_attendance_rate=68,
            optimized_attendance_rate=89,
            growth_percent=21,
        ),
        clusters=[
            Cluster(
                id=0,
                name="Держатели Пушкинской карты",
                tag="Молодежь (14-22)",
                color="#3B82F6",
                count=480,
                share_percent=34,
                key_interests=[
                    "Интерактивное искусство",
                    "Медиа-арт",
                    "VR-инсталляции",
                ],
            ),
            Cluster(
                id=1,
                name="Семейная аудитория с детьми",
                tag="Семьи",
                color="#10B981",
                count=390,
                share_percent=27,
                key_interests=[
                    "Детские спектакли",
                    "Творческие мастер-классы",
                    "Ремесла",
                ],
            ),
            Cluster(
                id=2,
                name="Академическое сообщество",
                tag="Ученые и краеведы",
                color="#8B5CF6",
                count=310,
                share_percent=22,
                key_interests=[
                    "История Татарстана",
                    "Круглые столы",
                    "Архивные лекции",
                ],
            ),
            Cluster(
                id=3,
                name="IT и Digital Art специалисты",
                tag="Профессионалы",
                color="#F59E0B",
                count=240,
                share_percent=17,
                key_interests=[
                    "AI в культуре",
                    "Нейроинтерфейсы",
                    "Генеративный звук",
                ],
            ),
        ],
        scatter_points=[
            ScatterPoint(
                x=1.2,
                y=2.4,
                cluster_id=0,
                name="Участник #102",
                target="Пушкинская карта",
            ),
            ScatterPoint(
                x=1.5,
                y=2.1,
                cluster_id=0,
                name="Участник #105",
                target="Пушкинская карта",
            ),
            ScatterPoint(
                x=0.9,
                y=1.8,
                cluster_id=0,
                name="Участник #118",
                target="Пушкинская карта",
            ),
            ScatterPoint(
                x=-2.1, y=1.4, cluster_id=1, name="Участник #201", target="Семья"
            ),
            ScatterPoint(
                x=-2.4, y=1.1, cluster_id=1, name="Участник #214", target="Семья"
            ),
            ScatterPoint(
                x=-1.8, y=1.7, cluster_id=1, name="Участник #220", target="Семья"
            ),
            ScatterPoint(
                x=2.5, y=-1.8, cluster_id=2, name="Участник #304", target="Академик"
            ),
            ScatterPoint(
                x=2.8, y=-1.5, cluster_id=2, name="Участник #312", target="Академик"
            ),
            ScatterPoint(
                x=2.1, y=-2.0, cluster_id=2, name="Участник #335", target="Академик"
            ),
            ScatterPoint(
                x=-1.1, y=-2.2, cluster_id=3, name="Участник #401", target="Digital Art"
            ),
            ScatterPoint(
                x=-1.4, y=-2.5, cluster_id=3, name="Участник #415", target="Digital Art"
            ),
            ScatterPoint(
                x=-0.8, y=-1.9, cluster_id=3, name="Участник #429", target="Digital Art"
            ),
        ],
        schedule=[
            ScheduleItem(
                id="evt-1",
                title="Генеративное искусство и AI в культуре",
                hall="Зал ЮНЕСКО",
                cluster_id=3,
                time_slot="14:00 - 15:30",
                has_conflict=True,
                optimized_time_slot="16:30 - 18:00",
            ),
            ScheduleItem(
                id="evt-2",
                title="Интерактивная медиа-выставка (Пушкинская карта)",
                hall="Медиа-лаборатория",
                cluster_id=0,
                time_slot="14:00 - 15:30",
                has_conflict=True,
                optimized_time_slot="14:00 - 15:30",
            ),
            ScheduleItem(
                id="evt-3",
                title="Традиции и ремесла Татарстана (Мастер-класс)",
                hall="Арт-пространство 1",
                cluster_id=1,
                time_slot="11:00 - 12:30",
                has_conflict=False,
                optimized_time_slot="11:00 - 12:30",
            ),
            ScheduleItem(
                id="evt-4",
                title="Круглый стол Академии наук: Цифровое наследие",
                hall="Конференц-зал",
                cluster_id=2,
                time_slot="12:00 - 13:30",
                has_conflict=False,
                optimized_time_slot="12:00 - 13:30",
            ),
        ],
        recommendations=[
            Recommendation(
                event_id="evt-1",
                event_title="Генеративное искусство и AI в культуре",
                action="Перенос времени слота",
                from_slot="14:00 (Зал ЮНЕСКО)",
                to_slot="16:30 (Зал ЮНЕСКО)",
                reason=(
                    "Устранение конкуренции за молодежную аудиторию между "
                    "медиа-выставкой и AI-лекцией"
                ),
                impact="+18% к общей посещаемости зала",
            )
        ],
    )
