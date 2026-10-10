"""Enterprise End-to-End Operations Validation Framework (masterrule §16).

Automated validation across all business workflows, layers, events, and integrations.
Composes AdminDiagnosticsService — does not redesign architecture.
"""

from porterchain_api.admin_engine.e2e_validation_consistency import (
    E2EValidationConsistencyMixin,
)
from porterchain_api.admin_engine.e2e_validation_core import E2EValidationCoreMixin
from porterchain_api.admin_engine.e2e_validation_events import E2EValidationEventsMixin
from porterchain_api.admin_engine.e2e_validation_failures import (
    E2EValidationFailuresMixin,
)
from porterchain_api.admin_engine.e2e_validation_forward import (
    E2EValidationForwardMixin,
)
from porterchain_api.admin_engine.e2e_validation_helpers import StepResult
from porterchain_api.admin_engine.e2e_validation_merchant import (
    E2EValidationMerchantMixin,
)
from porterchain_api.admin_engine.e2e_validation_notifications import (
    E2EValidationNotificationsMixin,
)
from porterchain_api.admin_engine.e2e_validation_observability import (
    E2EValidationObservabilityMixin,
)
from porterchain_api.admin_engine.e2e_validation_reports import (
    E2EValidationReportsMixin,
)
from porterchain_api.admin_engine.e2e_validation_reverse import (
    E2EValidationReverseMixin,
)
from porterchain_api.admin_engine.e2e_validation_system import E2EValidationSystemMixin
from porterchain_api.admin_engine.e2e_validation_verifiers import (
    E2EValidationVerifiersMixin,
)


class E2EValidationService(
    E2EValidationCoreMixin,
    E2EValidationVerifiersMixin,
    E2EValidationSystemMixin,
    E2EValidationForwardMixin,
    E2EValidationMerchantMixin,
    E2EValidationReverseMixin,
    E2EValidationFailuresMixin,
    E2EValidationEventsMixin,
    E2EValidationNotificationsMixin,
    E2EValidationConsistencyMixin,
    E2EValidationObservabilityMixin,
    E2EValidationReportsMixin,
):
    """Full-stack automated validation — phases 1–10 per masterrule locked topology."""


__all__ = ["E2EValidationService", "StepResult"]
