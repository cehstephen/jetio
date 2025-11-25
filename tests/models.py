# ---------------------------------------------------------------------------
# Jetio Framework
# Website: https://jetio.org
#
# Copyright (c) 2025 Stephen Burabari Tete. All Rights Reserved.
# 
# This source code is licensed under the BSD 3-Clause license found in the
# LICENSE file in the root directory of this source tree.
#
# Author:   Stephen Burabari Tete
# Contact:  cehtete [at] gmail.com
# LinkedIn: https://www.linkedin.com/in/tete-stephen/ 
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Mapped
from jetio import JetioModel


class Widget(JetioModel):
    """A test model for CRUD operations."""
    name: Mapped[str]
    part_number: Mapped[int]


class Staff(JetioModel):
    """A test model for staff members."""
    username: Mapped[str]


class Report(JetioModel):
    """A test model for reports."""
    title: Mapped[str]


class User(JetioModel):
    """A test model for authentication."""
    username: Mapped[str]
