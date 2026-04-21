"""Reflections of FCA api individual types"""

import fca_api.types.individual as fca_individual_types

from . import base


class Individual(base.reflect_fca_api_t(fca_individual_types.Individual)):
    """Reflected Individual model with conversion support"""


class IndividualControlledFunction(base.reflect_fca_api_t(fca_individual_types.IndividualControlledFunction)):
    """Reflected IndividualControlledFunction model with conversion support"""


class IndividualDisciplinaryRecord(base.reflect_fca_api_t(fca_individual_types.IndividualDisciplinaryRecord)):
    """Reflected IndividualDisciplinaryRecord model with conversion support"""
