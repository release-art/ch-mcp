"""Reflected officer-related Companies House types."""

import ch_api.types.public_data.company_officers as _co
import ch_api.types.public_data.disqualifications as _dq
import ch_api.types.public_data.officer_appointments as _oa

from . import base


class OfficerSummary(base.reflect_ch_api_t(_co.OfficerSummary)):
    """Summary of an officer as returned by the company officer list."""


class OfficerAppointmentSummary(base.reflect_ch_api_t(_oa.OfficerAppointmentSummary)):
    """Single officer appointment as returned by the officer appointments list."""


class NaturalDisqualification(base.reflect_ch_api_t(_dq.NaturalDisqualification)):
    """Disqualification record for a natural-person officer."""


class CorporateDisqualification(base.reflect_ch_api_t(_dq.CorporateDisqualification)):
    """Disqualification record for a corporate officer."""
