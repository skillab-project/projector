from app.client.tracker_client import TrackerClient
from app.core.state import ProjectorEngine
from app.services.analytics.market import MarketAnalytics
from app.services.analytics.occupations import OccupationAnalytics
from app.services.analytics.regional import RegionalAnalytics
from app.services.analytics.sectoral import SectoralAnalytics
from app.services.analytics.trends import TrendAnalytics
from app.services.esco_loader import EscoLoader
from app.services.projector_service import ProjectorService
from app.services.sector_snapshot_store import SectorSnapshotStore
from app.core.config import DATABASE_URL

engine = ProjectorEngine()
tracker = TrackerClient(engine)
loader = EscoLoader(engine)

occupations = OccupationAnalytics(engine)
regional = RegionalAnalytics(engine)

market = MarketAnalytics(engine, tracker, occupations)
trends = TrendAnalytics(engine, tracker, market)

sectoral = SectoralAnalytics(engine, occupations)
sector_snapshot_store = SectorSnapshotStore(DATABASE_URL)
service = ProjectorService(engine, tracker, occupations, regional, market, trends, sectoral, sector_snapshot_store)
