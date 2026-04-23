"""Reflected officer-related Companies House types."""

from typing import Annotated, Union

import ch_api.types.public_data.company_officers as _co
import ch_api.types.public_data.disqualifications as _dq
import ch_api.types.public_data.officer_appointments as _oa
import pydantic

from . import base, refs


class OfficerSummary(base.reflect_ch_api_t(_co.OfficerSummary, refs_type=refs.OfficerListItemRefs)):
    """Summary of an officer as returned by the company officer list."""


class OfficerAppointmentSummary(
    base.reflect_ch_api_t(_oa.OfficerAppointmentSummary, refs_type=refs.OfficerAppointmentItemRefs)
):
    """Single officer appointment as returned by the officer appointments list."""


class NaturalDisqualification(base.reflect_ch_api_t(_dq.NaturalDisqualification, refs_type=refs.DisqualificationRefs)):
    """Disqualification record for a natural-person officer."""


class CorporateDisqualification(
    base.reflect_ch_api_t(_dq.CorporateDisqualification, refs_type=refs.DisqualificationRefs)
):
    """Disqualification record for a corporate officer."""


#: Discriminated union of the two disqualification record shapes. Each variant
#: declares a distinct ``kind`` literal, so pydantic statically narrows responses
#: and MCP clients see a tagged union in the output schema.
OfficerDisqualificationRecord = Annotated[
    Union[NaturalDisqualification, CorporateDisqualification],
    pydantic.Field(discriminator="kind"),
]
