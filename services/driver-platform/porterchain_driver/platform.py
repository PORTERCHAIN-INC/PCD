"""Driver Platform facade — single entry for all reusable driver services."""

from __future__ import annotations

from porterchain_driver.availability import AvailabilityService
from porterchain_driver.bonuses import BonusesService
from porterchain_driver.communications import DriverCommunicationService
from porterchain_driver.dashboard import DashboardService
from porterchain_driver.documents import DocumentsService
from porterchain_driver.earnings import EarningsService
from porterchain_driver.emergency import EmergencyService
from porterchain_driver.finance import DriverFinanceService
from porterchain_driver.incidents import IncidentService
from porterchain_driver.insurance import InsuranceService
from porterchain_driver.jobs import JobsService
from porterchain_driver.location import LocationService
from porterchain_driver.navigation import NavigationService
from porterchain_driver.offline import OfflineService
from porterchain_driver.performance import PerformanceService
from porterchain_driver.pod import ProofOfDeliveryService
from porterchain_driver.profile import ProfileService
from porterchain_driver.push import PushService
from porterchain_driver.ratings import RatingsService
from porterchain_driver.shift import ShiftService
from porterchain_driver.stops import StopsService
from porterchain_driver.support import SupportService
from porterchain_driver.support_bridge import DriverSupportBridgeService
from porterchain_driver.training import TrainingService
from porterchain_driver.vehicle import VehicleService
from porterchain_driver.wallet import WalletService


class DriverPlatform:
    """
    Porterchain Driver Platform — extends Fleetbase, does not replace it.

    All driver-facing capabilities are exposed through reusable services.
    API layer (`driver_engine`) delegates here; Fleetbase adapter handles logistics sync.
    """

    def __init__(self) -> None:
        self.dashboard = DashboardService()
        self.earnings = EarningsService()
        self.finance = DriverFinanceService()
        self.wallet = WalletService()
        self.stops = StopsService()
        self.jobs = JobsService()
        self.bonuses = BonusesService()
        self.communications = DriverCommunicationService()
        self.performance = PerformanceService()
        self.profile = ProfileService()
        self.availability = AvailabilityService()
        self.shift = ShiftService()
        self.vehicle = VehicleService()
        self.insurance = InsuranceService()
        self.documents = DocumentsService()
        self.ratings = RatingsService()
        self.support = SupportService()
        self.support_hub = DriverSupportBridgeService()
        self.training = TrainingService()
        self.incidents = IncidentService()
        self.emergency = EmergencyService()
        self.offline = OfflineService()
        self.push = PushService()
        self.navigation = NavigationService()
        self.pod = ProofOfDeliveryService()
        self.location = LocationService()
